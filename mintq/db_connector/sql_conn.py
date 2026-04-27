import copy
import hashlib
import json
import re
import logging
import threading
import warnings

import sqlparse
from typing import Any, ClassVar, Sequence, Mapping, Literal, AsyncGenerator
import dataclasses
from dataclasses import dataclass
import collections
import pandas as pd
import os
import time
import asyncio
import contextlib
from contextlib import asynccontextmanager
import sqlalchemy
from sqlalchemy.exc import SAWarning
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine, event, select, func, distinct, inspect
from mintq.schema import (
    ErrorInfo,
    SQLDialect,
    SQLSchema,
    SQLColumnSchema,
    SQLTableSchema,
    ForeignKeySchema,
    ExecResult,
    TableRef,
)

from mintq.config import mintq_config, ColumnStatsMode
from mintq.db_connector.utils import infer_json_schema, looks_like_json

logger = logging.getLogger(__name__)

# Statements that modify data or schema.  The pattern matches the first
# non-whitespace, non-comment keyword in a single SQL statement.
_WRITE_STATEMENT_RE = re.compile(
    r"^\s*"
    r"(?:--[^\n]*\n\s*|/\*.*?\*/\s*)*"  # skip leading SQL comments
    r"(?P<keyword>"
    r"INSERT|UPDATE|DELETE|MERGE|UPSERT|REPLACE"  # DML
    r"|CREATE|ALTER|DROP|TRUNCATE|RENAME"  # DDL
    r"|GRANT|REVOKE"  # DCL
    r"|CALL|EXECUTE(?!\s+IMMEDIATE\b)|EXEC(?!UTE)"  # stored procs (not EXECUTE IMMEDIATE)
    r"|COPY|LOAD|UNLOAD|PUT|GET|REMOVE"  # bulk / file ops (Snowflake, etc.)
    r"|ATTACH|DETACH"  # database attachment
    r")\b",
    re.IGNORECASE | re.DOTALL,
)


def _contains_write_statement(query: str) -> re.Match[str] | None:
    """Check every statement in a (possibly multi-statement) query string.

    Uses ``sqlparse.split`` to split on statement boundaries and tests each
    fragment against ``_WRITE_STATEMENT_RE``.  Returns the first match found,
    or ``None`` if all statements are read-only.
    """
    for stmt in sqlparse.split(query):
        m = _WRITE_STATEMENT_RE.match(stmt)
        if m:
            return m
    return None


# DDL statements that modify the catalog. Used to serialize DDL on dialects
# with optimistic concurrency (DuckDB, SQLite) where concurrent DDL on the
# same object causes write-write conflict errors.
_DDL_STATEMENT_RE = re.compile(
    r"^\s*"
    r"(?:--[^\n]*\n\s*|/\*.*?\*/\s*)*"  # skip leading SQL comments
    r"(?:CREATE|ALTER|DROP|TRUNCATE|RENAME|ATTACH|DETACH)\b",
    re.IGNORECASE | re.DOTALL,
)

# Dialects that need DDL serialization.
_DDL_SERIAL_DIALECTS = frozenset({"duckdb", "sqlite"})


def _contains_ddl_statement(query: str) -> bool:
    """Return True if any statement in the query is a DDL operation."""
    for stmt in sqlparse.split(query):
        if _DDL_STATEMENT_RE.match(stmt):
            return True
    return False


_db_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)
_query_cache: dict[str, ExecResult] = {}
_query_cache_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)


@dataclass
class QueryResult:
    result: list[tuple[Any, ...]] | pd.DataFrame
    latency_seconds: float


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
# commits).  Add a subclass below when this matters for a new dialect.


class _CancelStrategy:
    """Base class for per-dialect cancellation strategies.

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

    name: str = "default"

    def __init__(self, engine: "ThrottledEngine") -> None:
        self.engine = engine
        self.install()

    def install(self) -> None:
        """Hook for one-time setup (e.g. registering SQLAlchemy event
        listeners).  Default: nothing."""
        return None

    def capture(self, conn: sqlalchemy.engine.Connection) -> Any:
        """Extract the cancel handle from a *sync* SQLAlchemy connection.
        Called inside the executor thread that runs ``_run_query_sync_engine``.

        Default: the raw DBAPI connection.  Override per dialect.
        """
        return conn.connection.driver_connection

    async def acapture(self, conn: "sqlalchemy.ext.asyncio.AsyncConnection") -> Any:
        """Extract the cancel handle from an *async* SQLAlchemy connection.
        Called on the event loop inside ``_run_query_async_engine``.

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


class _DuckDBCancel(_CancelStrategy):
    name = "duckdb"

    async def aabort(self, handle: Any) -> None:
        try:
            handle.interrupt()  # μs, no thread needed
        except Exception:
            logger.debug("interrupt failed for duckdb", exc_info=True)


class _SqliteCancel(_CancelStrategy):
    name = "sqlite"

    async def aabort(self, handle: Any) -> None:
        try:
            handle.interrupt()  # μs, no thread needed
        except Exception:
            logger.debug("interrupt failed for sqlite", exc_info=True)


class _PostgresCancel(_CancelStrategy):
    name = "postgresql"

    async def aabort(self, handle: Any) -> None:
        try:
            await asyncio.to_thread(handle.cancel)  # opens a side TCP conn
        except Exception:
            logger.debug("cancel failed for postgresql", exc_info=True)

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
            self.engine.engine
            if self.engine.engine_type == "sync"
            else self.engine.engine.sync_engine  # type: ignore[union-attr]
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
            logger.debug("cursor cancel failed for %s", self.name, exc_info=True)

    async def acancel_all(self) -> None:
        cursors = list(self._cursors.values())
        # One cancel-HTTP per cursor, fired concurrently.
        await asyncio.gather(
            *(asyncio.to_thread(self._cancel_cursor, c) for c in cursors),
            return_exceptions=True,
        )


