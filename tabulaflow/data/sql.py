"""Schema-aware async SQL client built on SQLAlchemy.

What this module adds on top of SQLAlchemy
==========================================

**Unified async API over sync and async engines.**  One
:meth:`SQLConnector.run_query_async` call works regardless of whether
the underlying driver is sync (psycopg2, snowflake, bigquery, duckdb, ...)
or async (asyncpg, aiosqlite, asyncmy, ...).

**Unified schema data structure.**  Schema introspection produces a
single dialect-agnostic :class:`tabulaflow.schema.SQLSchema` shape (tables,
columns, types, primary/foreign keys, optional column statistics)
regardless of whether the source is DuckDB, Snowflake, BigQuery,
MySQL, etc.  Downstream consumers (agents, BI tools, schema
browsers) see one structure across all backends.

**Timeout and cancellation.**  ``SQLConnector.run_query_async(...,
timeout=N)`` and ``task.cancel()`` share one path: a per-dialect
cancel primitive (``interrupt()``, ``cancel()``, ``KILL QUERY``,
``cursor.cancel()``, ...) actually stops the running query.  Covers
14+ sync dialects and the async variants that don't self-cancel on
``asyncio.Task.cancel()``.

**Concurrency control.**  Per-DB and shared per-DBMS asyncio
semaphores (independent of pool size) for shaping request rate across
many connectors — useful for cloud warehouses like Snowflake,
BigQuery, or Databricks where concurrent-query limits and per-query
billing make a hard cap valuable across an entire eval run, not just
per database.  Plus a DDL lock for dialects where concurrent
``CREATE TABLE`` causes catalog conflicts (DuckDB, SQLite).

**Schema lifecycle.**  :class:`SQLConnector` introspects at
construction, caches to disk (keyed by ``global_id``), and refreshes
on demand via :meth:`SQLConnector.refresh_schema_async` or
automatically after writes.

**Read-only safety guard.**  ``SQLConnector(read_only=True)`` blocks
recognized write statements and surfaces a ``ReadOnlyViolationError`` in
:class:`ExecResult`. This is defense against accidental writes, not an
authorization boundary; use read-only database credentials or IAM for enforced
security. Native read-only file modes are used where supported.

**Query result caching.**  Optional disk cache keyed by
query, parameters, and timeout. Configured via
:class:`tabulaflow.data.config.SQLConnectorConfig`.

**Errors-as-data.**  :meth:`SQLConnector.run_query_async` returns
errors in :class:`ExecResult` rather than raising — except
``CancelledError``, which propagates.

**DataFrame writing with rollback.**
:meth:`SQLConnector.write_dataframe_async` runs ``pandas.to_sql``
inside the cancel-strategy plumbing, so a cancelled write rolls
back on transactional dialects.

Architecture
============

::

    SQLAlchemy.Engine / AsyncEngine
            │
            ▼
    ThrottledEngine        (cancel + throttle + timeout)
            │
            ▼
    SQLConnector           (schema + caching + read-only)

Loaders (``loaders/files.py``, ``loaders/huggingface.py``) build a
:class:`SQLConnector` from non-SQL sources (CSV, Parquet, HF
datasets) by materializing into DuckDB.
"""

import hashlib
import importlib
import json
import re
import logging
import threading
import warnings

import sqlparse
from sqlparse.lexer import Lexer as SQLLexer
from typing import Any, Callable, ClassVar, Coroutine, Sequence, Mapping, Literal, AsyncGenerator, TypeVar
import dataclasses
from dataclasses import dataclass
import collections
import pandas as pd
import os
import time
import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path
import sqlalchemy
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import DBAPIError, SAWarning
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine, event, select, func, distinct, inspect, text
from tabulaflow.core.results import ErrorInfo, ExecResult
from tabulaflow.core.schema import (
    SQLDialect,
    SQLSchema,
    SQLColumnSchema,
    SQLTableSchema,
    ForeignKeySchema,
    TableRef,
)

from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.protocols import ResultTooLargeError, validate_global_id
from tabulaflow.data._cache import (
    cache_lock,
    query_cache_key,
    query_cache_path,
    read_cached_model,
    remove_cached_file,
    schema_cache_path as get_schema_cache_path,
    write_cached_model,
)
from tabulaflow.data.json_schema import infer_json_schema, looks_like_json
from tabulaflow.data.url import _global_id_from_url

logger = logging.getLogger(__name__)

_T = TypeVar("_T")
_UNSET = object()
_SQL_DIALECT_ADAPTER: TypeAdapter[SQLDialect] = TypeAdapter(SQLDialect)
_SQL_DIALECT_BY_BACKEND: dict[str, str] = {
    "awsathena": "athena",
    "mssql": "tsql",
}

# Keywords that mark a statement as data-modifying.  Used by the
# read-only guard.  False positives are preferred over false negatives:
# blocking a borderline query is mildly annoying; letting an unsafe
# write through bypasses the safety.
_WRITE_KEYWORDS = frozenset(
    {
        # DML
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "UPSERT",
        "REPLACE",
        # DDL
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "RENAME",
        # DCL
        "GRANT",
        "REVOKE",
        # Stored procs / dynamic execution.  ``EXECUTE IMMEDIATE`` is
        # excluded inside ``_first_keyword`` — its dynamic SQL is opaque.
        "CALL",
        "EXECUTE",
        "EXEC",
        # Bulk / file ops (Snowflake, etc.)
        "COPY",
        "LOAD",
        "UNLOAD",
        "PUT",
        "GET",
        "REMOVE",
        # Database attachment
        "ATTACH",
        "DETACH",
    }
)

# DML subset of write keywords — statements that match/affect rows and for
# which an affected-row count is meaningful (unlike DDL/DCL).
_DML_KEYWORDS = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "UPSERT",
        "REPLACE",
    }
)

# DDL subset of write keywords — used to acquire the per-engine DDL
# lock on dialects with optimistic concurrency (DuckDB, SQLite) where
# concurrent DDL on the same object causes catalog conflicts.
_DDL_KEYWORDS = frozenset(
    {
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "RENAME",
        "ATTACH",
        "DETACH",
    }
)

# Dialects that need DDL serialization.
_DDL_SERIAL_DIALECTS = frozenset({"duckdb", "sqlite"})

_LEXER = SQLLexer.get_default_instance()


def _first_keyword(statement: str) -> str | None:
    """Return the first significant keyword of ``statement`` (uppercased),
    skipping leading whitespace and comments.

    Reads the raw lexer stream rather than a parsed :class:`sqlparse.sql.Statement`:
    ``sqlparse.parse`` also *groups* the token tree, which is quadratic in
    statement length (a 100 KB generated query takes ~17s, 1 MB takes minutes),
    while the lexer is a lazy linear scan that stops at the first keywords.

    Returns ``None`` if the statement starts with something other than
    a keyword (punctuation, an identifier, etc.) or contains no
    significant tokens.

    Special case: ``EXECUTE IMMEDIATE`` returns ``None`` — the dynamic
    SQL inside is opaque, so we can't classify the outer statement
    from the leading keyword alone.  Matches the original regex's
    behaviour.
    """
    keywords: list[str] = []
    for ttype, value in _LEXER.get_tokens(statement):
        if ttype in sqlparse.tokens.Whitespace or ttype in sqlparse.tokens.Comment:
            continue
        # Accept Keyword (any subtype: DML, DDL, CTE) or Name.
        # Dialect-specific keywords like ``ATTACH`` / ``DETACH`` /
        # ``UNLOAD`` are tagged as ``Name`` by sqlparse rather than
        # ``Keyword`` because they're not in its built-in vocabulary;
        # the keyword-set check at the call site filters out genuine
        # identifiers.
        if ttype in sqlparse.tokens.Keyword or ttype is sqlparse.tokens.Name:
            keywords.append(value.upper())
            if len(keywords) >= 2:
                break
            continue
        # First significant token is something else (punctuation,
        # literal): not a leading keyword.
        if not keywords:
            return None
        break
    if not keywords:
        return None
    if keywords[0] == "EXECUTE" and len(keywords) > 1 and keywords[1] == "IMMEDIATE":
        return None
    return keywords[0]


def _leading_keywords(query: str) -> list[str | None]:
    """Return the leading keyword of every statement in ``query``, one entry each."""
    return [_first_keyword(statement) for statement in sqlparse.split(query)]


def _contains_write_statement(query: str) -> str | None:
    """Return the first write/DDL/DCL keyword (uppercased) if any
    statement in ``query`` is a write, or ``None`` if all statements
    are read-only.
    """
    for keyword in _leading_keywords(query):
        if keyword is not None and keyword in _WRITE_KEYWORDS:
            return keyword
    return None


def _contains_ddl_statement(query: str) -> bool:
    """Return True if any statement in ``query`` is a DDL operation."""
    return any(keyword in _DDL_KEYWORDS for keyword in _leading_keywords(query) if keyword is not None)


def _classify_statement(statement: str | sqlalchemy.sql.expression.Executable) -> tuple[bool, bool]:
    """Classify a statement for affected-row accounting.

    Returns ``(is_write, is_dml)``. ``is_write`` is True for any write
    (DML/DDL/DCL/…); ``is_dml`` is True only for a *single* row-affecting DML
    statement (INSERT/UPDATE/DELETE/MERGE/…), since an affected-row count is only
    well-defined for one such statement (a multi-statement script reports only
    the last). Both are best-effort: raw strings are classified by leading
    keyword, ``Executable``s by SQLAlchemy's ``is_dml``/``is_ddl`` flags.
    """
    if isinstance(statement, str):
        keywords = _leading_keywords(statement)
        is_write = any(kw in _WRITE_KEYWORDS for kw in keywords if kw is not None)
        is_dml = len(keywords) == 1 and keywords[0] in _DML_KEYWORDS
        return is_write, is_dml
    is_dml = bool(getattr(statement, "is_dml", False))
    is_ddl = bool(getattr(statement, "is_ddl", False))
    return (is_dml or is_ddl), is_dml


@dataclass(frozen=True)
class _ExecOutcome:
    """Low-level result of executing one statement against a connection.

    ``result`` holds the row data (a ``DataFrame`` or a list of rows) for a
    row-returning statement, or ``None`` for a non-row statement (DDL/DML) —
    mirroring ``ExecResult.df``. ``affected_rows`` is the matched-row count for a
    single DML statement, when the driver reports it, else ``None``.
    """

    result: list[tuple[Any, ...]] | pd.DataFrame | None
    affected_rows: int | None = None


def _rowcount_affected(rowcount: int | None, is_dml: bool) -> int | None:
    """Affected count from a DBAPI ``rowcount`` (the cross-dialect source), or
    ``None`` when it is not a DML or the driver reports ``-1`` (unsupported)."""
    return rowcount if (is_dml and rowcount is not None and rowcount >= 0) else None


def _fetch_rows(result: Any, max_rows: int | None) -> list[Any]:
    rows = list(result.fetchall() if max_rows is None else result.fetchmany(max_rows + 1))
    if max_rows is not None and len(rows) > max_rows:
        raise ResultTooLargeError(max_rows)
    return rows


def _build_row_outcome(
    rows: Sequence[Any],
    keys: Sequence[Any],
    return_df: bool,
    is_write: bool,
    is_dml: bool,
) -> _ExecOutcome:
    """Build an ``_ExecOutcome`` from an already-fetched row-returning result.

    Some drivers (DuckDB) report writes as a one-column ``Count`` result set
    rather than a non-row result; fold that back to a non-row outcome carrying
    the affected count, so the count never masquerades as query output. We
    require the statement to be independently classified as a write, so a genuine
    ``SELECT ... AS "Count"`` is never misread.
    """
    if is_write and len(keys) == 1 and str(keys[0]) == "Count":
        affected: int | None = None
        if is_dml and len(rows) == 1 and rows[0][0] is not None:
            try:
                affected = int(rows[0][0])
            except (TypeError, ValueError):
                affected = None
        return _ExecOutcome(result=None, affected_rows=affected)
    data = _rows_to_df(rows, keys) if return_df else list(rows)
    return _ExecOutcome(result=data, affected_rows=None)


_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1


