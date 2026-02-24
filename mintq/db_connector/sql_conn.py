import copy
import re
from typing import Any, Sequence, Mapping, Literal, AsyncGenerator
from dataclasses import dataclass
import collections
import pandas as pd
import os
import time
import asyncio
from contextlib import asynccontextmanager
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine, select, func, distinct, inspect
from mintq.schema import (
    ErrorInfo,
    SQLSchema,
    SQLColumnSchema,
    SQLTableSchema,
    ForeignKeySchema,
    ExecResult,
)
from mintq.config import config


_db_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)


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
        statement: sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        with self.engine.connect() as conn:  # type: ignore
            result = conn.execute(statement, parameters)
            rows = result.fetchall()
            if return_df:
                return pd.DataFrame(rows, columns=result.keys())
            return rows

    async def _run_query_a(
        self,
        statement: sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        rows = []
        async with self.engine.connect() as conn:  # type: ignore
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
        statement: sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
        timeout: int | None = None,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        """The generic wait_for solution does not work for sqlite. We need to use sqlite's native conn.interrupt() mechanism."""
        rows = []
        async with self.engine.connect() as conn:  # type: ignore
            if timeout is not None:
                interrupter = self._create_interrupter(conn, timeout)

            try:
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
        if isinstance(query, str):
            query = sqlalchemy.text(query)

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
    skip_date_partitioned_tables: bool = True,
    skip_table_regexes: list[str] = [],
) -> SQLSchema:
    """
    Loads the database schema, utilizing a cache if available and enabled.
    """
    schema_cache_dir = os.path.join(config.cache_dir, "schemas")
    os.makedirs(schema_cache_dir, exist_ok=True)
    cache_path = os.path.join(schema_cache_dir, f"{global_id}.json")

    lock = _db_locks[global_id]
    async with lock:
        if config.cache_enabled and os.path.exists(cache_path):
            if config.cache_overwrite:
                os.remove(cache_path)
            else:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return SQLSchema.model_validate_json(f.read())

        if config.cache_required:
            raise FileNotFoundError(f"Cache required (MINTQ_CACHE_REQUIRED=1) but not found at {cache_path}")

        dbms_supports_schema = t_eng.engine.dialect.name not in ("sqlite", "mysql")

        schema = await build_schema_async(
            t_eng,
            db_name,
            dbms_supports_schema,
            skip_date_partitioned_tables,
            skip_table_regexes,
        )
        if t_eng.engine_type == "async":
            await t_eng.engine.dispose()  # type: ignore
        else:
            t_eng.engine.dispose()
        if config.cache_enabled:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(schema.model_dump_json(indent=2))
        return schema


def _convert(value: Any) -> str | int | float | bool:
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def get_num_unique_stmt(
    dialect: str,
    col: sqlalchemy.ColumnElement[Any],
    tbl: sqlalchemy.FromClause,
    mode: Literal["exact", "approx"] = "approx",
) -> sqlalchemy.sql.expression.Executable:
    stmts = {
        "exact": select(func.count(distinct(col))).select_from(tbl),
        "snowflake": select(func.hll(col)).select_from(tbl),
    }
    if mode == "exact" or dialect not in stmts:
        return stmts["exact"]
    else:
        return stmts[dialect]


# Types that might be categorical
CATEGORICAL_TYPES = [
    "CHAR",
    "VARCHAR",
    "NCHAR",
    "NVARCHAR",
    "TEXT",
    "CLOB",
    "BOOLEAN",
    "SMALLINT",
    "INTEGER",
    "BIGINT",
    "ENUM",
]


async def build_column_async(
    t_eng: ThrottledEngine,
    column: dict[str, Any],
    table_name: str,
    schema_name: str | None,
    num_rows: int,
) -> SQLColumnSchema:
    col = sqlalchemy.column(column["name"])  # type: ignore
    tbl = sqlalchemy.table(table_name, schema=schema_name)
    dtype = column["type"].__visit_name__.upper()

    if num_rows > 0:
        dialect = t_eng.engine.dialect.name
        num_null = (await t_eng.run_query_async(select(func.count()).select_from(tbl).where(col.is_(None)))).result[0][
            0
        ]
        null_ratio = num_null / num_rows

        if dtype in CATEGORICAL_TYPES:
            num_unique = (await t_eng.run_query_async(get_num_unique_stmt(dialect, col, tbl, mode="approx"))).result[0][
                0
            ]
            unique_ratio = num_unique / num_rows
            examples = (
                await t_eng.run_query_async(
                    select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(min(20, num_unique))
                )
            ).result
        else:
            num_unique = None
            unique_ratio = None
            examples = (
                await t_eng.run_query_async(select(col).select_from(tbl).where(col.isnot(None)).limit(20))
            ).result
        # Note: examples will contain all possible values if cardinality <= 20
        examples = [_convert(row[0]) for row in examples]
    else:
        null_ratio = unique_ratio = 0.0
        num_unique = 0
        examples = []

    actual_col_name = str(t_eng.engine.dialect.denormalize_name(column["name"]))

    return SQLColumnSchema(
        name=actual_col_name,
        dtype=dtype,
        nullable=column["nullable"],
        null_ratio=null_ratio,
        num_unique=num_unique,
        unique_ratio=unique_ratio,
        examples=examples,
    )