class _SnowflakeCancel(_CursorTrackingCancel):
    """Snowflake: HTTP cancel via ``cursor.abort_query()`` (cross-thread safe)."""

    name = "snowflake"

    def _cancel_cursor(self, cursor: Any) -> None:
        cursor.abort_query()


class _BigQueryCancel(_CursorTrackingCancel):
    """BigQuery: ``Job.cancel()`` via the cursor's current ``query_job``.

    The dbapi cursor populates ``query_job`` on ``execute()``;
    :meth:`Job.cancel` issues a REST cancel for the running BigQuery
    job (cross-thread safe — it's just an HTTP call).
    """

    name = "bigquery"

    def _cancel_cursor(self, cursor: Any) -> None:
        job = getattr(cursor, "query_job", None)
        if job is not None:
            job.cancel()


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

    name = "mysql"

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
        sync_engine = self.engine.engine  # type: ignore[assignment]
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
    """asyncmy MySQL: KILL QUERY via a fresh async ``asyncmy.connect``.

    No worker thread — the side connection is async too, so the cancel
    is just a couple of awaits on the event loop.
    """

    async def _kill_one(self, thread_id: int) -> None:
        import asyncmy

        url = self.engine.engine.url  # AsyncEngine.url
        side = await asyncmy.connect(
            host=url.host,
            port=url.port or 3306,
            user=url.username,
            password=url.password or "",
            database=url.database,
        )
        try:
            async with side.cursor() as cur:
                await cur.execute(f"KILL QUERY {thread_id}")
        finally:
            await side.ensure_closed()


class _AsyncSqliteCancel(_CancelStrategy):
    """aiosqlite: ``conn.interrupt()`` on the underlying ``aiosqlite.Connection``.

    aiosqlite runs sqlite3 in a worker thread; an asyncio task cancel
    abandons the await but the worker keeps executing the SQL until
    ``Connection.interrupt()`` is called on the wrapper.  Same shape as
    :class:`_SqliteCancel` but the handle comes from the *async*
    SQLAlchemy connection — the default :meth:`acapture` does the right
    thing (it returns the aiosqlite ``Connection`` via
    ``await conn.get_raw_connection()`` + ``.driver_connection``).

    ``aiosqlite.Connection.interrupt`` is ``async def`` (it dispatches
    to the worker thread), so we ``await`` it.
    """

    name = "sqlite"

    async def aabort(self, handle: Any) -> None:
        try:
            await handle.interrupt()
        except Exception:
            logger.debug("interrupt failed for aiosqlite", exc_info=True)


# Sync-engine strategies — keyed by SQLAlchemy dialect.name.  Selected
# when ``ThrottledEngine.engine_type == "sync"``.
_SYNC_CANCEL_STRATEGIES: dict[str, type[_CancelStrategy]] = {
    "duckdb": _DuckDBCancel,
    "sqlite": _SqliteCancel,
    "postgresql": _PostgresCancel,
    "snowflake": _SnowflakeCancel,
    "bigquery": _BigQueryCancel,
    "mysql": _MySQLCancel,
}

# Async-engine strategies — keyed by SQLAlchemy dialect.name.  Selected
# when ``ThrottledEngine.engine_type == "async"``.  Dialects whose async
# driver self-cancels on asyncio task cancel (asyncpg in particular)
# don't need an entry — the absence of a strategy means "trust the
# driver".  Add entries for drivers that need our help: aiosqlite (no
# protocol-level cancel; needs ``interrupt()``), asyncmy (no cancel
# primitive at all; would need KILL QUERY from a side connection — not
# yet implemented).
_ASYNC_CANCEL_STRATEGIES: dict[str, type[_CancelStrategy]] = {
    "sqlite": _AsyncSqliteCancel,
    "mysql": _AsyncMySQLCancel,
}


# Dialect/engine-type pairs known to *need* a strategy — i.e. the driver
# does not self-cancel on asyncio task cancel.  Used by ``__post_init__``
# to log a warning when an engine is built without a registered strategy
# for a combination that's known to need one.  The intent is to make a
# missing strategy noisy rather than silent.
_DIALECTS_NEEDING_STRATEGY: dict[str, set[str]] = {
    "sync": {"duckdb", "sqlite", "postgresql", "snowflake", "bigquery", "mysql"},
    # Async drivers: asyncpg self-cancels on task cancel; aiosqlite and
    # asyncmy don't (and we provide strategies for them).  Add new
    # async dialects here as they're integrated.
    "async": {"sqlite", "mysql"},
}


