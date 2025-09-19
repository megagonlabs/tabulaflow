from typing import Any, Sequence, Mapping, Literal, AsyncGenerator
from dataclasses import dataclass
import collections
import pandas as pd
import os
import asyncio
from contextlib import asynccontextmanager
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine, select, func, distinct, inspect
from mintq.schema import SQLSchema, SQLColumnSchema, SQLTableSchema, ForeignKeySchema
from mintq.config import config


_db_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)


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

    async def _run_query_a_async(
        self,
        statement: sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        rows = []
        async with self.engine.connect() as conn:  # type: ignore
            result = await conn.execute(statement, parameters)
            async for row in result:
                rows.append(row)
            
        if return_df:
            return pd.DataFrame(rows, columns=result.keys())
        return rows

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = None,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        if isinstance(query, str):
            query = sqlalchemy.text(query)

        async with self.throttle():
            try:
                if self.engine_type == "async":
                    return await asyncio.wait_for(self._run_query_a_async(query, parameters, return_df), timeout=timeout)
                else:
                    loop = asyncio.get_running_loop()
                    return await asyncio.wait_for(
                        loop.run_in_executor(None, self._run_query_s, query, parameters, return_df),
                        timeout=timeout,
                    )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Query {query} timed out after {timeout} seconds")


@dataclass
class AsyncInspector:
    t_eng: ThrottledEngine

    def _run_inspector_conn(
        self, conn: sqlalchemy.engine.Connection, method: str, args: tuple[Any, ...], kwargs: dict[str, Any]
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


async def load_schema_with_cache_async(global_id: str, db_name: str, t_eng: ThrottledEngine) -> SQLSchema:
    """
    Loads the database schema, utilizing a cache if available and enabled.
    """
    schema_cache_dir = os.path.join(config.cache_dir, "schemas")
    os.makedirs(schema_cache_dir, exist_ok=True)
    cache_path = os.path.join(schema_cache_dir, f"{global_id}.json")

    lock = _db_locks[global_id]
    async with lock:
        if config.cache_enabled and os.path.exists(cache_path):
            if config.cache_refresh:
                os.remove(cache_path)
            else:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return SQLSchema.model_validate_json(f.read())

        dbms_supports_schema = t_eng.engine.dialect.name not in ("sqlite", "mysql")

        schema = await build_schema_async(t_eng, db_name, dbms_supports_schema)
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
    t_eng: ThrottledEngine, column: dict[str, Any], table_name: str, schema_name: str | None, num_rows: int
) -> SQLColumnSchema:
    col = sqlalchemy.column(column["name"])  # type: ignore
    tbl = sqlalchemy.table(table_name, schema=schema_name)
    dtype = column["type"].__visit_name__.upper()

    if num_rows > 0:
        dialect = t_eng.engine.dialect.name
        num_null = (await t_eng.run_query_async(select(func.count()).select_from(tbl).where(col.is_(None))))[0][0]
        null_ratio = num_null / num_rows

        if dtype in CATEGORICAL_TYPES:
            num_unique = (await t_eng.run_query_async(get_num_unique_stmt(dialect, col, tbl, mode="approx")))[0][0]
            unique_ratio = num_unique / num_rows
            examples = await t_eng.run_query_async(
                select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(min(20, num_unique))
            )
        else:
            num_unique = None
            unique_ratio = None
            examples = await t_eng.run_query_async(select(col).select_from(tbl).where(col.isnot(None)).limit(20))
        # Note: examples will contain all possible values if cardinality <= 20
        examples = [_convert(row[0]) for row in examples]
    else:
        null_ratio = unique_ratio = 0.0
        num_unique = 0
        examples = []

    return SQLColumnSchema(
        name=column["name"],
        dtype=dtype,
        nullable=column["nullable"],
        null_ratio=null_ratio,
        num_unique=num_unique,
        unique_ratio=unique_ratio,
        examples=examples,
    )


async def build_table_async(
    t_eng: ThrottledEngine, table_name: str, schema_name: str | None, is_view: bool = False
) -> SQLTableSchema:
    tbl = sqlalchemy.table(table_name, schema=schema_name)
    num_rows = (await t_eng.run_query_async(select(func.count()).select_from(tbl)))[0][0]

    async_inspector = AsyncInspector(t_eng)

    col_dicts = await async_inspector.get_columns(table_name, schema=schema_name)

    columns = await asyncio.gather(
        *[build_column_async(t_eng, col, table_name, schema_name, num_rows) for col in col_dicts]
    )
    name2col = {col.name: col for col in columns}

    primary_key = (await async_inspector.get_pk_constraint(table_name, schema=schema_name))["constrained_columns"]
    for col in primary_key:
        name2col[col].primary_key_type = "single" if len(primary_key) == 1 else "composite"

    foreign_keys = []
    for fk in await async_inspector.get_foreign_keys(table_name, schema=schema_name):
        foreign_keys.append(
            ForeignKeySchema(
                columns=fk["constrained_columns"],
                foreign_schema_name=fk["referred_schema"],
                foreign_table=fk["referred_table"],
                foreign_columns=fk["referred_columns"],
            )
        )
    for fk in foreign_keys:
        for col in fk.columns:
            name2col[col].foreign_keys.append(fk)

    return SQLTableSchema(
        name=table_name,
        schema_name=schema_name,
        is_view=is_view,
        columns=columns,
        primary_key=primary_key,
        num_rows=num_rows,
        foreign_keys=foreign_keys,
    )


async def build_schema_async(t_eng: ThrottledEngine, db_name: str, dbms_supports_schema: bool) -> SQLSchema:
    async_inspector = AsyncInspector(t_eng)

    if not dbms_supports_schema:
        schema_names = [None]
    else:
        schema_names = await async_inspector.get_schema_names()

    tasks = []
    for schema_name in schema_names:
        if schema_name and schema_name.lower() == "information_schema":
            continue

        for table_name in await async_inspector.get_table_names(schema=schema_name):
            tasks.append(asyncio.create_task(build_table_async(t_eng, table_name, schema_name, is_view=False)))

        for table_name in await async_inspector.get_view_names(
            schema=schema_name
        ):  # does not include materialized views
            tasks.append(asyncio.create_task(build_table_async(t_eng, table_name, schema_name, is_view=True)))

    tables = await asyncio.gather(*tasks)

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
            schema = await load_schema_with_cache_async(global_id, db_name, t_eng)
        return cls(global_id, schema, t_eng)

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int | None = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        return await self._t_eng.run_query_async(query, parameters, timeout, return_df)