def _rows_to_df(rows: Sequence[Any], keys: Any) -> pd.DataFrame:
    """Build a DataFrame from SQL rows, mapping each column to the
    nullable extension dtype that matches the source Python type.

    The default ``pd.DataFrame(rows, columns=keys)`` infers dtypes from
    values: integer-with-null becomes ``float64`` (NaN is a float),
    bool-with-null becomes ``object``.  Pandas' ``convert_dtypes`` would
    fix the int case but also *demotes* whole-number floats (e.g.
    ``[1.0, 2.0, None]``) to ``Int64`` — losing the source-type
    distinction for true ``FLOAT``/``DOUBLE`` columns.

    This helper inspects Python value types per column and picks the
    matching nullable dtype directly:

    * ``int`` (within signed int64 range) → ``Int64``
    * ``int`` (outside int64 range)       → stays ``object`` — Arrow /
      Parquet can't represent C-long-overflowing ints, and the
      downstream ``_sanitize_df_strings`` stringifies these columns
      before serialization
    * ``float`` / mixed ``int+float`` → ``Float64``
    * ``bool``        → ``boolean``
    * ``str``         → ``string``
    * ``Decimal`` / ``bytes`` / ``datetime`` / mixed / all-null
                      → ``object`` (today's behaviour)

    The dtype names themselves encode the backend choice: ``Int64`` /
    ``Float64`` / ``boolean`` / ``string`` are pandas' numpy-backed
    nullable extension dtypes (the ``numpy_nullable`` backend).  No
    ``dtype_backend=`` argument is needed — that parameter only applies
    when pandas is choosing the backend on your behalf (e.g.
    ``convert_dtypes`` or ``pd.read_sql_query``).  The pyarrow
    equivalents would be ``int64[pyarrow]`` / ``double[pyarrow]`` /
    ``bool[pyarrow]`` / ``string[pyarrow]``.
    """
    df = pd.DataFrame(list(rows), columns=list(keys), dtype=object)
    for col in df.columns:
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        types = {type(v) for v in non_null}
        # ``bool`` is a subclass of ``int`` — check first.
        if types == {bool}:
            df[col] = df[col].astype("boolean")
        elif types == {int}:
            # ``astype("Int64")`` raises OverflowError on values outside
            # the signed int64 range (Snowflake NUMBER(38), BigQuery
            # BIGNUMERIC, Postgres unbounded NUMERIC, DuckDB HUGEINT).
            # Leave those columns as object so ``_sanitize_df_strings``
            # can stringify them for Arrow/Parquet compatibility.
            if all(_INT64_MIN <= v <= _INT64_MAX for v in non_null):
                df[col] = df[col].astype("Int64")
        elif types <= {int, float}:
            df[col] = df[col].astype("Float64")
        elif types == {str}:
            df[col] = df[col].astype("string")
    return df


@dataclass
class QueryResult:
    """Low-level SQL execution result.

    Attributes:
        result: Row data as tuples or a DataFrame, or ``None`` for a
            non-row-returning statement.
        latency_seconds: Execution latency, excluding cache lookup.
        affected_rows: Driver-reported affected row count when available.
    """

    result: list[tuple[Any, ...]] | pd.DataFrame | None
    """Row data for a row-returning statement, or ``None`` for a non-row
    statement (DDL/DML) — mirrors ``ExecResult.df``."""
    latency_seconds: float
    affected_rows: int | None = None
    """Rows matched/affected by a single DML statement, when the driver reports
    it; ``None`` for SELECT/DDL/multi-statement/unsupported (see ``ExecResult``)."""

    @property
    def rows(self) -> list[tuple[Any, ...]] | pd.DataFrame:
        """The result set, asserting the statement was row-returning.

        For internal callers that issue a ``SELECT`` and know rows are present
        (introspection counts, samples). Raises if used on a non-row statement."""
        if self.result is None:
            raise RuntimeError("QueryResult.rows accessed on a non-row-returning statement")
        return self.result


_ASYNC_DRIVERS = frozenset(
    {
        "aiosqlite",
        "asyncpg",
        "aiomysql",
        "aiopg",
        "asyncmy",
        "aioodbc",
        "psycopg_async",
        "oracledb_async",
    }
)


def _is_async_url(url: str | SQLAlchemyURL) -> bool:
    """Return ``True`` if the URL uses a known async SQLAlchemy driver."""
    driver = str(url).split("://", 1)[0]  # e.g. "sqlite+aiosqlite"
    return any(d in driver for d in _ASYNC_DRIVERS)


# ---------------------------------------------------------------------------
# Per-dialect cancellation strategies
# ---------------------------------------------------------------------------
#
# Cancelling a sync-driver query in flight requires a driver-specific
# primitive: DuckDB / SQLite expose ``conn.interrupt()``; psycopg /
# psycopg2 expose ``conn.cancel()``; Snowflake expects
# ``cursor.abort_query()``; MySQL needs ``KILL QUERY <id>`` from a
# separate connection; BigQuery cancels at the Job level.
# ``ThrottledEngine`` doesn't bake any of those in directly — it
# instantiates a :class:`_CancelStrategy` subclass for its dialect and
# delegates.
#
# A strategy provides three things:
#   * ``capture(conn)`` — called inside ``with engine.begin() as conn``
#     to extract the opaque handle this dialect needs for cancellation.
#     For the simple cases this is the raw DBAPI connection.  For
#     Snowflake it's a SQLAlchemy connection id used to look up a
#     captured cursor.
#   * ``abort(handle)`` — called from another thread to abort the query
#     identified by ``handle``.  Idempotent; exceptions are swallowed
#     by the caller.
#   * ``abort_from_dbapi_conn(raw)`` — bulk-cancel hook for ``aclose``,
#     which only knows raw DBAPI connections.  Defaults to ``abort`` for
#     dialects whose handle == raw conn; explicitly ``None`` for
#     dialects (snowflake) where the raw conn isn't enough — bulk
#     cancel becomes a no-op there and ``aclose`` falls back to
#     waiting for natural completion.
#
# Dialects without a registered strategy fall back to a no-op cancel —
# the asyncio task's ``CancelledError`` propagates immediately but the
# executor thread runs the query to completion (and any transaction
# commits).  Map new dialects to an existing mechanism below, adding a
# strategy only when their cancellation behavior genuinely differs.


class _CancelStrategy:
    """Base class for cancellation strategies.

    Subclasses are instantiated once per :class:`ThrottledEngine` (so
    they may hold per-engine state).  Each subclass owns its async
    behaviour: :meth:`aabort` and :meth:`acancel_all` decide on their
    own whether to run sync code inline or off-load via
    :func:`asyncio.to_thread` — the base class doesn't second-guess.

    Subclasses must override :meth:`aabort`.  The default
    :meth:`acancel_all` walks ``engine._inflight_sync_conns`` and calls
    :meth:`aabort` on each — correct when the cancel handle is the raw
    DBAPI connection.  Override for richer state (e.g. snowflake's
    cursor map) or to parallelise.
    """

    def __init__(self, engine: "ThrottledEngine") -> None:
        self.engine = engine
        self.install()

    @property
    def dialect_name(self) -> str:
        return self.engine.engine.dialect.name

    def install(self) -> None:
        """Hook for one-time setup (e.g. registering SQLAlchemy event
        listeners).  Default: nothing."""
        return None

    def capture(self, conn: sqlalchemy.engine.Connection) -> Any:
        """Extract the cancel handle from a *sync* SQLAlchemy connection.
        Called inside the executor thread that runs ``_execute_sync_engine``.

        Default: the raw DBAPI connection.  Override per dialect.
        """
        return conn.connection.driver_connection

    async def acapture(self, conn: "sqlalchemy.ext.asyncio.AsyncConnection") -> Any:
        """Extract the cancel handle from an *async* SQLAlchemy connection.
        Called on the event loop inside ``_execute_async_engine``.

        Default: ``await conn.get_raw_connection()`` then return its
        ``driver_connection`` (i.e. the underlying DBAPI connection).
        Override for dialects that need cursor-level capture or other
        special handling.
        """
        raw = await conn.get_raw_connection()
        return raw.driver_connection

    async def aabort(self, handle: Any) -> None:
        """Abort the query identified by ``handle``.  Override per dialect.

        Implementations should swallow and debug-log any errors — the
        caller (which is itself usually in a cancellation flow) doesn't
        want to see secondary exceptions.
        """
        raise NotImplementedError

    async def acancel_all(self) -> None:
        """Abort every in-flight query on this engine — used by
        :meth:`ThrottledEngine.aclose` for full shutdown.

        Default: walk ``engine._inflight_sync_conns`` and ``aabort``
        each.  Override to parallelise via ``asyncio.gather`` (typical
        for HTTP-based cancels) or to walk a per-engine state map
        instead (e.g. snowflake's cursors).
        """
        with self.engine._inflight_sync_lock:
            conns = list(self.engine._inflight_sync_conns)
        for raw in conns:
            await self.aabort(raw)


class _InterruptCancel(_CancelStrategy):
    """Cancel through a connection's fast in-process ``interrupt()``."""

    async def aabort(self, handle: Any) -> None:
        try:
            handle.interrupt()  # μs, no thread needed
        except Exception:
            logger.debug("interrupt failed for %s", self.dialect_name, exc_info=True)


class _ConnectionCancel(_CancelStrategy):
    """Cancel through a connection's blocking ``cancel()`` method.

    Used by Postgres-compatible drivers, where this opens a side TCP
    connection, and by Oracle, where it sends an OCI break.
    """

    async def aabort(self, handle: Any) -> None:
        try:
            await asyncio.to_thread(handle.cancel)
        except Exception:
            logger.debug("cancel failed for %s", self.dialect_name, exc_info=True)

    async def acancel_all(self) -> None:
        with self.engine._inflight_sync_lock:
            conns = list(self.engine._inflight_sync_conns)
        await asyncio.gather(
            *(asyncio.to_thread(raw.cancel) for raw in conns),
            return_exceptions=True,
        )


class _CursorTrackingCancel(_CancelStrategy):
    """Shared base for dialects whose cancel primitive is on the cursor
    rather than the connection (Snowflake, BigQuery).

    Registers SQLAlchemy ``before_cursor_execute`` / ``after_cursor_execute``
    listeners on the engine and stashes the in-flight cursor keyed by
    the SQLAlchemy Connection's ``id``.  ``capture`` returns that id;
    :meth:`aabort` looks up the cursor and runs the subclass-specific
    cancel via :func:`asyncio.to_thread` (it's blocking HTTP).
    :meth:`acancel_all` walks the cursor map and parallelises via
    :func:`asyncio.gather`.

    Subclasses only override :meth:`_cancel_cursor` (sync, called
    inside :func:`asyncio.to_thread`).
    """

    def install(self) -> None:
        self._cursors: dict[int, Any] = {}
        sync_engine = (
            self.engine.engine if self.engine.engine_type == "sync" else self.engine.engine.sync_engine  # type: ignore[union-attr]
        )

        def _set(conn: Any, cursor: Any, *_args: Any, **_kwargs: Any) -> None:
            self._cursors[id(conn)] = cursor

        def _clear(conn: Any, _cursor: Any, *_args: Any, **_kwargs: Any) -> None:
            self._cursors.pop(id(conn), None)

        event.listen(sync_engine, "before_cursor_execute", _set)
        event.listen(sync_engine, "after_cursor_execute", _clear)

    def capture(self, conn: sqlalchemy.engine.Connection) -> Any:
        return id(conn)

    def _cancel_cursor(self, cursor: Any) -> None:
        """Subclass-specific cancel call (e.g. ``cursor.abort_query()``).
        Runs in a worker thread."""
        raise NotImplementedError

    async def aabort(self, handle: Any) -> None:
        cursor = self._cursors.get(handle)
        if cursor is None:
            return
        try:
            await asyncio.to_thread(self._cancel_cursor, cursor)
        except Exception:
            logger.debug("cursor cancel failed for %s", self.dialect_name, exc_info=True)

    async def acancel_all(self) -> None:
        cursors = list(self._cursors.values())
        # One cancel-HTTP per cursor, fired concurrently.
        await asyncio.gather(
            *(asyncio.to_thread(self._cancel_cursor, c) for c in cursors),
            return_exceptions=True,
        )


class _SnowflakeCancel(_CursorTrackingCancel):
    """Snowflake: HTTP cancel via ``cursor.abort_query()`` (cross-thread safe)."""

    def _cancel_cursor(self, cursor: Any) -> None:
        cursor.abort_query()