@dataclass
class ThrottledEngine:
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
            strategy_cls: type[_CancelStrategy] | None = _SYNC_CANCEL_STRATEGIES.get(
                self.engine.dialect.name
            )
        else:
            strategy_cls = _ASYNC_CANCEL_STRATEGIES.get(self.engine.dialect.name)
        if strategy_cls is not None:
            self._cancel_strategy = strategy_cls(self)
        elif self.engine.dialect.name in _DIALECTS_NEEDING_STRATEGY[self.engine_type]:
            logger.warning(
                "no cancel strategy registered for %s/%s engine — task cancel "
                "and timeout may not stop a running query",
                self.engine.dialect.name,
                self.engine_type,
            )

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
        """Build an engine from ``url`` and wrap it.

        Centralises engine creation (async vs sync dialect selection,
        DuckDB connect_args, DuckDB on-connect pragmas) so callers don't
        have to juggle a bare SQLAlchemy engine alongside a ThrottledEngine.
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

    @asynccontextmanager
    async def cleanup_on_failure(self) -> AsyncGenerator[None, None]:
        """Run the enclosed block, disposing the engine (with in-flight
        cancellation) only if an exception propagates out.  On clean exit
        the engine stays alive for its owning caller.
        """
        try:
            yield
        except BaseException:
            await self.aclose()
            raise

    async def aclose(self, timeout: float = 5.0) -> None:
        """Cancel any in-flight sync queries, wait for their executor
        threads to release their connections, then dispose the engine.

        This is the right shutdown primitive for sync dialects: a bare
        ``engine.dispose()`` cannot close connections still checked out by
        a running executor thread, leaving zombie connections that collide
        with subsequent opens on the same file (e.g. DuckDB's "different
        configuration" error).  For a clean shutdown with no in-flight
        work this is a fast no-op past the small grace period.

        Note: ``loop.run_in_executor`` wraps the thread's future in an
        asyncio Future that is considered "done" the moment it's cancelled,
        even while the thread keeps running.  That means awaiting the
        asyncio futures is unreliable here — we poll the raw-connection set
        instead, since a connection is only removed after ``_run_query_sync_engine`` /
        ``_run_inspector`` exits its ``with engine.begin()`` / ``.connect()``
        block (i.e. the thread has actually finished).
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

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = None,
        return_df: bool = False,
    ) -> QueryResult:
        """Run a query, with timeout and cancel both routed through the
        same :class:`_CancelStrategy` plumbing.

        Sync engines run the query in an executor thread; async engines
        run it as a coroutine.  Either way:

        * The inner call publishes a cancel handle via
          ``cancel_handle_box`` (when a strategy exists for the dialect).
        * ``asyncio.wait_for`` enforces ``timeout``.
        * On either ``CancelledError`` (caller cancelled the task) or
          ``TimeoutError`` (deadline expired), we abort *just this
          query's* handle via :meth:`_abort_handle` and re-raise.
        """
        ddl = isinstance(query, str) and _contains_ddl_statement(query)
        async with self.throttle(ddl=ddl):
            t0 = time.time()
            cancel_handle_box: list[Any] = [None]
            # Shield the inner from outer cancel propagation: without it,
            # ``Task.cancel()`` cascades into the inner's
            # ``async with engine.begin()`` __aexit__, whose rollback can
            # raise ``OperationalError`` *over* our ``CancelledError``.
            # With shield we (1) see the cancel cleanly, (2) abort via the
            # strategy first so the connection is in a known state, then
            # (3) cancel the inner explicitly so it unwinds.
            inner: asyncio.Future[Any]
            if self.engine_type == "async":
                inner = asyncio.create_task(
                    self._run_query_async_engine(query, parameters, return_df, cancel_handle_box)
                )
            else:
                loop = asyncio.get_running_loop()
                inner = loop.run_in_executor(
                    None, self._run_query_sync_engine, query, parameters, return_df, cancel_handle_box
                )
            try:
                result = await asyncio.wait_for(asyncio.shield(inner), timeout=timeout)
            except (asyncio.CancelledError, asyncio.TimeoutError) as exc:
                await self._abort_handle(cancel_handle_box[0])
                if not inner.done():
                    inner.cancel()
                # Drain to suppress "Task was destroyed but it is pending".
                with contextlib.suppress(BaseException):
                    await inner
                if isinstance(exc, asyncio.TimeoutError):
                    raise TimeoutError(
                        f"Query {query} timed out after {timeout} seconds"
                    ) from exc
                raise
            return QueryResult(result=result, latency_seconds=time.time() - t0)

    def _run_query_sync_engine(
        self,
        statement: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
        cancel_handle_box: list[Any] | None = None,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        with self.engine.begin() as conn:  # type: ignore
            # Publish the dialect's cancel handle so the calling task can
            # abort this specific query on cancel/timeout.  We deliberately
            # do NOT clear the box on success: it is a one-shot owned by
            # ``run_query_async`` and GC'd when that returns; an eager
            # clear here would race the outer cancel handler reading it.
            if cancel_handle_box is not None and self._cancel_strategy is not None:
                try:
                    cancel_handle_box[0] = self._cancel_strategy.capture(conn)
                except Exception:
                    logger.debug(
                        "capture failed for %s", self._cancel_strategy.name, exc_info=True
                    )
            if isinstance(statement, str):
                # exec_driver_sql avoids sqlalchemy.text() parameter parsing,
                # which misinterprets :identifier patterns (Snowflake Scripting
                # variables, VARIANT path access) as bind parameters.  Params
                # must use the driver's native paramstyle (e.g. %(name)s).
                result = conn.exec_driver_sql(statement, parameters or None)
            else:
                result = conn.execute(statement, parameters)
            rows = result.fetchall()
            if return_df:
                return pd.DataFrame(rows, columns=result.keys())
            return rows

    async def _run_query_async_engine(
        self,
        statement: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
        cancel_handle_box: list[Any] | None = None,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        """Async-engine query path.  Mirrors :meth:`_run_query_sync_engine` for the
        async case: optionally publishes a cancel handle (via the
        strategy's :meth:`_CancelStrategy.acapture`) so the calling task
        can abort this specific query on cancel/timeout.
        """
        async with self.engine.begin() as conn:  # type: ignore
            # See _run_query_sync_engine for the box-ownership rationale.
            if cancel_handle_box is not None and self._cancel_strategy is not None:
                try:
                    cancel_handle_box[0] = await self._cancel_strategy.acapture(conn)
                except Exception:
                    logger.debug(
                        "acapture failed for %s", self._cancel_strategy.name, exc_info=True
                    )
            if isinstance(statement, str):
                result = await conn.exec_driver_sql(statement, parameters or None)
                rows = list(result.fetchall())
            else:
                rows = []
                result = await conn.stream(statement, parameters)
                async for row in result:
                    rows.append(row)

        if return_df:
            return pd.DataFrame(rows, columns=result.keys())
        return rows

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
    t_eng: ThrottledEngine

    def _run_inspector_conn(
        self,
        conn: sqlalchemy.engine.Connection,
        method: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        inspector = inspect(conn)
        return getattr(inspector, method)(*args, **kwargs)

    def _run_inspector(self, method: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        with self.t_eng.engine.connect() as conn:  # type: ignore
            return self._run_inspector_conn(conn, method, args, kwargs)

    def __getattr__(self, method: str) -> Any:
        async def _stub_async(*args: Any, **kwargs: Any) -> Any:
            async with self.t_eng.throttle():
                if self.t_eng.engine_type == "async":
                    async with self.t_eng.engine.connect() as conn:  # type: ignore
                        return await conn.run_sync(self._run_inspector_conn, method, args, kwargs)
                else:
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(None, self._run_inspector, method, args, kwargs)

        return _stub_async


async def load_schema_with_cache_async(
    global_id: str,
    db_name: str,
    t_eng: ThrottledEngine,
    group_date_partitioned_tables: bool = True,
    group_table_regexes: list[str] = [],
    include_schema_names: list[str] | None = None,
    enable_schema_caching: bool = True,
    column_stats_mode: ColumnStatsMode | None = None,
    description: str | None = None,
) -> SQLSchema:
    """Loads the database schema, utilizing a cache if available and enabled.

    Args:
        enable_schema_caching: If False, skip schema cache read/write
            regardless of global config.  Useful for mutable databases
            where cached schemas would be stale.
        description: Optional database description to store in the schema.
    """
    schema_cache_dir = os.path.join(mintq_config.cache_dir, "schemas")
    os.makedirs(schema_cache_dir, exist_ok=True)
    cache_path = os.path.join(schema_cache_dir, f"{global_id}.json")

    lock = _db_locks[global_id]
    async with lock:
        sqlalchemy_dialect = t_eng.engine.dialect.name
        # SQLAlchemy uses "postgresql"; normalise to our SQLDialect literal "postgres"
        dialect_map: dict[str, str] = {"postgresql": "postgres"}
        dialect = dialect_map.get(sqlalchemy_dialect, sqlalchemy_dialect)

        if (
            enable_schema_caching
            and mintq_config.schema_cache_enabled
            and not mintq_config.schema_cache_overwrite
            and os.path.exists(cache_path)
        ):
            with open(cache_path, "r", encoding="utf-8") as f:
                return SQLSchema.model_validate_json(f.read())

        if enable_schema_caching and mintq_config.schema_cache_required:
            raise FileNotFoundError(f"Schema cache required but not found at {cache_path}")

        schema = await build_schema_async(
            t_eng,
            db_name,
            dialect,  # type: ignore
            group_date_partitioned_tables,
            group_table_regexes,
            column_stats_mode=column_stats_mode if column_stats_mode is not None else mintq_config.column_stats_mode,
            include_schema_names=include_schema_names,
        )
        if t_eng.engine_type == "async":
            await t_eng.engine.dispose()  # type: ignore
        else:
            t_eng.engine.dispose()
        if description:
            schema.description = description
        if enable_schema_caching and mintq_config.schema_cache_enabled and schema.tables:

            def _write_cache() -> None:
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(schema.model_dump_json(indent=2))

            await asyncio.to_thread(_write_cache)
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


# Types that might be categorical
CATEGORICAL_TYPES = [
    "CHAR",
    "VARCHAR",
    "NCHAR",
    "NVARCHAR",
    "STRING",
    "TEXT",
    "CLOB",
    "BOOLEAN",
    "SMALLINT",
    "INTEGER",
    "BIGINT",
    "ENUM",
]

# Column types whose values may contain nested JSON / semi-structured data
JSON_TYPES = [
    "VARIANT",  # Snowflake
    "OBJECT",  # Snowflake
    "ARRAY",  # Snowflake, BigQuery, PostgreSQL, DuckDB
    "STRUCT",  # BigQuery (RECORD/STRUCT), DuckDB
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

# Timeout (seconds) for per-table row-count queries during schema building.
# Views backed by expensive joins can take hours; this prevents hangs.
_TABLE_COUNT_TIMEOUT = 120
_VIEW_COUNT_TIMEOUT = 10

# Number of sample values used to infer JSON schema for semi-structured columns
_JSON_SCHEMA_SAMPLE_SIZE = 1000

# Used when column_stats_mode is either "sample_for_large_tables" or "skip_for_large_tables"
_LARGE_TABLE_THRESHOLD = 1000000
# Used when column_stats_mode is "sample_for_large_tables"
_LARGE_TABLE_SAMPLE_SIZE = 1000000


async def build_column_async(
    t_eng: ThrottledEngine,
    column: dict[str, Any],
    table_name: str,
    schema_name: str | None,
    num_rows: int | None,
    is_view: bool = False,
    column_stats_mode: ColumnStatsMode = "skip_for_large_tables",
) -> SQLColumnSchema:
    tbl: sqlalchemy.sql.expression.FromClause = sqlalchemy.table(
        table_name, sqlalchemy.column(column["name"]), schema=schema_name
    )
    col = tbl.c[column["name"]]
    dtype = column["type"].__visit_name__.upper()
    if dtype == "USER_DEFINED":
        dtype = type(column["type"]).__name__.upper()
    nullable = column["nullable"]
    can_use_distinct = dtype in DISTINCT_SAFE_TYPES

    skip_stats = (
        column_stats_mode == "always_skip"
        or num_rows is None
        or num_rows == 0
        or (column_stats_mode == "skip_for_large_tables" and num_rows > _LARGE_TABLE_THRESHOLD)
    )
    if skip_stats:
        null_ratio = num_unique = unique_ratio = None
    else:
        assert num_rows is not None
        sampled_rows = num_rows
        if column_stats_mode == "sample_for_large_tables" and num_rows > _LARGE_TABLE_THRESHOLD:
            if t_eng.engine.dialect.name in ("snowflake", "postgresql"):
                sample_frac = min(_LARGE_TABLE_SAMPLE_SIZE / num_rows, 1.0)
                sample_pct = max(sample_frac * 100, 0.1)  # sample at least 0.1%
                # Snowflake views only support row-wise sampling (BERNOULLI) without seed
                if t_eng.engine.dialect.name == "snowflake" and is_view:
                    tbl = tbl.tablesample(func.bernoulli(sample_pct))
                else:
                    tbl = tbl.tablesample(func.system(sample_pct))
                col = tbl.c[column["name"]]
                sampled_rows = int(sample_pct / 100 * num_rows)

        num_null = (await t_eng.run_query_async(select(func.count()).select_from(tbl).where(col.is_(None)))).result[0][
            0
        ]
        null_ratio = num_null / sampled_rows

        num_unique = None
        if dtype in CATEGORICAL_TYPES:
            use_snowflake_hll = t_eng.engine.dialect.name == "snowflake" and column_stats_mode != "always_precise"
            if use_snowflake_hll:
                # Efficient estimation using HyperLogLog (returns a float; cast to int)
                num_unique = int((await t_eng.run_query_async(select(func.hll(col)).select_from(tbl))).result[0][0])
            elif can_use_distinct:
                num_unique = (await t_eng.run_query_async(select(func.count(distinct(col))).select_from(tbl))).result[
                    0
                ][0]
        unique_ratio = (num_unique / sampled_rows) if num_unique is not None else None

    examples: list[Any]
    if skip_stats and num_rows is None:
        examples = []
    elif num_rows is not None and num_rows == 0:
        examples = []
    elif dtype in CATEGORICAL_TYPES and num_unique is not None:
        examples = (
            await t_eng.run_query_async(
                select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(min(20, num_unique))
            )
        ).result
        # Note: examples will contain all possible values if cardinality <= 20
        examples = [_convert(row[0]) for row in examples]
    else:
        # Avoids scanning a large table for distinct values while still providing diverse example values.
        subq = select(col.label("_v")).select_from(tbl).where(col.isnot(None)).limit(1000).subquery()
        if can_use_distinct:
            stmt = select(subq.c._v).distinct().limit(5)
        else:
            stmt = select(subq.c._v).limit(5)
        examples = (await t_eng.run_query_async(stmt)).result
        examples = [_convert(row[0]) for row in examples]

    # Infer JSON schema for semi-structured columns (VARIANT, JSON, JSONB, etc.)
    # For text columns (e.g. SQLite TEXT), heuristically detect JSON content from examples.
    json_schema: dict[str, Any] | None = None
    if num_rows is None or num_rows > 0:
        is_json_type = dtype in JSON_TYPES
        is_text_with_json = dtype in TEXT_TYPES and looks_like_json(examples)
        logger.debug(
            f"table {table_name}, column {column['name']}: is_json_type: {is_json_type}, is_text_with_json: {is_text_with_json}"
        )
        if is_json_type or is_text_with_json:
            json_sample_rows = (
                await t_eng.run_query_async(
                    select(col).select_from(tbl).where(col.isnot(None)).limit(_JSON_SCHEMA_SAMPLE_SIZE)
                )
            ).result
            json_sample_values = [row[0] for row in json_sample_rows]
            json_schema = infer_json_schema(json_sample_values)

    return SQLColumnSchema(
        name=_denorm(t_eng, column["name"]),
        dtype=dtype,
        nullable=nullable,
        null_ratio=null_ratio,
        num_unique=num_unique,
        unique_ratio=unique_ratio,
        examples=examples,
        json_schema=json_schema,
    )


async def build_table_async(
    t_eng: ThrottledEngine,
    table_name: str,
    schema_name: str | None,
    is_view: bool = False,
    column_stats_mode: ColumnStatsMode = "skip_for_large_tables",
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

    tbl = sqlalchemy.table(table_name, schema=schema_name)
    if is_view and column_stats_mode == "always_skip":
        num_rows = None
    else:
        count_timeout = _VIEW_COUNT_TIMEOUT if is_view else _TABLE_COUNT_TIMEOUT
        try:
            num_rows = (
                await t_eng.run_query_async(
                    select(func.count()).select_from(tbl),
                    timeout=count_timeout,
                )
            ).result[0][0]
        except (TimeoutError, asyncio.TimeoutError):
            kind = "view" if is_view else "table"
            logger.warning(
                f"COUNT(*) on {kind} {schema_name}.{table_name} timed out after {count_timeout}s; skipping column stats"
            )
            num_rows = None

    columns = await asyncio.gather(
        *[
            build_column_async(
                t_eng, col, table_name, schema_name, num_rows, is_view=is_view, column_stats_mode=column_stats_mode
            )
            for col in col_dicts
        ]
    )
    name2col = {col.name: col for col in columns}

    primary_key = (await async_inspector.get_pk_constraint(table_name, schema=schema_name))["constrained_columns"]
    for col in primary_key:
        name2col[_denorm(t_eng, col)].primary_key_type = "single" if len(primary_key) == 1 else "composite"

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
    for fk in foreign_keys:
        for col in fk.columns:
            name2col[col].foreign_keys.append(fk)

    # Sample rows from the table
    if is_view and column_stats_mode == "always_skip":
        sampled_df = None
    else:
        sampled_df = (await t_eng.run_query_async(select("*").select_from(tbl).limit(10), return_df=True)).result

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


def group_table_names(
    table_names: list[str],
    group_date_partitioned_tables: bool = True,
    group_table_regexes: list[str] = [],
) -> list[list[str]]:
    groups = []
    remaining = table_names

    for regex in group_table_regexes:
        matched = [table_name for table_name in remaining if re.match(regex, table_name)]
        if len(matched) > 1:
            groups.append(matched)
            remaining = [table_name for table_name in remaining if table_name not in matched]

    if group_date_partitioned_tables:
        date_patterns = [
            r"^(?P<prefix>.*?)(?P<date>\d{8})(?P<suffix>.*?)$",
            r"^(?P<prefix>.*?)(?P<date>\d{6})(?P<suffix>.*?)$",
            r"^(?P<prefix>.*?)(?P<date>\d{4})(?P<suffix>.*?)$",
        ]
        for regex in date_patterns:
            affix_groups = collections.defaultdict(list)
            for s in remaining:
                match = re.match(regex, s)
                if match:
                    affix_groups[(match.group("prefix"), match.group("suffix"))].append(s)
            for _, matched in affix_groups.items():
                if len(matched) > 1:
                    groups.append(matched)
                    remaining = [table_name for table_name in remaining if table_name not in matched]

    for t in remaining:
        groups.append([t])

    return groups


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


async def build_schema_async(
    t_eng: ThrottledEngine,
    db_name: str,
    dialect: SQLDialect,
    group_date_partitioned_tables: bool = True,
    group_table_regexes: list[str] = [],
    column_stats_mode: ColumnStatsMode = "skip_for_large_tables",
    include_schema_names: list[str] | None = None,
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
    if include_schema_names is not None:
        allowed = set(include_schema_names)
        schema_names = [s for s in schema_names if s in allowed]

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

    tasks = []
    all_groups = []

    for schema_name, (raw_table_names, raw_view_names) in zip(schema_names, discovery_results):
        table_names = [_denorm(t_eng, name) for name in raw_table_names]
        view_names = [_denorm(t_eng, name) for name in raw_view_names]
        view_name_set = set(view_names)

        groups = group_table_names(table_names + view_names, group_date_partitioned_tables, group_table_regexes)
        if groups:
            logger.info(
                f"Schema {schema_name}: {len(table_names) + len(view_names)} tables/views grouped into {len(groups)} representative tables ({', '.join(f'{g[0]} ({len(g)})' for g in groups)})"
            )
        for group in groups:
            tasks.append(
                asyncio.create_task(
                    build_table_async(
                        t_eng,
                        group[0],
                        schema_name,
                        is_view=group[0] in view_name_set,
                        column_stats_mode=column_stats_mode,
                    )
                )
            )
            all_groups.append(group)

    with warnings.catch_warnings(record=True):
        # Capture Snowflake's "failed to reflect" warnings; let all others pass through normally
        warnings.filterwarnings("always", message="Failed to reflect", category=SAWarning)
        warnings.filterwarnings("always", message="Did not recognize type", category=SAWarning)
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

    tables = []
    for group, table in zip(all_groups, task_results):
        if table is None:
            continue
        if isinstance(table, BaseException):
            logger.warning(f"Skipping table {group[0]}: {table}")
            continue
        tables.append(table)
        for table_name in group[1:]:
            table = copy.deepcopy(table)
            table.name = table_name
            table.num_rows = None
            table.sampled_df = None
            for col in table.columns:
                col.examples = []
            tables.append(SQLTableSchema.model_validate(table.model_dump()))

    logger.info(f"Time taken to build schema for {db_name}: {time.time() - t0} seconds")
    return SQLSchema(name=db_name, dialect=dialect, tables=tables)


@dataclass
class SQLConnector:
    """Database connector that wraps a SQLAlchemy engine with concurrency
    control, schema caching, and query result caching.

    Raw SQL strings are executed via ``exec_driver_sql``, which sends them
    directly to the DBAPI driver without any SQLAlchemy parameter parsing.
    This means procedural / scripting blocks (e.g. Snowflake Scripting
    ``DECLARE … BEGIN … END``, ``EXECUTE IMMEDIATE``) and dialect-specific
    syntax that uses ``:identifier`` patterns (e.g. Snowflake VARIANT path
    access) are fully supported.
    """

    connector_type: ClassVar[Literal["sql"]] = "sql"
    global_id: str
    schema: SQLSchema
    language: SQLDialect
    _t_eng: ThrottledEngine
    read_only: bool = True
    enable_schema_caching: bool = True
    enable_query_caching: bool = False
    _group_date_partitioned_tables: bool = True
    _group_table_regexes: list[str] = dataclasses.field(default_factory=list)
    _include_schema_names: list[str] | None = None
    _column_stats_mode: ColumnStatsMode = "skip_for_large_tables"
    _temp_db_path: str | None = None
    _schema_lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)

    def save_schema_cache(self) -> None:
        """Write the current schema to the cache file if caching is enabled."""
        if self.enable_schema_caching and mintq_config.schema_cache_enabled:
            schema_cache_dir = os.path.join(mintq_config.cache_dir, "schemas")
            os.makedirs(schema_cache_dir, exist_ok=True)
            cache_path = os.path.join(schema_cache_dir, f"{self.global_id}.json")
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(self.schema.model_dump_json(indent=2))

    @classmethod
    async def from_url_async(
        cls,
        global_id: str,
        url: str | SQLAlchemyURL,
        db_name: str,
        max_concurrency_per_db: int = 8,
        dbms_semaphore: asyncio.Semaphore | None = None,
        schema: SQLSchema | None = None,
        group_date_partitioned_tables: bool = True,
        group_table_regexes: list[str] = [],
        read_only: bool = True,
        enable_schema_caching: bool = True,
        enable_query_caching: bool = False,
        include_schema_names: list[str] | None = None,
        column_stats_mode: ColumnStatsMode | None = None,
        duckdb_init_sql: list[str] | None = None,
        description: str | None = None,
        **engine_kwargs: Any,
    ) -> "SQLConnector":
        """Asynchronously create a SQLConnector from a database URL.

        Creates a SQLAlchemy engine (async or sync) wrapped in a
        :class:`ThrottledEngine` with concurrency control, and optionally loads
        the database schema if one is not provided.

        Args:
            global_id: A globally unique identifier for this database connection, also
                used as the cache key when loading the schema.
            url: The database URL (string or :class:`SQLAlchemyURL`).
            db_name: Human-readable database name used in ``schema.name``.
            max_concurrency_per_db: Maximum number of concurrent queries
                allowed against this database.  Also used as the engine's
                ``pool_size``.  Defaults to ``8``.
            dbms_semaphore: An optional semaphore shared across all databases
                to limit overall concurrency.
            schema: A pre-loaded :class:`SQLSchema`.  When ``None`` the schema
                is loaded (and cached) automatically via
                :func:`load_schema_with_cache_async`.
            group_date_partitioned_tables: If ``True``, tables whose names
                share the same prefix and suffix but differ only by a
                date-like numeric segment (8, 6, or 4 digits) are grouped
                together.  Only the first table in each group has its schema
                fully inspected; the remaining tables receive a shallow copy.
                Defaults to ``True``.
            group_table_regexes: A list of regex patterns used to group
                tables.  For each pattern, all table names that match are
                collected into a group.  If a group contains more than one
                table, only the first is fully inspected and the rest receive
                a shallow copy of its schema.
            read_only: If ``True`` (the default), write statements (INSERT,
                UPDATE, DELETE, DROP, etc.) are rejected before reaching the
                database, returning an :class:`ExecResult` with an error.
            enable_schema_caching: If ``False``, skip schema cache
                read/write for this connector regardless of global config.
            enable_query_caching: If ``False``, skip query result caching
                for this connector regardless of global config. Useful for
                interactive use where fresh results are always needed.
            description: Optional database description stored in the schema
                and persisted to the schema cache.
            **engine_kwargs: Additional keyword arguments forwarded to the
                SQLAlchemy engine constructor (e.g. ``pool_pre_ping``).

        Returns:
            A fully initialised :class:`SQLConnector` instance ready to
            execute queries.
        """
        t_eng = ThrottledEngine.from_url(
            url,
            max_concurrency_per_db=max_concurrency_per_db,
            dbms_semaphore=dbms_semaphore,
            read_only=read_only,
            duckdb_init_sql=duckdb_init_sql,
            **engine_kwargs,
        )
        async with t_eng.cleanup_on_failure():
            # Eagerly open one connection to surface file-lock errors (DuckDB)
            # or credential / network issues immediately rather than at first query.
            await t_eng.run_query_async("SELECT 1")

            if schema is None:
                schema = await load_schema_with_cache_async(
                    global_id,
                    db_name,
                    t_eng,
                    group_date_partitioned_tables,
                    group_table_regexes,
                    include_schema_names=include_schema_names,
                    enable_schema_caching=enable_schema_caching,
                    column_stats_mode=column_stats_mode,
                    description=description,
                )
            language: SQLDialect = schema.dialect  # type: ignore[assignment]
            return cls(
                global_id,
                schema,
                language,
                t_eng,
                read_only=read_only,
                enable_schema_caching=enable_schema_caching,
                enable_query_caching=enable_query_caching,
                _group_date_partitioned_tables=group_date_partitioned_tables,
                _group_table_regexes=list(group_table_regexes),
                _include_schema_names=include_schema_names,
                _column_stats_mode=column_stats_mode
                if column_stats_mode is not None
                else mintq_config.column_stats_mode,
            )

    async def disconnect_async(self) -> None:
        """Close all pooled connections in the underlying SQLAlchemy engine.

        For read-write DuckDB connectors, this releases the file-level
        lock so external processes (e.g. ``dbt run``) can acquire a write
        lock.  Read-only connectors already use DuckDB's native read-only
        mode and do not hold a lock.

        After disconnect, ``schema`` remains in memory and SQLAlchemy will
        transparently create new connections on demand.

        If this connector was created with ``_temp_db_path`` set (e.g. via
        :func:`mintq.db_connector.loaders.files.load_files` with no
        ``data_dir``), the temporary DuckDB file is also deleted.
        """
        await self._t_eng.aclose()
        if self._temp_db_path is not None:
            try:
                os.unlink(self._temp_db_path)
            except OSError:
                pass
            self._temp_db_path = None

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
        async with self._schema_lock:
            if tables is not None:
                async_inspector = AsyncInspector(self._t_eng)
                view_names_by_schema: dict[str | None, set[str]] = {}
                for ref in tables:
                    if ref.schema_name not in view_names_by_schema:
                        raw_views = await async_inspector.get_view_names(schema=ref.schema_name)
                        view_names_by_schema[ref.schema_name] = {_denorm(self._t_eng, v) for v in raw_views}

                new_tables = await asyncio.gather(
                    *[
                        build_table_async(
                            self._t_eng,
                            ref.table_name,
                            ref.schema_name,
                            is_view=ref.table_name in view_names_by_schema.get(ref.schema_name, set()),
                            column_stats_mode=self._column_stats_mode,
                        )
                        for ref in tables
                    ]
                )

                requested = {(ref.schema_name, ref.table_name) for ref in tables}
                kept = [t for t in self.schema.tables if (t.schema_name, t.name) not in requested]
                for t in new_tables:
                    if t is not None:
                        kept.append(t)

                self.schema = SQLSchema(
                    name=self.schema.name,
                    dialect=self.schema.dialect,
                    tables=kept,
                )
            else:
                self.schema = await build_schema_async(
                    self._t_eng,
                    self.schema.name,
                    self.schema.dialect,  # type: ignore[arg-type]
                    self._group_date_partitioned_tables,
                    self._group_table_regexes,
                    column_stats_mode=self._column_stats_mode,
                    include_schema_names=self._include_schema_names,
                )

            self.save_schema_cache()

            logger.info(f"Schema refreshed for {self.global_id}: {len(self.schema.tables)} tables")
            return self.schema

    async def write_dataframe_async(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema_name: str | None = None,
        mode: Literal["append", "replace"] = "append",
    ) -> int:
        """Write a DataFrame into a database table.

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
        if self.read_only:
            raise ValueError("write_dataframe_async is blocked when read_only=True")
        if not table_name.strip():
            raise ValueError("table_name must be non-empty")
        if mode not in {"append", "replace"}:
            raise ValueError(f"Unsupported mode: {mode!r}")

        if_exists: Literal["append", "replace"] = "replace" if mode == "replace" else "append"

        async with self._t_eng.throttle():
            if self._t_eng.engine_type == "async":
                async_engine = self._t_eng.engine
                assert isinstance(async_engine, AsyncEngine)
                async with async_engine.begin() as conn:
                    await conn.run_sync(
                        lambda sync_conn: self._write_df_to_sql(
                            df=df,
                            conn=sync_conn,
                            table_name=table_name,
                            schema_name=schema_name,
                            if_exists=if_exists,
                        )
                    )
            else:
                sync_engine = self._t_eng.engine
                cancel_handle_box: list[Any] = [None]
                strategy = self._t_eng._cancel_strategy

                def _write_sync() -> None:
                    with sync_engine.begin() as conn:  # type: ignore[union-attr]
                        # Publish the dialect's cancel handle so an outer
                        # cancel can abort this specific write.
                        if strategy is not None:
                            try:
                                cancel_handle_box[0] = strategy.capture(conn)
                            except Exception:
                                logger.debug(
                                    "capture failed for %s", strategy.name, exc_info=True
                                )
                        self._write_df_to_sql(
                            df=df,
                            conn=conn,
                            table_name=table_name,
                            schema_name=schema_name,
                            if_exists=if_exists,
                        )
                        # See ``_run_query_sync_engine`` for why we don't clear
                        # ``cancel_handle_box`` here.

                loop = asyncio.get_running_loop()
                try:
                    await loop.run_in_executor(None, _write_sync)
                except asyncio.CancelledError:
                    # Abort the write so its transaction is rolled back
                    # rather than allowed to commit in the zombie thread.
                    # Only this call's handle is targeted.
                    await self._t_eng._abort_handle(cancel_handle_box[0])
                    raise

        await self.refresh_schema_async(tables=[TableRef(schema_name=schema_name, table_name=table_name)])

        return len(df)

    @staticmethod
    def _write_df_to_sql(
        *,
        df: pd.DataFrame,
        conn: sqlalchemy.engine.Connection,
        table_name: str,
        schema_name: str | None,
        if_exists: Literal["append", "replace"],
    ) -> None:
        """Write a DataFrame to a SQL table using pandas."""
        df.to_sql(
            name=table_name,
            con=conn,
            schema=schema_name,
            if_exists=if_exists,
            index=False,
            method="multi",
        )

    @staticmethod
    def _query_cache_key(global_id: str, query: str, parameters: Mapping[str, Any], timeout: int | None) -> str:
        """Build a deterministic cache key for a query."""
        key_data = json.dumps(
            {
                "global_id": global_id,
                "query": query.strip(),
                "parameters": dict(sorted(parameters.items())) if parameters else {},
                "timeout": timeout,
            },
            sort_keys=True,
            ensure_ascii=True,
        )
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = None,
    ) -> ExecResult:
        """Execute a query and return the result.

        Raw SQL strings are sent to the DBAPI driver via
        ``exec_driver_sql``, bypassing SQLAlchemy's ``text()`` parameter
        parsing.  This allows procedural / scripting blocks (e.g.
        Snowflake Scripting ``DECLARE … BEGIN … END``) and
        ``:identifier`` patterns (e.g. VARIANT path access) to be
        executed without interference.

        Args:
            query: A raw SQL string or a SQLAlchemy ``Executable``.
            parameters: Bind parameters.  For raw SQL strings these must
                use the driver's native paramstyle (e.g. ``%(name)s``
                for pyformat drivers).
            timeout: Query timeout in seconds. ``None`` means no timeout.

        Returns:
            An :class:`ExecResult` containing the result DataFrame (or
            an error) and latency information.
        """
        # --- read-only guard (checks every statement in multi-statement strings) ---
        query_str = str(query) if not isinstance(query, str) else query
        if self.read_only:
            write_match = _contains_write_statement(query_str)
            if write_match:
                return ExecResult(
                    error=ErrorInfo(
                        exc_type="ReadOnlyViolationError",
                        message=f"Write statement blocked (read_only=True): {write_match.group('keyword').upper()} ...",
                    ),
                )

        # --- query result cache lookup ---
        params_map: Mapping[str, Any] = parameters if isinstance(parameters, Mapping) else {}
        caching_on = self.enable_query_caching and mintq_config.query_cache_enabled
        use_cache = caching_on and not mintq_config.query_cache_overwrite

        cache_hash: str | None = None
        if caching_on:
            cache_hash = self._query_cache_key(self.global_id, query_str, params_map, timeout)
            cache_dir = os.path.join(mintq_config.cache_dir, "query_results")
            cache_path = os.path.join(cache_dir, f"{self.global_id}_{cache_hash}.json")

            if use_cache:
                # Check in-memory cache first
                if cache_hash in _query_cache:
                    logger.debug(f"Query cache hit (memory): {query_str[:80]}")
                    return _query_cache[cache_hash]

                # Check disk cache
                successful_only = mintq_config.query_cache_mode == "successful_only"
                async with _query_cache_locks[cache_hash]:
                    # Re-check memory after acquiring lock
                    if cache_hash in _query_cache:
                        return _query_cache[cache_hash]
                    if os.path.exists(cache_path):
                        with open(cache_path, "r", encoding="utf-8") as f:
                            cached = ExecResult.model_validate_json(f.read())
                        if successful_only and cached.df is None:
                            logger.debug(f"Query cache skip (error in successful_only mode): {query_str[:80]}")
                        else:
                            _query_cache[cache_hash] = cached
                            logger.debug(f"Query cache hit (disk): {query_str[:80]}")
                            return cached

        # --- execute query ---
        df, error, latency_seconds = None, None, None
        try:
            result = await self._t_eng.run_query_async(query, parameters, timeout, return_df=True)
            df = result.result
            latency_seconds = result.latency_seconds
        except Exception as e:
            error = ErrorInfo(exc_type=type(e).__name__, message=str(e))
        exec_result = ExecResult(df=df, error=error, latency_seconds=latency_seconds)

        # --- write to cache ---
        if caching_on and cache_hash is not None:
            skip = mintq_config.query_cache_mode == "successful_only" and exec_result.df is None
            if not skip:
                async with _query_cache_locks[cache_hash]:
                    os.makedirs(cache_dir, exist_ok=True)
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(exec_result.model_dump_json(indent=2))
                    _query_cache[cache_hash] = exec_result
                    logger.debug(f"Query cache write: {query_str[:80]}")

        return exec_result
