from typing import Any, Sequence, Mapping, Literal
from dataclasses import dataclass
import pandas as pd
import hashlib
import os
import asyncio
from contextlib import asynccontextmanager
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine, select, func, distinct, inspect
from mintq.schema import SQLSchema, SQLColumnSchema, SQLTableSchema, ForeignKeySchema
from mintq.config import config


@dataclass
class ThrottledEngine:
    engine_type: Literal["async", "sync"]
    engine: AsyncEngine | sqlalchemy.engine.Engine
    dbms_semaphore: asyncio.Semaphore | None
    db_semaphore: asyncio.Semaphore | None

    @asynccontextmanager
    async def throttle(self):
        semaphores = [sem for sem in [self.dbms_semaphore, self.db_semaphore] if sem is not None]
        for sem in semaphores:
            await sem.acquire()
        try:
            yield
        finally:
            for sem in reversed(semaphores):
                sem.release()

    def _run_query(
        self,
        statement: sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | dict[str, Any] = (),
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        with self.engine.connect() as conn:
            result = conn.execute(statement, parameters)
            rows = result.fetchall()
            if return_df:
                return pd.DataFrame(rows, columns=result.keys())
            return rows

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | dict[str, Any] = (),
        timeout: int | None = None,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        if isinstance(query, str):
            query = sqlalchemy.text(query)

        async with self.throttle():
            try:
                if self.engine_type == "async":
                    async with self.engine.connect() as conn:
                        result = await asyncio.wait_for(conn.execute(query, parameters), timeout=timeout)
                        rows = result.fetchall()
                        if return_df:
                            return pd.DataFrame(rows, columns=result.keys())
                        return rows
                else:
                    loop = asyncio.get_running_loop()
                    return await asyncio.wait_for(
                        loop.run_in_executor(None, self._run_query, query, parameters, return_df),
                        timeout=timeout,
                    )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Query {query} timed out after {timeout} seconds")


@dataclass
class AsyncInspector:
    t_eng: ThrottledEngine

    def _run_inspector_conn(self, conn, method: str, args, kwargs) -> Any:
        inspector = inspect(conn)
        return getattr(inspector, method)(*args, **kwargs)

    def _run_inspector(self, method: str, args, kwargs) -> Any:
        with self.t_eng.engine.connect() as conn:
            return self._run_inspector_conn(conn, method, args, kwargs)

    def __getattr__(self, method: str) -> Any:
        async def _stub_async(*args, **kwargs) -> Any:
            async with self.t_eng.throttle():
                if self.t_eng.engine_type == "async":
                    async with self.t_eng.engine.connect() as conn:
                        return await conn.run_sync(self._run_inspector_conn, method, args, kwargs)
                else:
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(None, self._run_inspector, method, args, kwargs)

        return _stub_async


async def load_schema_with_cache_async(name: str, t_eng: ThrottledEngine) -> SQLSchema:
    """
    Loads the database schema, utilizing a cache if available and enabled.
    """
    schema_cache_dir = os.path.join(config.cache_dir, "schemas")

    os.makedirs(schema_cache_dir, exist_ok=True)

    engine_url_str = str(t_eng.engine.url)
    hashed = hashlib.sha256(engine_url_str.encode()).hexdigest()
    cache_path = os.path.join(schema_cache_dir, f"{name}.{hashed}.json")

    if config.cache_refresh and os.path.exists(cache_path):
        os.remove(cache_path)

    if config.cache_enabled and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            content = f.read()
            return SQLSchema.model_validate_json(content)

    dbms_supports_schema = t_eng.engine.dialect.name not in ("sqlite", "mysql")

    schema = await build_schema_async(t_eng, name, dbms_supports_schema)

    if config.cache_enabled:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(schema.model_dump_json(indent=2))
    return schema


def _convert(value: Any) -> str | int | float | bool:
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def get_num_unique_stmt(
    dialect: str, col: sqlalchemy.Column, tbl: sqlalchemy.Table, mode: Literal["exact", "approx"] = "approx"
) -> sqlalchemy.sql.expression.Executable:
    stmts = {
        "exact": select(func.count(distinct(col))).select_from(tbl),
        "snowflake": select(func.hll(col)).select_from(tbl),
    }
    if mode == "exact" or dialect not in stmts:
        return stmts["exact"]
    else:
        return stmts[dialect]


async def build_column_async(
    t_eng: ThrottledEngine, column: dict[str, Any], table_name: str, schema_name: str, num_rows: int
) -> SQLColumnSchema:
    col = sqlalchemy.column(column["name"])  # type: ignore
    tbl = sqlalchemy.table(table_name, schema=schema_name)

    if num_rows > 0:
        tasks = []
        dialect = t_eng.engine.dialect.name
        tasks.append(
            asyncio.create_task(t_eng.run_query_async(select(func.count()).select_from(tbl).where(col.is_(None))))
        )
        tasks.append(asyncio.create_task(t_eng.run_query_async(get_num_unique_stmt(dialect, col, tbl))))
        tasks.append(
            asyncio.create_task(
                t_eng.run_query_async(select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(21))
            )
        )

        num_null, num_unique, examples = await asyncio.gather(*tasks)

        num_null = num_null[0][0]
        num_unique = num_unique[0][0]
        null_ratio = num_null / num_rows
        unique_ratio = num_unique / num_rows
        # Note: examples will contain all possible values if cardinality <= 20
        examples = [_convert(row[0]) for row in examples]
    else:
        null_ratio = num_unique = unique_ratio = 0.0
        examples = []

    return SQLColumnSchema(
        name=column["name"],
        dtype=column["type"].__visit_name__,
        nullable=column["nullable"],
        null_ratio=null_ratio,
        num_unique=num_unique,
        unique_ratio=unique_ratio,
        examples=examples,
    )


async def build_table_async(
    t_eng: ThrottledEngine, table_name: str, schema_name: str, is_view: bool = False
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


async def build_schema_async(t_eng: ThrottledEngine, name: str, dbms_supports_schema: bool) -> SQLSchema:
    async_inspector = AsyncInspector(t_eng)

    if not dbms_supports_schema:
        schema_names = [None]
    else:
        schema_names = await async_inspector.get_schema_names()  # type: ignore

    tasks = []
    for schema_name in schema_names:
        if schema_name and schema_name.lower() == "information_schema":
            continue

        for table_name in await async_inspector.get_table_names(schema=schema_name):
            tasks.append(asyncio.create_task(build_table_async(t_eng, table_name, schema_name)))

        for table_name in await async_inspector.get_view_names(
            schema=schema_name
        ):  # does not include materialized views
            tasks.append(asyncio.create_task(build_table_async(t_eng, table_name, schema_name, is_view=True)))

    tables = await asyncio.gather(*tasks)

    return SQLSchema(name=name, tables=tables)


@dataclass
class SQLConnector:
    name: str
    schema: SQLSchema
    _t_eng: ThrottledEngine

    @classmethod
    async def from_url_async(
        cls,
        name: str,
        engine_type: Literal["async", "sync"],
        url: str | SQLAlchemyURL,
        max_concurrency_per_db: int = 8,
        dbms_semaphore: asyncio.Semaphore | None = None,
        **engine_kwargs: Any,
    ) -> "SQLConnector":
        engine_kwargs.setdefault("echo", False)  # avoid excessive logging from engine
        if engine_type == "async":
            engine = create_async_engine(url, pool_size=max_concurrency_per_db, **engine_kwargs)
        else:
            engine = create_engine(url, pool_size=max_concurrency_per_db, **engine_kwargs)
        db_semaphore = asyncio.Semaphore(max_concurrency_per_db)
        t_eng = ThrottledEngine(engine_type, engine, dbms_semaphore, db_semaphore)
        schema = await load_schema_with_cache_async(name, t_eng)
        return cls(name, schema, t_eng)

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        return await self._t_eng.run_query_async(query, parameters, timeout, return_df)