class _BigQueryCancel(_CursorTrackingCancel):
    """BigQuery: ``Job.cancel()`` via the cursor's current ``query_job``.

    The dbapi cursor populates ``query_job`` on ``execute()``;
    :meth:`Job.cancel` issues a REST cancel for the running BigQuery
    job (cross-thread safe — it's just an HTTP call).
    """

    def _cancel_cursor(self, cursor: Any) -> None:
        job = getattr(cursor, "query_job", None)
        if job is not None:
            job.cancel()


class _PlainCursorCancel(_CursorTrackingCancel):
    """For dialects whose cursor exposes a plain ``.cancel()`` method
    (Trino, Databricks, Athena, ClickHouse-native, Vertica, …).
    """

    def _cancel_cursor(self, cursor: Any) -> None:
        cursor.cancel()


class _KillQueryCancel(_CancelStrategy):
    """MySQL-family cancel via ``KILL QUERY <thread_id>`` from a side
    connection.

    MySQL has no protocol-level cancel; the cancel primitive is a SQL
    statement, and the original connection is busy waiting for the
    query result, so we open a separate connection to issue ``KILL``.
    The handle is the busy connection's session ``thread_id``, captured
    eagerly so we don't need to touch the busy connection at cancel
    time.

    Subclasses implement :meth:`_kill_one` for the engine-type-specific
    side-connection open path (sync DBAPI vs async driver).
    """

    def capture(self, conn: sqlalchemy.engine.Connection) -> Any:
        raw = conn.connection.driver_connection
        return raw.thread_id() if raw is not None else None

    async def acapture(self, conn: "sqlalchemy.ext.asyncio.AsyncConnection") -> Any:
        raw = await conn.get_raw_connection()
        ac = raw.driver_connection
        try:
            return ac.thread_id() if ac is not None else None
        except Exception:
            logger.debug("could not read thread_id (async)", exc_info=True)
            return None

    async def aabort(self, handle: Any) -> None:
        if handle is None:
            return
        try:
            await self._kill_one(int(handle))
        except Exception:
            logger.debug("KILL QUERY failed", exc_info=True)

    async def acancel_all(self) -> None:
        with self.engine._inflight_sync_lock:
            conns = list(self.engine._inflight_sync_conns)
        thread_ids: list[int] = []
        for raw in conns:
            try:
                thread_ids.append(int(raw.thread_id()))
            except Exception:
                logger.debug("could not read thread_id", exc_info=True)
        await asyncio.gather(
            *(self._kill_one(tid) for tid in thread_ids),
            return_exceptions=True,
        )

    async def _kill_one(self, thread_id: int) -> None:
        """Open a side connection and run ``KILL QUERY``.  Subclass-specific."""
        raise NotImplementedError


class _MySQLCancel(_KillQueryCancel):
    """Sync-driver MySQL: KILL QUERY via a fresh sync DBAPI connection,
    dispatched to a worker thread (blocking network I/O)."""

    async def _kill_one(self, thread_id: int) -> None:
        await asyncio.to_thread(self._kill_sync, thread_id)

    def _kill_sync(self, thread_id: int) -> None:
        sync_engine = self.engine.engine
        cargs, ckwargs = sync_engine.dialect.create_connect_args(sync_engine.url)
        dbapi = sync_engine.dialect.dbapi
        if dbapi is None:
            return
        side = dbapi.connect(*cargs, **ckwargs)
        try:
            cur = side.cursor()
            try:
                cur.execute(f"KILL QUERY {thread_id}")
            finally:
                cur.close()
        finally:
            side.close()


class _AsyncMySQLCancel(_KillQueryCancel):
    """Async-driver MySQL: KILL QUERY via a fresh async side connection.

    Driver-agnostic: imports the module SQLAlchemy chose for this engine
    (``dialect.driver`` — typically ``asyncmy`` or ``aiomysql``) and uses
    its ``connect()`` directly.  Both drivers descend from PyMySQL and
    share the relevant surface (kwargs to ``connect``, ``conn.cursor()``
    as an async context manager, ``await cur.execute``,
    ``await conn.ensure_closed()``).
    """

    async def _kill_one(self, thread_id: int) -> None:
        url = self.engine.engine.url  # AsyncEngine.url
        driver = url.get_driver_name()  # "asyncmy" / "aiomysql" / ...
        module = importlib.import_module(driver)
        side = await module.connect(
            host=url.host,
            port=url.port or 3306,
            user=url.username,
            password=url.password or "",
            db=url.database,
        )
        try:
            async with side.cursor() as cur:
                await cur.execute(f"KILL QUERY {thread_id}")
        finally:
            await side.ensure_closed()


class _MSSQLCancel(_CancelStrategy):
    """MSSQL: ``KILL <session_id>`` from a side connection.

    SQL Server has no protocol-level cancel.  KILL is session-level
    (not query-level), so it terminates the entire session — heavier
    than MySQL's ``KILL QUERY``.  For our use case (Ctrl+C / asyncio
    cancel) this is acceptable: SQLAlchemy's pool fetches a fresh
    connection on the next operation.

    The session id is ``@@SPID``; we capture it once per fresh DBAPI
    connection via a connect-event hook (one extra round trip per pool
    miss) and look it up by ``id(conn)``.
    """

    def install(self) -> None:
        self._spids: dict[int, int] = {}
        sync_engine = (
            self.engine.engine if self.engine.engine_type == "sync" else self.engine.engine.sync_engine  # type: ignore[union-attr]
        )

        def _capture_spid(dbapi_conn: Any, _rec: Any) -> None:
            try:
                cur = dbapi_conn.cursor()
                try:
                    cur.execute("SELECT @@SPID")
                    self._spids[id(dbapi_conn)] = int(cur.fetchone()[0])
                finally:
                    cur.close()
            except Exception:
                logger.debug("could not capture @@SPID", exc_info=True)

        def _drop_spid(dbapi_conn: Any, _rec: Any) -> None:
            self._spids.pop(id(dbapi_conn), None)

        event.listen(sync_engine, "connect", _capture_spid)
        event.listen(sync_engine, "close", _drop_spid)

    def capture(self, conn: sqlalchemy.engine.Connection) -> Any:
        raw = conn.connection.driver_connection
        return self._spids.get(id(raw))

    async def aabort(self, handle: Any) -> None:
        if handle is None:
            return
        try:
            await asyncio.to_thread(self._kill, int(handle))
        except Exception:
            logger.debug("KILL failed for mssql", exc_info=True)

    async def acancel_all(self) -> None:
        with self.engine._inflight_sync_lock:
            conns = list(self.engine._inflight_sync_conns)
        spids = [self._spids.get(id(c)) for c in conns]
        await asyncio.gather(
            *(asyncio.to_thread(self._kill, s) for s in spids if s is not None),
            return_exceptions=True,
        )

    def _kill(self, session_id: int) -> None:
        sync_engine = (
            self.engine.engine if self.engine.engine_type == "sync" else self.engine.engine.sync_engine  # type: ignore[union-attr]
        )
        cargs, ckwargs = sync_engine.dialect.create_connect_args(sync_engine.url)
        dbapi = sync_engine.dialect.dbapi
        if dbapi is None:
            return
        side = dbapi.connect(*cargs, **ckwargs)
        try:
            cur = side.cursor()
            try:
                cur.execute(f"KILL {session_id}")
            finally:
                cur.close()
        finally:
            side.close()


class _AsyncOracleCancel(_CancelStrategy):
    """Async-mode oracledb: ``await Connection.cancel()`` sends an OCI
    break.  oracledb 2.x+ async mode exposes ``AsyncConnection.cancel``
    as a coroutine; the default :meth:`acapture` returns the
    ``AsyncConnection`` from the SQLAlchemy ``AsyncConnection``.
    """

    async def aabort(self, handle: Any) -> None:
        try:
            await handle.cancel()
        except Exception:
            logger.debug("cancel failed for oracle (async)", exc_info=True)


class _AsyncSqliteCancel(_CancelStrategy):
    """aiosqlite: ``conn.interrupt()`` on the underlying ``aiosqlite.Connection``.

    aiosqlite runs sqlite3 in a worker thread; an asyncio task cancel
    abandons the await but the worker keeps executing the SQL until
    ``Connection.interrupt()`` is called on the wrapper.  Same shape as
    :class:`_InterruptCancel` but the handle comes from the *async*
    SQLAlchemy connection — the default :meth:`acapture` does the right
    thing (it returns the aiosqlite ``Connection`` via
    ``await conn.get_raw_connection()`` + ``.driver_connection``).

    ``aiosqlite.Connection.interrupt`` is ``async def`` (it dispatches
    to the worker thread), so we ``await`` it.
    """

    async def aabort(self, handle: Any) -> None:
        try:
            await handle.interrupt()
        except Exception:
            logger.debug("interrupt failed for aiosqlite", exc_info=True)


# Sync-engine strategies — keyed by SQLAlchemy dialect.name.  Selected
# when ``ThrottledEngine.engine_type == "sync"``.
_SYNC_CANCEL_STRATEGIES: dict[str, type[_CancelStrategy]] = {
    "duckdb": _InterruptCancel,
    "sqlite": _InterruptCancel,
    "postgresql": _ConnectionCancel,
    "cockroachdb": _ConnectionCancel,  # Postgres wire protocol
    "redshift": _ConnectionCancel,  # AWS Redshift via psycopg2/psycopg
    "yugabytedb": _ConnectionCancel,  # distributed Postgres-compatible
    "snowflake": _SnowflakeCancel,
    "bigquery": _BigQueryCancel,
    "mysql": _MySQLCancel,
    "mariadb": _MySQLCancel,  # identical KILL QUERY primitive
    "oracle": _ConnectionCancel,
    "mssql": _MSSQLCancel,
    "trino": _PlainCursorCancel,
    "databricks": _PlainCursorCancel,
    "awsathena": _PlainCursorCancel,
    "clickhouse": _PlainCursorCancel,
}

# Async-engine strategies — keyed by SQLAlchemy dialect.name.  Selected
# when ``ThrottledEngine.engine_type == "async"``.  Dialects whose async
# driver self-cancels on asyncio task cancel (asyncpg, psycopg3 async)
# don't need an entry — the absence of a strategy means "trust the
# driver".  Entries below cover drivers that need our help.
_ASYNC_CANCEL_STRATEGIES: dict[str, type[_CancelStrategy]] = {
    "sqlite": _AsyncSqliteCancel,  # aiosqlite worker thread
    "mysql": _AsyncMySQLCancel,  # asyncmy / aiomysql: KILL QUERY
    "mariadb": _AsyncMySQLCancel,
    "oracle": _AsyncOracleCancel,  # oracledb async: OCI break
}


