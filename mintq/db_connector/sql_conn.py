import copy
import hashlib
import json
import re
import logging
import warnings
from typing import Any, Sequence, Mapping, Literal, AsyncGenerator
from dataclasses import dataclass
import collections
import pandas as pd
import os
import time
import asyncio
from contextlib import asynccontextmanager
import sqlalchemy
from sqlalchemy.exc import SAWarning
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine, select, func, distinct, inspect
from mintq.schema import (
    ErrorInfo,
    SQLDialect,
    SQLSchema,
    SQLColumnSchema,
    SQLTableSchema,
    ForeignKeySchema,
    ExecResult,
)

from mintq.config import mintq_config, ColumnStatsMode
from mintq.db_connector.utils import infer_json_schema, looks_like_json

logger = logging.getLogger(__name__)

# Statements that modify data or schema.  The pattern matches the *first*
# non-whitespace, non-comment keyword in the query.
_WRITE_STATEMENT_RE = re.compile(
    r"^\s*"
    r"(?:--[^\n]*\n\s*|/\*.*?\*/\s*)*"  # skip leading SQL comments
    r"(?P<keyword>"
    r"INSERT|UPDATE|DELETE|MERGE|UPSERT|REPLACE"  # DML
    r"|CREATE|ALTER|DROP|TRUNCATE|RENAME"  # DDL
    r"|GRANT|REVOKE"  # DCL
    r"|CALL|EXECUTE(?!\s+IMMEDIATE\b)|EXEC(?!UTE)"  # stored procs (not EXECUTE IMMEDIATE)
    r"|COPY|LOAD|UNLOAD|PUT|GET|REMOVE"  # bulk / file ops (Snowflake, etc.)
    r")\b",
    re.IGNORECASE | re.DOTALL,
)


_db_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)
_query_cache: dict[str, ExecResult] = {}
_query_cache_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)


@dataclass
class QueryResult:
    result: list[tuple[Any, ...]] | pd.DataFrame
    latency_seconds: float