async def build_table_async(
    t_eng: ThrottledEngine,
    table_name: str,
    schema_name: str | None,
    is_view: bool = False,
) -> SQLTableSchema:
    tbl = sqlalchemy.table(table_name, schema=schema_name)
    num_rows = (await t_eng.run_query_async(select(func.count()).select_from(tbl))).result[0][0]

    async_inspector = AsyncInspector(t_eng)
    dialect = t_eng.engine.dialect

    def _denorm(name: str | None) -> str | None:
        """Denormalize a normalized identifier back to its actual stored form as a plain str."""
        if name is None:
            return None
        return str(dialect.denormalize_name(name))

    col_dicts = await async_inspector.get_columns(table_name, schema=schema_name)

    columns = await asyncio.gather(
        *[build_column_async(t_eng, col, table_name, schema_name, num_rows) for col in col_dicts]
    )
    name2col = {col.name: col for col in columns}

    primary_key = (await async_inspector.get_pk_constraint(table_name, schema=schema_name))["constrained_columns"]
    for col in primary_key:
        name2col[_denorm(col)].primary_key_type = "single" if len(primary_key) == 1 else "composite"

    foreign_keys = []
    for fk in await async_inspector.get_foreign_keys(table_name, schema=schema_name):
        foreign_keys.append(
            ForeignKeySchema(
                columns=[_denorm(c) for c in fk["constrained_columns"]],
                foreign_schema_name=_denorm(fk["referred_schema"]),
                foreign_table=_denorm(fk["referred_table"]),
                foreign_columns=[_denorm(c) for c in fk["referred_columns"]],
            )
        )
    for fk in foreign_keys:
        for col in fk.columns:
            name2col[col].foreign_keys.append(fk)

    # Sample rows from the table
    sampled_df = (await t_eng.run_query_async(select("*").select_from(tbl).limit(10), return_df=True)).result

    return SQLTableSchema(
        name=_denorm(table_name),
        schema_name=_denorm(schema_name),
        is_view=is_view,
        columns=columns,
        primary_key=[_denorm(c) for c in primary_key],
        num_rows=num_rows,
        foreign_keys=foreign_keys,
        sampled_df=sampled_df,
    )


def group_table_names(
    table_names: list[str],
    skip_date_partitioned_tables: bool = True,
    skip_table_regexes: list[str] = [],
) -> list[list[str]]:
    groups = []
    remaining = table_names

    for regex in skip_table_regexes:
        matched = [table_name for table_name in remaining if re.match(regex, table_name)]
        if len(matched) > 1:
            groups.append(matched)
            remaining = [table_name for table_name in remaining if table_name not in matched]

    if skip_date_partitioned_tables:
        date_patterns = [
            re.compile(r"^(?P<prefix>.*?)(?P<date>\d{8})(?P<suffix>.*?)$"),
            re.compile(r"^(?P<prefix>.*?)(?P<date>\d{6})(?P<suffix>.*?)$"),
            re.compile(r"^(?P<prefix>.*?)(?P<date>\d{4})(?P<suffix>.*?)$"),
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
    dbms_supports_schema: bool,
    skip_date_partitioned_tables: bool = True,
    skip_table_regexes: list[str] = [],
) -> SQLSchema:
    async_inspector = AsyncInspector(t_eng)

    if not dbms_supports_schema:
        schema_names = [None]
    else:
        schema_names = await async_inspector.get_schema_names()

    tasks = []
    all_groups = []

    for schema_name in schema_names:
        if schema_name and schema_name.lower() == "information_schema":
            continue

        table_names = await async_inspector.get_table_names(schema=schema_name)
        view_names = await async_inspector.get_view_names(schema=schema_name)  # does not include materialized views

        groups = group_table_names(table_names + view_names, skip_date_partitioned_tables, skip_table_regexes)
        for group in groups:
            print(group[0], len(group))
            tasks.append(
                asyncio.create_task(build_table_async(t_eng, group[0], schema_name, is_view=group[0] in view_names))
            )
            all_groups.append(group)

    task_results = await asyncio.gather(*tasks)
    tables = []
    for group, table in zip(all_groups, task_results):
        tables.append(table)
        for t in group:
            table = copy.deepcopy(table)
            table.name = t
            # table.num_rows = None
            # table.sampled_df = None
            tables.append(table)

    return SQLSchema(name=db_name, tables=tables)


@dataclass
class SQLConnector:
    global_id: str
    schema: SQLSchema
    _t_eng: ThrottledEngine

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
        skip_date_partitioned_tables: bool = True,
        skip_table_regexes: list[str] = [],
        **engine_kwargs: Any,
    ) -> "SQLConnector":
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
                skip_date_partitioned_tables,
                skip_table_regexes,
            )
        return cls(global_id, schema, t_eng)

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = None,
    ) -> ExecResult:
        df, error, latency_seconds = None, None, None
        try:
            result = await self._t_eng.run_query_async(query, parameters, timeout, return_df=True)
            df = result.result
            latency_seconds = result.latency_seconds
        except Exception as e:
            error = ErrorInfo(exc_type=type(e).__name__, message=str(e))
        return ExecResult(df=df, error=error, latency_seconds=latency_seconds)