@dataclass
class ThrottledEngine:
    """Execute SQL across sync and async SQLAlchemy engines.

    Provides per-connector and shared concurrency limits, result-size limits,
    DataFrame conversion, and timeout/cancellation through backend-specific
    cancel mechanisms. Most callers should use :class:`SQLConnector`.
    """

    engine_type: Literal["async", "sync"]
    engine: AsyncEngine | sqlalchemy.engine.Engine
    dbms_semaphore: asyncio.Semaphore | None
    db_semaphore: asyncio.Semaphore | None
    _ddl_lock: asyncio.Lock | None = dataclasses.field(default=None, init=False)
    # Track in-flight sync-driver raw DBAPI connections so we can abort
    # queries on cancellation.  Sync-driver queries run in a thread-pool
    # executor and cannot be cancelled via ``asyncio`` alone — we need to
    # call the dialect's cancel primitive (see ``_CANCEL_STRATEGIES``) from
    # a separate thread, then wait for the executor thread to return the
    # connection before disposing the pool.
    _inflight_sync_conns: set[Any] = dataclasses.field(default_factory=set, init=False)
    _inflight_sync_lock: threading.Lock = dataclasses.field(default_factory=threading.Lock, init=False)
    _cancel_strategy: _CancelStrategy | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.engine.dialect.name in _DDL_SERIAL_DIALECTS:
            self._ddl_lock = asyncio.Lock()
        # Pick a cancel strategy from the appropriate registry for this
        # engine type.  Sync engines need help cancelling executor-thread
        # queries; async engines may also need help if their driver
        # doesn't self-cancel on asyncio task cancel (e.g. aiosqlite).
        if self.engine_type == "sync":
            strategy_cls: type[_CancelStrategy] | None = _SYNC_CANCEL_STRATEGIES.get(self.engine.dialect.name)
        else:
            strategy_cls = _ASYNC_CANCEL_STRATEGIES.get(self.engine.dialect.name)
        if strategy_cls is not None:
            self._cancel_strategy = strategy_cls(self)

        # Track raw DBAPI connections via pool checkout/checkin events for
        # sync engines.  This covers the full lifetime of a checked-out
        # connection, including setup inside ``engine.begin()`` before
        # our own code runs — important because cancellation can arrive
        # at any moment.
        if self.engine_type == "sync":
            sync_engine = self.engine
        else:
            sync_engine = self.engine.sync_engine  # type: ignore[union-attr]

        def _on_checkout(dbapi_conn: Any, _rec: Any, _proxy: Any) -> None:
            with self._inflight_sync_lock:
                self._inflight_sync_conns.add(dbapi_conn)

        def _on_checkin(dbapi_conn: Any, _rec: Any) -> None:
            with self._inflight_sync_lock:
                self._inflight_sync_conns.discard(dbapi_conn)

        event.listen(sync_engine, "checkout", _on_checkout)
        event.listen(sync_engine, "checkin", _on_checkin)

    @classmethod
    def from_url(
        cls,
        url: str | SQLAlchemyURL,
        *,
        max_concurrency_per_db: int = 8,
        dbms_semaphore: asyncio.Semaphore | None = None,
        read_only: bool = True,
        duckdb_init_sql: list[str] | None = None,
        **engine_kwargs: Any,
    ) -> "ThrottledEngine":
        """Build a SQLAlchemy engine from ``url`` and wrap it.

        Centralises engine creation (async vs sync dialect selection,
        DuckDB connect_args, DuckDB on-connect pragmas) so callers
        don't have to juggle a bare SQLAlchemy engine alongside a
        :class:`ThrottledEngine`.

        Args:
            url: SQLAlchemy database URL, sync or async (e.g.
                ``"duckdb:///:memory:"`` or
                ``"postgresql+asyncpg://..."``).
            max_concurrency_per_db: Cap on concurrent queries against
                this database.  Also the underlying pool size.
            dbms_semaphore: Optional semaphore shared across all
                engines targeting the same DBMS, for global rate
                shaping.
            read_only: When True and the URL is a DuckDB file, opens in
                native read-only mode so no file lock is held.
            duckdb_init_sql: Optional list of SQL statements to run on
                every fresh DuckDB connection (e.g.
                ``"INSTALL spatial; LOAD spatial;"``).
            **engine_kwargs: Extra kwargs forwarded to
                :func:`sqlalchemy.create_engine` /
                :func:`sqlalchemy.ext.asyncio.create_async_engine`.

        Returns:
            A :class:`ThrottledEngine` wrapping the new engine.
        """
        engine_kwargs.setdefault("echo", False)  # avoid excessive logging from engine

        # Open DuckDB in native read-only mode so it doesn't hold a file lock.
        if read_only and str(url).startswith("duckdb"):
            connect_args = engine_kwargs.setdefault("connect_args", {})
            connect_args.setdefault("read_only", True)

        engine_type: Literal["async", "sync"] = "async" if _is_async_url(url) else "sync"
        engine: AsyncEngine | sqlalchemy.engine.Engine
        if engine_type == "async":
            engine = create_async_engine(url, pool_size=max_concurrency_per_db, **engine_kwargs)
        else:
            engine = create_engine(url, pool_size=max_concurrency_per_db, **engine_kwargs)

        # DuckDB prints a noisy progress bar to stdout for long-running
        # queries; suppress it so it doesn't pollute pipeline logs.
        # Also set file_search_path so relative paths inside views
        # (e.g. read_csv_auto('data/foo.csv')) resolve against the
        # database file's directory rather than the process CWD.
        if str(url).startswith("duckdb"):
            url_str = str(url)
            db_dir = os.path.dirname(os.path.abspath(url_str.replace("duckdb:///", "", 1)))
            sync_engine = engine.sync_engine if isinstance(engine, AsyncEngine) else engine

            def _duckdb_on_connect(dbapi_conn: Any, _rec: Any) -> None:
                dbapi_conn.execute("PRAGMA enable_progress_bar=false")
                if db_dir:
                    dbapi_conn.execute(f"SET file_search_path='{db_dir}'")
                for sql in duckdb_init_sql or []:
                    dbapi_conn.execute(sql)

            event.listen(sync_engine, "connect", _duckdb_on_connect)

        db_semaphore = asyncio.Semaphore(max_concurrency_per_db)
        return cls(engine_type, engine, dbms_semaphore, db_semaphore)

    async def aclose(self, timeout: float = 5.0) -> None:
        """Cancel any in-flight sync queries, wait for their executor
        threads to release their connections, then dispose the engine.

        This is the right shutdown primitive for sync dialects: a bare
        ``engine.dispose()`` cannot close connections still checked out
        by a running executor thread, leaving zombie connections that
        collide with subsequent opens on the same file (e.g. DuckDB's
        "different configuration" error).  For a clean shutdown with no
        in-flight work this is a fast no-op past the small grace
        period.

        Note: ``loop.run_in_executor`` wraps the thread's future in an
        asyncio Future that is considered "done" the moment it's
        cancelled, even while the thread keeps running.  Awaiting those
        asyncio futures is unreliable — we poll the raw-connection set
        instead, since a connection is only removed after
        ``_execute_sync_engine`` / ``_run_inspector`` exits its
        ``with engine.begin()`` / ``.connect()`` block (i.e. the thread
        has actually finished).

        Args:
            timeout: Maximum seconds to wait for executor threads to
                release their connections after cancellation.  Past
                this deadline the engine is disposed regardless.
        """
        # Small grace period so any executor thread that was mid-checkout at
        # cancel time has a chance to register its connection with our
        # ``checkout`` event listener before we start polling.  Without this,
        # the poll may see an empty set and exit before the thread finishes
        # acquiring the connection it's about to run a query on.
        await asyncio.sleep(0.05)
        await self._cancel_inflight()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._inflight_sync_lock:
                if not self._inflight_sync_conns:
                    break
            await asyncio.sleep(0.02)
            # Re-issue cancel: some threads may have entered checkout after
            # our first call to ``_cancel_inflight``.
            await self._cancel_inflight()
        if self.engine_type == "async":
            await self.engine.dispose()  # type: ignore[misc]
        else:
            self.engine.dispose()

    @asynccontextmanager
    async def throttle(self, *, ddl: bool = False) -> AsyncGenerator[None, None]:
        """Acquire concurrency semaphores (and optionally the DDL lock).

        Args:
            ddl: When True and the engine's dialect requires DDL
                serialization (DuckDB, SQLite), acquire a per-engine lock
                so that concurrent DDL statements don't cause catalog
                write-write conflicts.
        """
        locks: list[asyncio.Lock | asyncio.Semaphore] = []
        if ddl and self._ddl_lock is not None:
            locks.append(self._ddl_lock)
        if self.dbms_semaphore is not None:
            locks.append(self.dbms_semaphore)
        if self.db_semaphore is not None:
            locks.append(self.db_semaphore)
        for lock in locks:
            await lock.acquire()
        try:
            yield
        finally:
            for lock in reversed(locks):
                lock.release()

    async def execute_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = None,
        return_df: bool = False,
        max_rows: int | None = None,
    ) -> QueryResult:
        """Execute a query with timeout and cancellation routed through
        the dialect's :class:`_CancelStrategy`.

        Cancellation / timeout contract:

        * ``CancelledError`` and ``timeout=`` share one code path —
          timeout is "cancel after N seconds."  Both abort the
          in-flight query via the dialect's strategy, then unwind.
        * Statements run inside ``engine.begin()`` — on cancel, the
          transaction rolls back **if the dialect is transactional**.
          Postgres / DuckDB / SQLite / MSSQL-in-explicit-txn: full
          rollback.  **MySQL and Oracle DDL auto-commit per
          statement** — cancel stops execution but cannot undo what
          already committed (a dialect property, not a flaw here).
        * After cancel, the connection is usable for the next call.
          On dialects where cancel kills the session (MSSQL), the pool
          fetches a fresh connection.
        * Multi-statement strings cancel at the currently-running
          statement; statements not yet reached don't execute.
        * Procedural blocks (Snowflake Scripting, PL/SQL, T-SQL
          batches) are one statement to the driver; cancel aborts the
          whole block at the next break point.

        Args:
            query: A raw SQL string or a SQLAlchemy ``Executable``.
            parameters: Bind parameters.  Raw strings must use the
                driver's native paramstyle (e.g. ``%(name)s`` for
                pyformat).
            timeout: Per-query deadline in seconds.  ``None`` disables.
            return_df: Wrap rows in a ``pandas.DataFrame``.
            max_rows: Maximum rows to materialize. ``None`` disables the limit.

        Returns:
            A :class:`QueryResult` carrying rows (or DataFrame) and
            elapsed latency.

        Raises:
            asyncio.CancelledError: If the awaiting task is cancelled.
            ResultTooLargeError: If the result exceeds ``max_rows``.
            TimeoutError: If ``timeout`` expires.
        """
        if max_rows is not None and max_rows < 1:
            raise ValueError("max_rows must be positive or None")
        ddl = isinstance(query, str) and _contains_ddl_statement(query)
        async with self.throttle(ddl=ddl):
            t0 = time.time()
            outcome = await self._dispatch_with_cancel(
                sync_inner=lambda box: self._execute_sync_engine(query, parameters, return_df, max_rows, box),
                async_inner=lambda box: self._execute_async_engine(query, parameters, return_df, max_rows, box),
                timeout=timeout,
                timeout_label=f"Query {query}",
            )
            return QueryResult(
                result=outcome.result,
                latency_seconds=time.time() - t0,
                affected_rows=outcome.affected_rows,
            )

    async def run_with_conn_async(
        self,
        callback: Callable[[sqlalchemy.engine.Connection], _T],
        *,
        ddl: bool = False,
        timeout: int | None = None,
    ) -> _T:
        """Run a sync callable inside the engine's transaction + throttle
        + cancel-strategy plumbing.

        Use this for operations that don't fit ``execute_async`` —
        pandas ``to_sql``, multi-step DBAPI sequences, or anything that
        needs a live ``Connection`` rather than a single SQL string.
        The callback receives a sync ``Connection``; for async engines
        it is bridged via ``conn.run_sync``.

        Cancellation / timeout semantics match :meth:`execute_async`.

        Args:
            callback: Sync callable taking a ``Connection`` and returning
                ``_T``.
            ddl: When True and the dialect requires DDL serialization,
                acquire the per-engine DDL lock.
            timeout: Per-call deadline in seconds.  ``None`` disables.
        """
        async with self.throttle(ddl=ddl):
            return await self._dispatch_with_cancel(
                sync_inner=lambda box: self._run_callback_sync_engine(callback, box),
                async_inner=lambda box: self._run_callback_async_engine(callback, box),
                timeout=timeout,
                timeout_label="Operation",
            )

    async def _dispatch_with_cancel(
        self,
        *,
        sync_inner: Callable[[list[Any]], _T],
        async_inner: Callable[[list[Any]], Coroutine[Any, Any, _T]],
        timeout: int | None,
        timeout_label: str,
    ) -> _T:
        """Run an inner worker (sync via executor, async via task) with
        the cancel-handle dance: shield from outer cancel propagation,
        abort the captured handle on cancel/timeout, then drain the
        inner.

        Both ``sync_inner`` and ``async_inner`` receive a
        ``cancel_handle_box`` (a single-element list) into which they
        publish the dialect's cancel handle once captured.

        Shielding the inner is essential: without it, ``Task.cancel()``
        cascades into the inner's ``async with engine.begin()``
        ``__aexit__``, whose rollback can raise ``OperationalError``
        *over* our ``CancelledError``.  With shield we (1) see the
        cancel cleanly, (2) abort via the strategy first so the
        connection is in a known state, then (3) cancel the inner
        explicitly so it unwinds.
        """
        cancel_handle_box: list[Any] = [None]
        inner: asyncio.Future[Any]
        if self.engine_type == "async":
            inner = asyncio.create_task(async_inner(cancel_handle_box))
        else:
            loop = asyncio.get_running_loop()
            inner = loop.run_in_executor(None, sync_inner, cancel_handle_box)
        try:
            return await asyncio.wait_for(asyncio.shield(inner), timeout=timeout)
        except (asyncio.CancelledError, asyncio.TimeoutError) as exc:
            await self._abort_handle(cancel_handle_box[0])
            if not inner.done():
                inner.cancel()
            # Drain to suppress "Task was destroyed but it is pending".
            with contextlib.suppress(BaseException):
                await inner
            if isinstance(exc, asyncio.TimeoutError):
                raise TimeoutError(f"{timeout_label} timed out after {timeout} seconds") from exc
            raise

    def _execute_sync_engine(
        self,
        statement: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
        max_rows: int | None = None,
        cancel_handle_box: list[Any] | None = None,
    ) -> _ExecOutcome:
        is_write, is_dml = _classify_statement(statement)
        with self.engine.begin() as conn:  # type: ignore
            # Publish the dialect's cancel handle so the calling task can
            # abort this specific query on cancel/timeout.  We deliberately
            # do NOT clear the box on success: it is a one-shot owned by
            # ``execute_async`` and GC'd when that returns; an eager
            # clear here would race the outer cancel handler reading it.
            if cancel_handle_box is not None and self._cancel_strategy is not None:
                try:
                    cancel_handle_box[0] = self._cancel_strategy.capture(conn)
                except Exception:
                    logger.debug("capture failed for %s", self._cancel_strategy.dialect_name, exc_info=True)
            if isinstance(statement, str):
                # exec_driver_sql avoids sqlalchemy.text() parameter parsing,
                # which misinterprets :identifier patterns (Snowflake Scripting
                # variables, VARIANT path access) as bind parameters.  Params
                # must use the driver's native paramstyle (e.g. %(name)s).
                result = conn.exec_driver_sql(statement, parameters or None)
            else:
                result = conn.execute(statement, parameters)
            # Non-row-returning statements (DDL/DML) have no result set;
            # fetchall() would raise ResourceClosedError.  A ``None`` result
            # distinguishes a succeeded DDL/DML from an empty SELECT.
            if not result.returns_rows:
                return _ExecOutcome(result=None, affected_rows=_rowcount_affected(result.rowcount, is_dml))
            return _build_row_outcome(_fetch_rows(result, max_rows), list(result.keys()), return_df, is_write, is_dml)

    async def _execute_async_engine(
        self,
        statement: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
        max_rows: int | None = None,
        cancel_handle_box: list[Any] | None = None,
    ) -> _ExecOutcome:
        """Async-engine query path.  Mirrors :meth:`_execute_sync_engine` for the
        async case: optionally publishes a cancel handle (via the
        strategy's :meth:`_CancelStrategy.acapture`) so the calling task
        can abort this specific query on cancel/timeout.
        """
        is_write, is_dml = _classify_statement(statement)
        async with self.engine.begin() as conn:  # type: ignore
            # See _execute_sync_engine for the box-ownership rationale.
            if cancel_handle_box is not None and self._cancel_strategy is not None:
                try:
                    cancel_handle_box[0] = await self._cancel_strategy.acapture(conn)
                except Exception:
                    logger.debug("acapture failed for %s", self._cancel_strategy.dialect_name, exc_info=True)
            if isinstance(statement, str):
                result = await conn.exec_driver_sql(statement, parameters or None)
                # Non-row-returning statements (DDL/DML) have no result set;
                # fetchall() would raise ResourceClosedError.
                if not result.returns_rows:
                    return _ExecOutcome(result=None, affected_rows=_rowcount_affected(result.rowcount, is_dml))
                rows = _fetch_rows(result, max_rows)
            elif is_write:
                # A write Executable (UPDATE/INSERT/DELETE/DDL) is not row-returning
                # in general — ``conn.stream`` would raise "does not return rows".
                # Execute it and read the affected count from rowcount instead.
                wresult = await conn.execute(statement, parameters)
                if not wresult.returns_rows:
                    return _ExecOutcome(result=None, affected_rows=_rowcount_affected(wresult.rowcount, is_dml))
                rows = _fetch_rows(wresult, max_rows)  # e.g. UPDATE ... RETURNING
                keys = list(wresult.keys())
                return _build_row_outcome(rows, keys, return_df, is_write, is_dml)
            else:
                rows = []
                result = await conn.stream(statement, parameters)
                async for row in result:
                    rows.append(row)
                    if max_rows is not None and len(rows) > max_rows:
                        raise ResultTooLargeError(max_rows)
            keys = list(result.keys())

        # Reaching here means a result set: the string path returned early on the
        # non-row case, and the streaming path is only used for row-returning
        # Executables. ``_build_row_outcome`` folds a driver's ``Count``
        # write-result back to a non-row outcome (see :meth:`_execute_sync_engine`).
        return _build_row_outcome(rows, keys, return_df, is_write, is_dml)

    def _run_callback_sync_engine(
        self,
        callback: Callable[[sqlalchemy.engine.Connection], Any],
        cancel_handle_box: list[Any] | None = None,
    ) -> Any:
        """Sync-engine worker for :meth:`run_with_conn_async` — opens a
        transactional connection, publishes the cancel handle, runs the
        callback.  See ``_execute_sync_engine`` for the box-ownership
        rationale."""
        with self.engine.begin() as conn:  # type: ignore
            if cancel_handle_box is not None and self._cancel_strategy is not None:
                try:
                    cancel_handle_box[0] = self._cancel_strategy.capture(conn)
                except Exception:
                    logger.debug("capture failed for %s", self._cancel_strategy.dialect_name, exc_info=True)
            return callback(conn)

    async def _run_callback_async_engine(
        self,
        callback: Callable[[sqlalchemy.engine.Connection], Any],
        cancel_handle_box: list[Any] | None = None,
    ) -> Any:
        """Async-engine worker for :meth:`run_with_conn_async` — opens a
        transactional connection, publishes the cancel handle, then
        bridges the sync callback via ``conn.run_sync``."""
        async with self.engine.begin() as conn:  # type: ignore
            if cancel_handle_box is not None and self._cancel_strategy is not None:
                try:
                    cancel_handle_box[0] = await self._cancel_strategy.acapture(conn)
                except Exception:
                    logger.debug("acapture failed for %s", self._cancel_strategy.dialect_name, exc_info=True)
            return await conn.run_sync(callback)

    async def _abort_handle(self, handle: Any) -> None:
        """Abort one in-flight query via the dialect's cancellation
        strategy.

        Strategies own their async behaviour: simple in-process
        primitives (DuckDB / SQLite ``interrupt()``) run inline, while
        network-I/O ones (Postgres / Snowflake / BigQuery / MySQL) run
        in a worker thread.  No-op if the dialect has no registered
        strategy.
        """
        if handle is None or self._cancel_strategy is None:
            return
        await self._cancel_strategy.aabort(handle)

    async def _cancel_inflight(self) -> None:
        """Abort every in-flight sync-driver query on this engine.

        Used by :meth:`aclose` for full engine shutdown.  Per-call
        cancellation should capture the specific handle inside the
        worker and call :meth:`_abort_handle` — aborting *every*
        in-flight query when only one was cancelled would be
        collateral damage.

        Delegates to the strategy's async :meth:`acancel_all`.
        """
        if self._cancel_strategy is None:
            return
        await self._cancel_strategy.acancel_all()