@dataclass
class ThrottledEngine:
    engine_type: Literal["async", "sync"]
    engine: AsyncEngine | sqlalchemy.engine.Engine
    dbms_semaphore: asyncio.Semaphore | None
    db_semaphore: asyncio.Semaphore | None

    @asynccontextmanager
    async def throttle(self) -> AsyncGenerator[None, None]:
        semaphores = [sem for sem in [self.dbms_semaphore, self.db_semaphore] if sem is not None]
        for sem in semaphores:
            await sem.acquire()
        try:
            yield
        finally:
            for sem in reversed(semaphores):
                sem.release()

    def _run_query_s(
        self,
        statement: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        with self.engine.connect() as conn:  # type: ignore
            if isinstance(statement, str):
                # We use exec_driver_sql to avoid sqlalchemy.text() parameter
                # parsing, which misinterprets :identifier patterns (e.g.
                # Snowflake Scripting variables, VARIANT path access) as bind
                # parameters. exec_driver_sql sends the raw SQL string directly
                # to the DBAPI driver, so parameters (if any) must already use
                # the driver's native paramstyle (e.g. %(name)s for pyformat).
                result = conn.exec_driver_sql(statement, parameters or None)
            else:
                result = conn.execute(statement, parameters)
            rows = result.fetchall()
            if return_df:
                return pd.DataFrame(rows, columns=result.keys())
            return rows

    async def _run_query_a(
        self,
        statement: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        async with self.engine.connect() as conn:  # type: ignore
            if isinstance(statement, str):
                # See _run_query_s for rationale on exec_driver_sql.
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

    def _create_interrupter(self, conn: sqlalchemy.ext.asyncio.AsyncConnection, timeout: int) -> asyncio.Task[None]:
        async def interrupt_after() -> None:
            await asyncio.sleep(timeout)
            raw_conn = await conn.get_raw_connection()
            await raw_conn.driver_connection.interrupt()  # type: ignore

        return asyncio.create_task(interrupt_after())

    async def _run_query_aiosqlite(
        self,
        statement: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
        timeout: int | None = None,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        """The generic wait_for solution does not work for sqlite. We need to use sqlite's native conn.interrupt() mechanism."""
        async with self.engine.connect() as conn:  # type: ignore
            if timeout is not None:
                interrupter = self._create_interrupter(conn, timeout)

            try:
                if isinstance(statement, str):
                    # See _run_query_s for rationale on exec_driver_sql.
                    result = await conn.exec_driver_sql(statement, parameters or None)
                    rows = list(result.fetchall())
                else:
                    rows = []
                    result = await conn.stream(statement, parameters)
                    async for row in result:
                        rows.append(row)
            except sqlalchemy.exc.OperationalError as e:
                if "interrupted" in str(e).lower():
                    raise asyncio.TimeoutError()
                else:
                    raise e
            finally:
                if timeout is not None:
                    interrupter.cancel()

        if return_df:
            return pd.DataFrame(rows, columns=result.keys())
        return rows

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = None,
        return_df: bool = False,
    ) -> QueryResult:
        # Note: str queries are passed through to _run_query_s / _run_query_a
        # which handle the text() conversion or exec_driver_sql routing internally.
        async with self.throttle():
            t0 = time.time()
            try:
                if self.engine_type == "async":
                    if self.engine.dialect.name == "sqlite":
                        return QueryResult(
                            result=await self._run_query_aiosqlite(query, parameters, return_df, timeout),
                            latency_seconds=time.time() - t0,
                        )
                    else:
                        return QueryResult(
                            result=await asyncio.wait_for(
                                self._run_query_a(query, parameters, return_df),
                                timeout=timeout,
                            ),
                            latency_seconds=time.time() - t0,
                        )
                else:
                    loop = asyncio.get_running_loop()
                    return QueryResult(
                        result=await asyncio.wait_for(
                            loop.run_in_executor(None, self._run_query_s, query, parameters, return_df),
                            timeout=timeout,
                        ),
                        latency_seconds=time.time() - t0,
                    )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Query {query} timed out after {timeout} seconds")


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
) -> SQLSchema:
    """
    Loads the database schema, utilizing a cache if available and enabled.
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

        if mintq_config.schema_cache_enabled and not mintq_config.schema_cache_overwrite and os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return SQLSchema.model_validate_json(f.read())

        if mintq_config.schema_cache_required:
            raise FileNotFoundError(f"Schema cache required but not found at {cache_path}")

        schema = await build_schema_async(
            t_eng,
            db_name,
            dialect,  # type: ignore
            group_date_partitioned_tables,
            group_table_regexes,
            column_stats_mode=mintq_config.column_stats_mode,
            include_schema_names=include_schema_names,
        )
        if t_eng.engine_type == "async":
            await t_eng.engine.dispose()  # type: ignore
        else:
            t_eng.engine.dispose()
        if mintq_config.schema_cache_enabled:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(schema.model_dump_json(indent=2))
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
    num_rows: int,
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

    if num_rows == 0 or (column_stats_mode == "skip_for_large_tables" and num_rows > _LARGE_TABLE_THRESHOLD):
        null_ratio = num_unique = unique_ratio = None
    else:
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
    if num_rows == 0:
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
    if num_rows > 0:
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
    col_dicts = await async_inspector.get_columns(table_name, schema=schema_name)

    if t_eng.engine.dialect.name == "bigquery":
        col_dicts = [c for c in col_dicts if "." not in c["name"]]

    if not col_dicts:
        logger.warning(f"Skipping table {schema_name}.{table_name}: no columns found")
        return None

    tbl = sqlalchemy.table(table_name, schema=schema_name)
    num_rows = (await t_eng.run_query_async(select(func.count()).select_from(tbl))).result[0][0]

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
        task_results = await asyncio.gather(*tasks)

    tables = []
    for group, table in zip(all_groups, task_results):
        if table is None:
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

    global_id: str
    schema: SQLSchema
    language: SQLDialect
    _t_eng: ThrottledEngine
    read_only: bool = True

    @classmethod
    async def from_url_async(
        cls,
        global_id: str,
        db_name: str,
        engine_type: Literal["async", "sync"],
        url: str | SQLAlchemyURL,
        max_concurrency_per_db: int = 8,
        dbms_semaphore: asyncio.Semaphore | None = None,
        schema: SQLSchema | None = None,
        group_date_partitioned_tables: bool = True,
        group_table_regexes: list[str] = [],
        read_only: bool = True,
        include_schema_names: list[str] | None = None,
        **engine_kwargs: Any,
    ) -> "SQLConnector":
        """Asynchronously create a SQLConnector from a database URL.

        Creates a SQLAlchemy engine (async or sync) wrapped in a
        :class:`ThrottledEngine` with concurrency control, and optionally loads
        the database schema if one is not provided.

        Args:
            global_id: A globally unique identifier for this database connection, also
                used as the cache key when loading the schema.
            db_name: The name of the database to connect to.
            engine_type: Whether to create an ``"async"`` or ``"sync"``
                SQLAlchemy engine.
            url: The database URL (string or :class:`SQLAlchemyURL`).
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
            **engine_kwargs: Additional keyword arguments forwarded to the
                SQLAlchemy engine constructor (e.g. ``pool_pre_ping``).

        Returns:
            A fully initialised :class:`SQLConnector` instance ready to
            execute queries.
        """
        engine_kwargs.setdefault("echo", False)  # avoid excessive logging from engine
        if engine_type == "async":
            engine = create_async_engine(url, pool_size=max_concurrency_per_db, **engine_kwargs)
        else:
            engine = create_engine(url, pool_size=max_concurrency_per_db, **engine_kwargs)  # type: ignore
        db_semaphore = asyncio.Semaphore(max_concurrency_per_db)
        t_eng = ThrottledEngine(engine_type, engine, dbms_semaphore, db_semaphore)
        if schema is None:
            schema = await load_schema_with_cache_async(
                global_id,
                db_name,
                t_eng,
                group_date_partitioned_tables,
                group_table_regexes,
                include_schema_names=include_schema_names,
            )
        language: SQLDialect = schema.dialect  # type: ignore[assignment]
        return cls(global_id, schema, language, t_eng, read_only=read_only)

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
        # --- read-only guard ---
        query_str = str(query) if not isinstance(query, str) else query
        if self.read_only and _WRITE_STATEMENT_RE.match(query_str):
            keyword = _WRITE_STATEMENT_RE.match(query_str)
            assert keyword is not None
            return ExecResult(
                error=ErrorInfo(
                    exc_type="ReadOnlyViolationError",
                    message=f"Write statement blocked (read_only=True): {keyword.group('keyword').upper()} ...",
                ),
            )

        # --- query result cache lookup ---
        params_map: Mapping[str, Any] = parameters if isinstance(parameters, Mapping) else {}
        use_cache = mintq_config.query_cache_enabled and not mintq_config.query_cache_overwrite

        cache_hash: str | None = None
        if mintq_config.query_cache_enabled:
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
        if mintq_config.query_cache_enabled and cache_hash is not None:
            skip = mintq_config.query_cache_mode == "successful_only" and exec_result.df is None
            if not skip:
                async with _query_cache_locks[cache_hash]:
                    os.makedirs(cache_dir, exist_ok=True)
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(exec_result.model_dump_json(indent=2))
                    _query_cache[cache_hash] = exec_result
                    logger.debug(f"Query cache write: {query_str[:80]}")

        return exec_result