@dataclass
class AsyncInspector:
    """Async wrapper around a SQLAlchemy ``Inspector``.

    Proxies attribute access via ``__getattr__``: ``inspector.get_columns(...)``
    returns a coroutine that runs the matching sync ``Inspector`` method
    through the engine's throttle and either an executor thread (sync
    engines) or ``conn.run_sync`` (async engines, via SQLAlchemy's
    greenlet bridge).  Any inspector method works without a hand-written
    wrapper.
    """

    t_eng: ThrottledEngine

    def __getattr__(self, method: str) -> Any:
        async def _stub_async(*args: Any, **kwargs: Any) -> Any:
            def call(c: Any) -> Any:
                return getattr(inspect(c), method)(*args, **kwargs)

            async with self.t_eng.throttle():
                if self.t_eng.engine_type == "async":
                    async with self.t_eng.engine.connect() as conn:  # type: ignore
                        return await conn.run_sync(call)
                return await asyncio.to_thread(call, self.t_eng.engine)

        return _stub_async


_DATE_PARTITION_PATTERNS = (
    re.compile(r"^(?P<prefix>.*?)(?P<date>\d{8})(?P<suffix>.*?)$"),
    re.compile(r"^(?P<prefix>.*?)(?P<date>\d{6})(?P<suffix>.*?)$"),
    re.compile(r"^(?P<prefix>.*?)(?P<date>\d{4})(?P<suffix>.*?)$"),
)


@dataclass(frozen=True)
class _SchemaIntrospectionOptions:
    include_schema_names: frozenset[str] | None = None
    exclude_schema_names: frozenset[str] = frozenset()
    reuse_date_partition_schemas: bool = False
    schema_reuse_regexes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for pattern in self.schema_reuse_regexes:
            re.compile(pattern)

    def allows_schema(self, schema_name: str | None) -> bool:
        return (
            self.include_schema_names is None or schema_name in self.include_schema_names
        ) and schema_name not in self.exclude_schema_names

    def schema_reuse_groups(self, table_names: list[str]) -> list[list[str]]:
        groups: list[list[str]] = []
        remaining = list(table_names)

        for reuse_pattern in self.schema_reuse_regexes:
            matched = [name for name in remaining if re.match(reuse_pattern, name)]
            if len(matched) > 1:
                groups.append(matched)
                matched_names = set(matched)
                remaining = [name for name in remaining if name not in matched_names]

        if self.reuse_date_partition_schemas:
            for date_pattern in _DATE_PARTITION_PATTERNS:
                by_affixes: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
                for name in remaining:
                    if match := date_pattern.match(name):
                        by_affixes[(match.group("prefix"), match.group("suffix"))].append(name)

                reused = [group for group in by_affixes.values() if len(group) > 1]
                groups.extend(reused)
                reused_names = {name for group in reused for name in group}
                remaining = [name for name in remaining if name not in reused_names]

        groups.extend([name] for name in remaining)
        return groups

    def cache_fingerprint(self) -> str:
        payload = json.dumps(
            {
                "include_schema_names": sorted(self.include_schema_names)
                if self.include_schema_names is not None
                else None,
                "exclude_schema_names": sorted(self.exclude_schema_names),
                "reuse_date_partition_schemas": self.reuse_date_partition_schemas,
                "schema_reuse_regexes": self.schema_reuse_regexes,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def _sql_schema_cache_path(
    config: SQLConnectorConfig,
    global_id: str,
    options: _SchemaIntrospectionOptions = _SchemaIntrospectionOptions(),
) -> Path:
    stats_policy = "column-stats" if config.collect_column_stats else "no-column-stats"
    variant = f"{stats_policy}+{options.cache_fingerprint()}"
    return get_schema_cache_path(config.cache_dir, global_id, variant=variant)


def _sql_dialect_for_backend(backend: str) -> SQLDialect:
    candidate = _SQL_DIALECT_BY_BACKEND.get(backend, backend)
    try:
        return _SQL_DIALECT_ADAPTER.validate_python(candidate)
    except ValidationError as e:
        raise ValueError(f"Unsupported SQLAlchemy dialect: {backend!r}") from e


async def _load_schema_async(
    global_id: str,
    db_name: str,
    t_eng: ThrottledEngine,
    config: SQLConnectorConfig,
    options: _SchemaIntrospectionOptions,
    description: str | None = None,
) -> SQLSchema:
    """Load the database schema, using the on-disk cache when available
    and enabled.

    Reads the cache variant matching the configured column-statistics
    policy if it exists and caching is enabled; otherwise introspects the
    live database via :func:`_build_schema_async`, writes the result back
    to the cache (when caching is enabled and the schema is non-empty),
    and returns it.

    Args:
        global_id: Unique identifier used as the cache filename and
            the per-database lock key.
        db_name: Human-readable database name stored in
            ``schema.name``.
        t_eng: The :class:`ThrottledEngine` whose schema to load.
        config: Connector cache and schema-introspection policy.
        options: Source-specific schema scope and structural reuse assumptions.
        description: Optional database description stored in
            ``schema.description``.

    Returns:
        The loaded :class:`SQLSchema`.

    Raises:
        FileNotFoundError: If schema cache mode is ``cache_only`` and the
            cache file is missing.
    """
    cache_path = _sql_schema_cache_path(config, global_id, options)

    async with cache_lock(cache_path):
        dialect = _sql_dialect_for_backend(t_eng.engine.dialect.name)

        if config.schema_cache_mode in ("read_write", "cache_only") and cache_path.exists():
            try:
                return await read_cached_model(cache_path, SQLSchema)
            except (ValidationError, UnicodeError) as e:
                if config.schema_cache_mode == "cache_only":
                    raise RuntimeError(f"Required schema cache is invalid: {cache_path}") from e
                logger.warning("Removing invalid schema cache entry: %s", cache_path)
                await remove_cached_file(cache_path)

        if config.schema_cache_mode == "cache_only":
            raise FileNotFoundError(f"Schema cache required but not found at {cache_path}")

        schema = await _build_schema_async(
            t_eng,
            db_name,
            dialect,
            options,
            collect_column_stats=config.collect_column_stats,
            query_timeout_seconds=config.query_timeout_seconds,
        )
        if t_eng.engine_type == "async":
            await t_eng.engine.dispose()  # type: ignore
        else:
            t_eng.engine.dispose()
        if description:
            schema.description = description
        if config.schema_cache_mode in ("read_write", "refresh") and schema.tables:
            await write_cached_model(cache_path, schema)
        return schema


def _convert(value: Any) -> str | int | float | bool:
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        # Strip lone surrogate code points that are invalid in UTF-8 (breaks Pydantic JSON serialization)
        return value.encode("utf-8", errors="replace").decode("utf-8")
    return str(value)


def _denorm(t_eng: ThrottledEngine, name: str | Any) -> str:
    """Denormalize a normalized identifier back to its actual stored form as a plain str."""
    if getattr(t_eng.engine.dialect, "requires_name_normalize", False):
        return str(t_eng.engine.dialect.denormalize_name(name))
    return str(name)


_ENUMERATION_TYPES = frozenset({"TEXT", "VARCHAR", "STRING", "ENUM"})

# Column types whose values may contain nested JSON / semi-structured data
JSON_TYPES = [
    "VARIANT",  # Snowflake
    "OBJECT",  # Snowflake
    "ARRAY",  # Snowflake, BigQuery, PostgreSQL, DuckDB
    "STRUCT",  # BigQuery (RECORD/STRUCT), DuckDB
    "MAP",  # DuckDB
    "JSON",  # MySQL, PostgreSQL, SQLite, DuckDB, BigQuery
    "JSONB",  # PostgreSQL
    "SUPER",  # Redshift
    "SQL_VARIANT",  # SQL Server
]

# Text column types that might contain JSON (detected via heuristic sampling)
TEXT_TYPES = [
    "TEXT",
    "VARCHAR",
    "NVARCHAR",
    "STRING",
    "CLOB",
]

# Only use DISTINCT on known-safe scalar types. Complex/LOB/semi-structured
# types are handled without DISTINCT to avoid cross-dialect comparability errors.
DISTINCT_SAFE_TYPES = {
    "BOOLEAN",
    "TINYINT",
    "SMALLINT",
    "INTEGER",
    "BIGINT",
    "INT",
    "INT2",
    "INT4",
    "INT8",
    "NUMERIC",
    "BIGNUMERIC",
    "DECIMAL",
    "FLOAT",
    "REAL",
    "DOUBLE",
    "DOUBLE_PRECISION",
    "DATE",
    "TIME",
    "DATETIME",
    "TIMESTAMP",
    "TIMESTAMPTZ",
    "TIMESTAMP_NTZ",
    "TIMESTAMP_LTZ",
    "TIMESTAMP_TZ",
    "CHAR",
    "VARCHAR",
    "NCHAR",
    "NVARCHAR",
    "STRING",
    "ENUM",
    "UUID",
    "BINARY",
    "VARBINARY",
    "BYTES",
}

_PROFILE_SAMPLE_ROWS = 1000
_STORED_SAMPLE_ROWS = 10


def _canonicalize_dtype(native: str) -> str:
    """Map a dialect-native type string into a canonical uppercase atomic token.

    The result is matched against _ENUMERATION_TYPES / JSON_TYPES /
    DISTINCT_SAFE_TYPES, so it must use the canonical names those
    constants use (e.g. ``ARRAY``, ``STRUCT``, ``DECIMAL``, ``VARCHAR``).

    Strips parameter lists (``DECIMAL(18,2)`` → ``DECIMAL``) and collapses
    array notations (``JSON[]``, ``ARRAY<STRING>``, ``STRUCT(...)[]``) to
    ``ARRAY``.
    """
    s = native.strip()
    up = s.upper()
    if up.endswith("[]"):
        return "ARRAY"
    # BigQuery: ARRAY<STRING>, STRUCT<a INT64> — strip from the angle bracket
    angle = up.find("<")
    if angle >= 0:
        up = up[:angle]
    paren = up.find("(")
    if paren >= 0:
        up = up[:paren]
    return up.strip()


async def _catalog_native_dtype_async(
    t_eng: ThrottledEngine,
    schema_name: str | None,
    table_name: str,
    column_name: str,
) -> str | None:
    """Recover a column's native type by querying the dialect's catalog.

    Used when SQLAlchemy's ``TypeEngine.compile`` fails because the
    inspector returned ``NullType`` (e.g. ``duckdb_engine`` on ``LIST`` /
    ``STRUCT`` / ``MAP`` — Mause/duckdb_engine#654).

    Returns ``None`` if the dialect has no implemented fallback or the
    lookup fails.
    """
    dialect = t_eng.engine.dialect.name
    if dialect != "duckdb":
        return None

    stmt = text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column "
        "AND (:schema IS NULL OR table_schema = :schema)"
    )
    try:
        result = await t_eng.execute_async(
            stmt,
            parameters={"table": table_name, "column": column_name, "schema": schema_name},
        )
    except Exception:
        logger.debug(
            f"native dtype catalog lookup failed for {schema_name}.{table_name}.{column_name}",
            exc_info=True,
        )
        return None
    rows = result.result
    if not rows or rows[0][0] is None:
        return None
    return str(rows[0][0])


async def _resolve_native_dtype_async(
    t_eng: ThrottledEngine,
    schema_name: str | None,
    table_name: str,
    column: dict[str, Any],
) -> str | None:
    """Best-effort native type string for a column.

    Tries the dialect-agnostic ``TypeEngine.compile`` first, then falls
    back to the dialect's catalog for cases where SQLAlchemy lost the
    type (``NullType``).
    """
    try:
        return str(column["type"].compile(dialect=t_eng.engine.dialect))
    except sqlalchemy.exc.CompileError:
        pass
    return await _catalog_native_dtype_async(t_eng, schema_name, table_name, column["name"])


async def _build_column_structure_async(
    t_eng: ThrottledEngine,
    column: dict[str, Any],
    table_name: str,
    schema_name: str | None,
) -> SQLColumnSchema:
    dtype = column["type"].__visit_name__.upper()
    if dtype == "USER_DEFINED":
        dtype = type(column["type"]).__name__.upper()
    native_dtype = await _resolve_native_dtype_async(t_eng, schema_name, table_name, column)
    if dtype == "NULL" and native_dtype is not None:
        # The inspector failed to translate the native type (e.g. duckdb_engine
        # on LIST/STRUCT/MAP). Canonicalize from the native string so the
        # categorical type-class checks below still work.
        dtype = _canonicalize_dtype(native_dtype)

    return SQLColumnSchema(
        name=_denorm(t_eng, column["name"]),
        dtype=dtype,
        native_dtype=native_dtype,
        nullable=column["nullable"],
        examples=[],
    )


def _qualified_name(schema_name: str | None, table_name: str, column_name: str | None = None) -> str:
    return ".".join(name for name in (schema_name, table_name, column_name) if name is not None)


async def _try_profile_query_async(
    t_eng: ThrottledEngine,
    query: sqlalchemy.sql.expression.Executable,
    *,
    timeout: int | None,
    operation: str,
    return_df: bool = False,
) -> QueryResult | None:
    try:
        return await t_eng.execute_async(query, timeout=timeout, return_df=return_df)
    except (TimeoutError, DBAPIError) as e:
        logger.warning("Could not %s: %s", operation, e)
        return None


def _enrich_column_from_sample(column: SQLColumnSchema, sampled_df: pd.DataFrame) -> SQLColumnSchema:
    if column.name not in sampled_df.columns:
        return column
    values: list[Any] = sampled_df[column.name].dropna().tolist()
    examples: list[Any] = []
    for value in values:
        converted = _convert(value)
        if converted not in examples:
            examples.append(converted)
        if len(examples) == 5:
            break
    is_json_type = column.dtype in JSON_TYPES
    is_text_with_json = column.dtype in TEXT_TYPES and looks_like_json(examples)
    json_schema = infer_json_schema(values) if values and (is_json_type or is_text_with_json) else None
    return column.model_copy(update={"examples": examples, "json_schema": json_schema})


async def _collect_column_stats_async(
    t_eng: ThrottledEngine,
    column: SQLColumnSchema,
    table_name: str,
    schema_name: str | None,
    num_rows: int,
    query_timeout_seconds: int | None,
) -> SQLColumnSchema:
    tbl = sqlalchemy.table(table_name, sqlalchemy.column(column.name), schema=schema_name)
    col = tbl.c[column.name]
    null_ratio: float | None = None
    num_unique: int | None = None

    if num_rows > 0:
        result = await _try_profile_query_async(
            t_eng,
            select(func.count()).select_from(tbl).where(col.is_(None)),
            timeout=query_timeout_seconds,
            operation=f"collect null ratio for {_qualified_name(schema_name, table_name, column.name)}",
        )
        if result is not None:
            num_null = result.rows[0][0]
            null_ratio = num_null / num_rows

    if column.dtype in DISTINCT_SAFE_TYPES:
        if num_rows == 0:
            num_unique = 0
        else:
            result = await _try_profile_query_async(
                t_eng,
                select(func.count(distinct(col))).select_from(tbl),
                timeout=query_timeout_seconds,
                operation=f"collect distinct count for {_qualified_name(schema_name, table_name, column.name)}",
            )
            if result is not None:
                num_unique = int(result.rows[0][0])

    examples = column.examples
    if column.dtype in _ENUMERATION_TYPES and num_unique is not None and 0 < num_unique <= 20:
        result = await _try_profile_query_async(
            t_eng,
            select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(num_unique),
            timeout=query_timeout_seconds,
            operation=f"collect categorical values for {_qualified_name(schema_name, table_name, column.name)}",
        )
        if result is not None:
            examples = [_convert(row[0]) for row in result.rows]

    unique_ratio = num_unique / num_rows if num_unique is not None and num_rows > 0 else None
    return column.model_copy(
        update={
            "null_ratio": null_ratio,
            "num_unique": num_unique,
            "unique_ratio": unique_ratio,
            "examples": examples,
        }
    )


async def _build_table_async(
    t_eng: ThrottledEngine,
    table_name: str,
    schema_name: str | None,
    is_view: bool = False,
    collect_column_stats: bool = False,
    query_timeout_seconds: int | None = 300,
) -> SQLTableSchema | None:
    async_inspector = AsyncInspector(t_eng)
    try:
        col_dicts = await async_inspector.get_columns(table_name, schema=schema_name)
    except Exception as e:
        logger.warning(f"Skipping table {schema_name}.{table_name}: failed to introspect columns: {e}")
        return None

    if t_eng.engine.dialect.name == "bigquery":
        col_dicts = [c for c in col_dicts if "." not in c["name"]]

    if not col_dicts:
        logger.warning(f"Skipping table {schema_name}.{table_name}: no columns found")
        return None

    columns = await asyncio.gather(
        *[
            _build_column_structure_async(
                t_eng,
                col,
                table_name,
                schema_name,
            )
            for col in col_dicts
        ]
    )

    tbl = sqlalchemy.table(table_name, schema=schema_name)
    sample_result = await _try_profile_query_async(
        t_eng,
        select("*").select_from(tbl).limit(_PROFILE_SAMPLE_ROWS),
        timeout=query_timeout_seconds,
        operation=f"sample relation {_qualified_name(schema_name, table_name)}",
        return_df=True,
    )
    if sample_result is not None:
        profile_sample = sample_result.result
        assert isinstance(profile_sample, pd.DataFrame)
        columns = [_enrich_column_from_sample(column, profile_sample) for column in columns]
        sampled_df = profile_sample.head(_STORED_SAMPLE_ROWS)
    else:
        sampled_df = None

    num_rows = None
    if collect_column_stats and not is_view:
        count_result = await _try_profile_query_async(
            t_eng,
            select(func.count()).select_from(tbl),
            timeout=query_timeout_seconds,
            operation=f"collect row count for table {_qualified_name(schema_name, table_name)}",
        )
        if count_result is not None:
            num_rows = int(count_result.rows[0][0])
            columns = await asyncio.gather(
                *[
                    _collect_column_stats_async(
                        t_eng,
                        column,
                        table_name,
                        schema_name,
                        num_rows,
                        query_timeout_seconds,
                    )
                    for column in columns
                ]
            )

    primary_key = (await async_inspector.get_pk_constraint(table_name, schema=schema_name))["constrained_columns"]

    foreign_keys = []
    for fk in await async_inspector.get_foreign_keys(table_name, schema=schema_name):
        foreign_keys.append(
            ForeignKeySchema(
                columns=[_denorm(t_eng, c) for c in fk["constrained_columns"]],
                foreign_schema_name=_denorm(t_eng, fk["referred_schema"])
                if fk["referred_schema"] is not None
                else None,
                foreign_table=_denorm(t_eng, fk["referred_table"]),
                foreign_columns=[_denorm(t_eng, c) for c in fk["referred_columns"]],
            )
        )
    return SQLTableSchema(
        name=table_name,
        schema_name=schema_name,
        is_view=is_view,
        columns=columns,
        primary_key=[_denorm(t_eng, c) for c in primary_key],
        num_rows=num_rows,
        foreign_keys=foreign_keys,
        sampled_df=sampled_df,
    )


async def _normalize_duckdb_schema_names(t_eng: ThrottledEngine, schema_names: list[str | None]) -> list[str | None]:
    """Strip the database prefix from duckdb-engine schema names.

    ``duckdb-engine`` flattens DuckDB's 3-level hierarchy (database, schema,
    table) into SQLAlchemy's 2-level model by returning ``"database.schema"``
    from ``get_schema_names()``.  This function strips the database prefix and
    filters to only schemas belonging to the current database.
    """

    def _get_current_db() -> str | None:
        with t_eng.engine.connect() as conn:  # type: ignore
            return conn.execute(sqlalchemy.text("SELECT current_database()")).scalar()

    current_db = await asyncio.to_thread(_get_current_db)

    result: list[str | None] = []
    for s in schema_names:
        if s and "." in s:
            db_part, schema_part = s.split(".", 1)
            if current_db and db_part.strip('"') != current_db:
                continue
            result.append(schema_part)
        else:
            result.append(s)
    return result


async def _build_schema_async(
    t_eng: ThrottledEngine,
    db_name: str,
    dialect: SQLDialect,
    options: _SchemaIntrospectionOptions,
    collect_column_stats: bool = False,
    query_timeout_seconds: int | None = 300,
) -> SQLSchema:
    t0 = time.time()
    logger.info(f"Building schema for {db_name}...")
    async_inspector = AsyncInspector(t_eng)

    schema_names: list[str | None]
    if dialect in ["sqlite", "mysql"]:
        schema_names = [None]
    else:
        schema_names = [_denorm(t_eng, name) for name in await async_inspector.get_schema_names()]

    if dialect == "duckdb":
        schema_names = await _normalize_duckdb_schema_names(t_eng, schema_names)

    schema_names = [s for s in schema_names if not (s and s.lower() == "information_schema")]
    schema_names = [name for name in schema_names if options.allows_schema(name)]

    # Discover table/view names for all schemas concurrently
    discovery_results = await asyncio.gather(
        *[
            asyncio.gather(
                async_inspector.get_table_names(schema=schema_name),
                async_inspector.get_view_names(schema=schema_name),
            )
            for schema_name in schema_names
        ]
    )

    jobs: list[tuple[str | None, list[str], bool]] = []

    for schema_name, (raw_table_names, raw_view_names) in zip(schema_names, discovery_results):
        table_names = [_denorm(t_eng, name) for name in raw_table_names]
        view_names = [_denorm(t_eng, name) for name in raw_view_names]

        for names, is_view in ((table_names, False), (view_names, True)):
            groups = options.schema_reuse_groups(names)
            reused_groups = [group for group in groups if len(group) > 1]
            if reused_groups:
                logger.info(
                    "Schema %s: reusing representative schemas for %d families spanning %d relations",
                    schema_name,
                    len(reused_groups),
                    sum(len(group) for group in reused_groups),
                )
            for group in groups:
                jobs.append((schema_name, group, is_view))

    with warnings.catch_warnings(record=True):
        # Capture Snowflake's "failed to reflect" warnings; let all others pass through normally
        warnings.filterwarnings("always", message="Failed to reflect", category=SAWarning)
        warnings.filterwarnings("always", message="Did not recognize type", category=SAWarning)
        results = await asyncio.gather(
            *(
                _build_table_async(
                    t_eng,
                    group[0],
                    schema_name,
                    is_view=is_view,
                    collect_column_stats=collect_column_stats,
                    query_timeout_seconds=query_timeout_seconds,
                )
                for schema_name, group, is_view in jobs
            ),
            return_exceptions=True,
        )

    tables = []
    for (_, group, _), table in zip(jobs, results):
        if table is None:
            continue
        if isinstance(table, BaseException):
            logger.warning(f"Skipping table {group[0]}: {table}")
            continue
        tables.append(table)
        for table_name in group[1:]:
            copied = table.model_copy(deep=True)
            copied.name = table_name
            copied.num_rows = None
            copied.sampled_df = None
            for col in copied.columns:
                col.null_ratio = None
                col.num_unique = None
                col.unique_ratio = None
                col.examples = []
                col.json_schema = None
            tables.append(copied)

    logger.info(f"Time taken to build schema for {db_name}: {time.time() - t0} seconds")
    return SQLSchema(name=db_name, dialect=dialect, tables=tables)


def _preserve_sql_descriptions(previous: SQLSchema, refreshed: SQLSchema) -> None:
    refreshed.description = refreshed.description or previous.description
    previous_tables = {(table.schema_name, table.name): table for table in previous.tables}
    for table in refreshed.tables:
        previous_table = previous_tables.get((table.schema_name, table.name))
        if previous_table is None:
            continue
        table.description = table.description or previous_table.description
        previous_columns = {column.name: column for column in previous_table.columns}
        for column in table.columns:
            previous_column = previous_columns.get(column.name)
            if previous_column is not None:
                column.description = column.description or previous_column.description


@dataclass
class SQLConnector:
    """Schema-aware async SQL database client.

    Combines:

    - a :class:`ThrottledEngine` for cancellable, throttled query
      execution across sync and async dialects
    - a live :class:`SQLSchema` introspected at construction and
      refreshed on demand (with optional disk cache)
    - read-only safety guards for borderline queries
    - optional query result caching

    For raw query execution without the schema / caching layer, use
    :class:`ThrottledEngine` directly — that's what the loaders do
    when building a connector from source files.

    Suitable as the database layer for any tool that needs both query
    execution and live schema metadata: NL2SQL agents, schema
    browsers, query-by-example UIs, ETL jobs, catalog-aware data
    pipelines.

    Raw SQL strings go to the DBAPI driver via ``exec_driver_sql``,
    bypassing SQLAlchemy's parameter parsing — procedural blocks
    (Snowflake Scripting, PL/SQL, T-SQL batches) and dialect-specific
    ``:identifier`` syntax work unchanged.

    Attributes:
        global_id: Stable, filename-safe identity used by caches.
        schema: Current introspected SQL schema.
        backend: Concrete SQLAlchemy database backend.
        language: SQL dialect reported by the schema.
        config: Resolved immutable connector configuration.
        read_only: Whether read-only behavior was requested. This is a
            client-side safety guard unless the backend enforces it natively.
    """

    connector_type: ClassVar[Literal["sql"]] = "sql"
    global_id: str
    # ``schema`` is *live state*: ``refresh_schema_async`` and
    # ``write_dataframe_async`` replace this attribute with a fresh
    # :class:`SQLSchema` object.  External code holding a reference to
    # the old object will see stale data — re-read ``connector.schema``
    # after any operation that may mutate the database.
    schema: SQLSchema
    _t_eng: ThrottledEngine
    config: SQLConnectorConfig = dataclasses.field(default_factory=SQLConnectorConfig)
    read_only: bool = True
    _schema_introspection: _SchemaIntrospectionOptions = dataclasses.field(default_factory=_SchemaIntrospectionOptions)
    # Optional cleanup the loader registers (e.g. "delete the DuckDB
    # cache file I generated for this connector").  Called from
    # ``close_async`` after the engine is closed.  Lets loaders own
    # their resource lifecycle without leaking loader-specific
    # vocabulary into ``SQLConnector``.
    _on_close: Callable[[], None] | None = None
    _schema_lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)
    _closed: bool = dataclasses.field(default=False, init=False)

    @property
    def backend(self) -> str:
        """Return the SQLAlchemy database backend name."""
        return self._t_eng.engine.dialect.name

    @property
    def language(self) -> SQLDialect:
        """Return the connector's SQL dialect."""
        assert self.schema.dialect is not None
        return self.schema.dialect

    async def _save_schema_cache_async(self) -> None:
        """Write the current schema to the cache file if caching is enabled."""
        if self.config.schema_cache_mode in ("read_write", "refresh"):
            cache_path = _sql_schema_cache_path(self.config, self.global_id, self._schema_introspection)
            async with cache_lock(cache_path):
                await write_cached_model(cache_path, self.schema)

    @classmethod
    async def from_url_async(
        cls,
        url: str | SQLAlchemyURL,
        *,
        db_name: str,
        global_id: str | None = None,
        read_only: bool = True,
        config: SQLConnectorConfig | None = None,
        schema: SQLSchema | None = None,
        include_schema_names: Sequence[str] | None = None,
        exclude_schema_names: Sequence[str] = (),
        reuse_date_partition_schemas: bool = False,
        schema_reuse_regexes: Sequence[str] = (),
        dbms_semaphore: asyncio.Semaphore | None = None,
        description: str | None = None,
        duckdb_init_sql: Sequence[str] = (),
        **engine_kwargs: Any,
    ) -> "SQLConnector":
        """Asynchronously create a SQLConnector from a database URL.

        Creates a SQLAlchemy engine (async or sync) wrapped in a
        :class:`ThrottledEngine` with concurrency control, and optionally loads
        the database schema if one is not provided.

        Args:
            url: The database URL (string or :class:`SQLAlchemyURL`).
            db_name: Human-readable database name used in ``schema.name``.
            global_id: Globally unique, filename-safe identifier for this
                database connection and its caches. Derived from the
                credential-free URL when omitted.
            read_only: If ``True`` (the default), write statements (INSERT,
                UPDATE, DELETE, DROP, etc.) recognized by the client guard are
                rejected before reaching the database. This is not a security
                boundary; use read-only credentials or IAM for enforcement.
            config: Immutable connector execution and cache policy. Environment
                values and built-in defaults are used when omitted.
            schema: A pre-loaded :class:`SQLSchema`.  When ``None`` the schema
                is loaded (and cached) automatically via
                :func:`_load_schema_async`.
            include_schema_names: Optional allowlist of schemas to introspect.
            exclude_schema_names: Schemas to omit from introspection.
            reuse_date_partition_schemas: If ``True``, date-suffixed table
                families reuse one representative's structural schema.
            schema_reuse_regexes: Regexes defining additional table families
                whose members are asserted to share one structural schema.
            dbms_semaphore: Optional semaphore shared across connectors to
                limit aggregate DBMS concurrency.
            description: Optional database description stored in the schema
                and persisted to the schema cache.
            duckdb_init_sql: SQL statements to run on each new DuckDB
                connection.
            **engine_kwargs: Additional keyword arguments forwarded to the
                SQLAlchemy engine constructor (e.g. ``pool_pre_ping``).

        Returns:
            A fully initialised :class:`SQLConnector` instance ready to
            execute queries.
        """
        global_id = validate_global_id(global_id or _global_id_from_url(str(url)))
        config = SQLConnectorConfig() if config is None else config
        if not read_only and config.query_cache_mode != "off":
            raise ValueError("Query caching requires read_only=True")
        if "pool_size" in engine_kwargs:
            raise TypeError("Configure SQL query concurrency through SQLConnectorConfig.max_query_concurrency")
        introspection = _SchemaIntrospectionOptions(
            include_schema_names=frozenset(include_schema_names) if include_schema_names is not None else None,
            exclude_schema_names=frozenset(exclude_schema_names),
            reuse_date_partition_schemas=reuse_date_partition_schemas,
            schema_reuse_regexes=tuple(schema_reuse_regexes),
        )
        t_eng = ThrottledEngine.from_url(
            url,
            max_concurrency_per_db=config.max_query_concurrency,
            dbms_semaphore=dbms_semaphore,
            read_only=read_only,
            duckdb_init_sql=list(duckdb_init_sql),
            **engine_kwargs,
        )
        # If anything below raises (or the awaiting task is cancelled
        # mid-schema-build), dispose ``t_eng`` — leaving it alive would
        # leak zombie executor threads holding DuckDB connections that
        # collide with subsequent opens.  ``aclose`` cancels in-flight
        # work and disposes the pool; we suppress its own errors so they
        # don't mask the original construction failure.
        try:
            # Eagerly open one connection to surface file-lock errors (DuckDB)
            # or credential / network issues immediately rather than at first query.
            await t_eng.execute_async("SELECT 1")

            if schema is None:
                schema = await _load_schema_async(
                    global_id,
                    db_name,
                    t_eng,
                    config,
                    introspection,
                    description=description,
                )
            if schema.dialect is None:
                raise ValueError("SQL connector schema must declare its dialect")
            return cls(
                global_id,
                schema,
                t_eng,
                config=config,
                read_only=read_only,
                _schema_introspection=introspection,
            )
        except BaseException:
            try:
                await t_eng.aclose()
            except Exception:
                logger.debug("aclose during construction failed", exc_info=True)
            raise

    def _set_close_hook(self, callback: Callable[[], None]) -> None:
        self._on_close = callback

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError("SQLConnector is closed")

    async def release_connections_async(self) -> None:
        """Release pooled connections while keeping the connector reusable."""
        self._check_open()
        await self._t_eng.aclose()

    async def close_async(self) -> None:
        """Permanently close the connector and release its resources.

        For read-write DuckDB connectors, this releases the file-level
        lock so external processes (e.g. ``dbt run``) can acquire a write
        lock.  Read-only connectors already use DuckDB's native read-only
        mode and do not hold a lock.

        A loader-owned cleanup hook, when present, runs after the engine closes.
        """
        if self._closed:
            return
        await self._t_eng.aclose()
        self._closed = True
        if self._on_close is not None:
            try:
                self._on_close()
            except Exception:
                logger.debug("close callback failed", exc_info=True)
            self._on_close = None

    async def refresh_schema_async(
        self,
        tables: list[TableRef] | None = None,
    ) -> SQLSchema:
        """Re-introspect the live database and update ``self.schema``.

        Use after DDL mutations (e.g. ``dbt run`` creating new tables) to
        make the connector's schema reflect the current database state.
        Also updates the on-disk schema cache when caching is enabled.

        Args:
            tables: If provided, only (re-)build schemas for these tables
                (or views) and merge them into the existing schema —
                replacing any entry with a matching name, and appending
                truly new ones. If ``None``, do a full rebuild.

        Returns:
            The updated :class:`SQLSchema`.
        """
        self._check_open()
        if tables is not None:
            tables = [ref for ref in tables if self._schema_introspection.allows_schema(ref.schema_name)]
            if not tables:
                return self.schema
        async with self._schema_lock:
            previous = self.schema
            if tables is not None:
                async_inspector = AsyncInspector(self._t_eng)
                view_names_by_schema: dict[str | None, set[str]] = {}
                for ref in tables:
                    if ref.schema_name not in view_names_by_schema:
                        raw_views = await async_inspector.get_view_names(schema=ref.schema_name)
                        view_names_by_schema[ref.schema_name] = {_denorm(self._t_eng, v) for v in raw_views}

                new_tables = await asyncio.gather(
                    *[
                        _build_table_async(
                            self._t_eng,
                            ref.table_name,
                            ref.schema_name,
                            is_view=ref.table_name in view_names_by_schema.get(ref.schema_name, set()),
                            collect_column_stats=self.config.collect_column_stats,
                            query_timeout_seconds=self.config.query_timeout_seconds,
                        )
                        for ref in tables
                    ]
                )

                requested = {(ref.schema_name, ref.table_name) for ref in tables}
                kept = [t for t in self.schema.tables if (t.schema_name, t.name) not in requested]
                for t in new_tables:
                    if t is not None:
                        kept.append(t)

                refreshed = SQLSchema(
                    name=self.schema.name,
                    dialect=self.schema.dialect,
                    tables=kept,
                )
            else:
                refreshed = await _build_schema_async(
                    self._t_eng,
                    self.schema.name,
                    self.schema.dialect,  # type: ignore[arg-type]
                    self._schema_introspection,
                    collect_column_stats=self.config.collect_column_stats,
                    query_timeout_seconds=self.config.query_timeout_seconds,
                )

            _preserve_sql_descriptions(previous, refreshed)
            self.schema = refreshed
            await self._save_schema_cache_async()

            logger.info(f"Schema refreshed for {self.global_id}: {len(self.schema.tables)} tables")
            return self.schema

    async def _default_schema_label_async(self) -> str | None:
        """Schema label an unqualified object resolves to under this connector.

        Mirrors the per-dialect schema labelling in :func:`_build_schema_async`
        so a table written with ``schema_name=None`` is recorded under the same
        label a full re-introspection would assign it. Without this, the live
        database resolves the unqualified write to its default schema (e.g.
        DuckDB's ``main``) while the in-memory schema records it under a
        ``None`` label — surfacing as a spurious schema-less ``(default)``
        entry alongside the real ``main`` one.
        """
        dialect = self.language
        # _build_schema_async collapses these single-logical-schema dialects to a
        # ``None`` label, so unqualified writes must resolve to None to match.
        if dialect in ("sqlite", "mysql"):
            return None

        raw = await self._t_eng.run_with_conn_async(lambda conn: inspect(conn).default_schema_name)
        if raw is None:
            return None
        if dialect == "duckdb":
            normalized = await _normalize_duckdb_schema_names(self._t_eng, [raw])
            return normalized[0] if normalized else None
        return _denorm(self._t_eng, raw)

    async def write_dataframe_async(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema_name: str | None = None,
        mode: Literal["append", "replace"] = "append",
    ) -> int:
        """Write a DataFrame into a database table.

        On success, automatically refreshes ``self.schema`` for the
        target table via :meth:`refresh_schema_async` so the connector
        reflects the new column types and (for ``mode="replace"``) the
        new table identity.  This costs one extra round trip per write
        — callers that batch many writes may prefer to skip per-write
        refresh and call :meth:`refresh_schema_async` once at the end.

        Args:
            df: DataFrame to persist.
            table_name: Destination table name.
            schema_name: Optional destination schema name.
            mode: Write mode. ``append`` inserts rows into an existing table
                (or creates one if missing). ``replace`` recreates the table.

        Returns:
            Number of rows written.

        Raises:
            ValueError: If ``table_name`` is empty, ``mode`` is invalid, or
                the connector is read-only.
        """
        self._check_open()
        if self.read_only:
            raise ValueError("write_dataframe_async is blocked when read_only=True")
        if not table_name.strip():
            raise ValueError("table_name must be non-empty")
        if mode not in {"append", "replace"}:
            raise ValueError(f"Unsupported mode: {mode!r}")

        if_exists: Literal["append", "replace"] = "replace" if mode == "replace" else "append"

        def write(conn: sqlalchemy.engine.Connection) -> None:
            df.to_sql(
                name=table_name,
                con=conn,
                schema=schema_name,
                if_exists=if_exists,
                index=False,
                method="multi",
            )

        await self._t_eng.run_with_conn_async(write)

        # Resolve None to the schema the live DB actually wrote into, so the
        # in-memory schema label matches a full re-introspection (avoids a
        # spurious ``(default)`` entry shadowing the real default schema).
        effective_schema = schema_name if schema_name is not None else await self._default_schema_label_async()
        await self.refresh_schema_async(tables=[TableRef(schema_name=effective_schema, table_name=table_name)])

        return len(df)

    async def _execute_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any],
        timeout: int | None,
    ) -> ExecResult:
        try:
            result = await self._t_eng.execute_async(
                query,
                parameters,
                timeout,
                return_df=True,
                max_rows=self.config.max_result_rows,
            )
        except Exception as e:
            return ExecResult(error=ErrorInfo(exc_type=type(e).__name__, message=str(e)))
        return ExecResult(
            df=result.result,
            latency_seconds=result.latency_seconds,
            affected_rows=result.affected_rows,
        )

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None | object = _UNSET,
    ) -> ExecResult:
        """Execute a query and return the result.

        Raw SQL strings are sent to the DBAPI driver via
        ``exec_driver_sql``, bypassing SQLAlchemy's ``text()`` parameter
        parsing.  This allows procedural / scripting blocks (e.g.
        Snowflake Scripting ``DECLARE … BEGIN … END``) and
        ``:identifier`` patterns (e.g. VARIANT path access) to be
        executed without interference.

        Two surfaces stop a running query, both routed through the
        dialect's cancel strategy (``interrupt()``, ``cancel()``,
        ``KILL QUERY``, ``cursor.cancel()``, …):

        - ``timeout=N`` — per-query deadline.  On expiry the query is
          aborted and the returned :class:`ExecResult` carries
          ``error.exc_type == "TimeoutError"``.  Query-level failures
          (timeouts, syntax errors, …) are returned in
          ``ExecResult.error``, never raised.
        - ``asyncio.Task.cancel()`` on the awaiting task — the caller
          wants the query to stop.  ``CancelledError`` is
          ``BaseException`` and propagates through this method
          unchanged.  Wrap the call in a Task to cancel it from
          elsewhere (see Example below).

        See :meth:`ThrottledEngine.execute_async` for the full
        transaction / rollback contract, including the caveat that
        **MySQL and Oracle DDL auto-commit per statement** — cancel
        stops execution but cannot undo committed effects on those
        dialects.

        Args:
            query: A raw SQL string or a SQLAlchemy ``Executable``.
            parameters: Bind parameters.  For raw SQL strings these must
                use the driver's native paramstyle (e.g. ``%(name)s``
                for pyformat drivers).
            timeout: Query timeout in seconds. When omitted, use the connector
                configuration; ``None`` explicitly disables the timeout. On
                expiry, the result's ``error.exc_type`` is
                ``"TimeoutError"`` (not raised).

        Returns:
            An :class:`ExecResult` containing the result DataFrame (or
            an error) and latency information.

        Raises:
            asyncio.CancelledError: If the awaiting task was cancelled.
                Propagates as-is; not wrapped in :class:`ExecResult`.

        Example:
            Cancel a long-running query from elsewhere (e.g. a Ctrl+C
            handler or an external trigger):

            .. code-block:: python

                task = asyncio.create_task(
                    connector.run_query_async("SELECT ... long-running")
                )
                # ... on Ctrl+C / external trigger:
                task.cancel()
                try:
                    result = await task
                except asyncio.CancelledError:
                    ...  # query was aborted server-side
        """
        self._check_open()
        effective_timeout = self.config.query_timeout_seconds if timeout is _UNSET else timeout
        assert isinstance(effective_timeout, int) or effective_timeout is None

        # --- read-only guard (checks every statement in multi-statement strings) ---
        query_str = str(query) if not isinstance(query, str) else query
        if self.read_only:
            write_keyword = _contains_write_statement(query_str)
            if write_keyword:
                return ExecResult(
                    error=ErrorInfo(
                        exc_type="ReadOnlyViolationError",
                        message=f"Write statement blocked (read_only=True): {write_keyword} ...",
                    ),
                )

        if self.config.query_cache_mode == "off":
            return await self._execute_query_async(query, parameters, effective_timeout)

        key = query_cache_key(query_str, parameters, effective_timeout, self.config.max_result_rows)
        path = query_cache_path(self.config.cache_dir, self.global_id, key)
        async with cache_lock(path):
            if self.config.query_cache_mode == "read_write" and path.exists():
                try:
                    cached = await read_cached_model(path, ExecResult)
                except (ValidationError, UnicodeError):
                    logger.warning("Removing invalid query cache entry: %s", path)
                    await remove_cached_file(path)
                else:
                    if cached.df is None or cached.error is not None:
                        await remove_cached_file(path)
                    else:
                        logger.debug("Query cache hit: %s", query_str[:80])
                        return cached.model_copy(update={"latency_seconds": None})

            result = await self._execute_query_async(query, parameters, effective_timeout)
            if result.df is not None:
                await write_cached_model(path, result)
                logger.debug("Query cache write: %s", query_str[:80])
            return result
