import os
import hashlib
from typing import Any
import asyncio
import sqlalchemy
from sqlalchemy import select, func, inspect
from sqlalchemy.ext.asyncio import AsyncEngine
from mintq.schema import SQLSchema, SQLColumnSchema, SQLTableSchema, ForeignKeySchema
from mintq.config import config


MAXIMUM_CONCURRENT_CONNECTIONS = 10
sem = asyncio.Semaphore(MAXIMUM_CONCURRENT_CONNECTIONS)


async def load_schema_with_cache_async(name: str, engine: AsyncEngine | sqlalchemy.engine.Engine) -> SQLSchema:
    """
    Loads the database schema, utilizing a cache if available and enabled.
    """
    schema_cache_dir = os.path.join(config.cache_dir, "schemas")

    os.makedirs(schema_cache_dir, exist_ok=True)

    engine_url_str = str(engine.url)
    hashed = hashlib.sha256(engine_url_str.encode()).hexdigest()
    cache_path = os.path.join(schema_cache_dir, f"{name}.{hashed}.json")

    if config.cache_refresh and os.path.exists(cache_path):
        os.remove(cache_path)

    if config.cache_enabled and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            content = f.read()
            return SQLSchema.model_validate_json(content)

    dbms_supports_schema = engine.dialect.name not in ("sqlite", "mysql")
    schema = await build_schema_async(engine, name, dbms_supports_schema)

    if config.cache_enabled:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(schema.model_dump_json(indent=2))
    return schema


def _convert(value: Any) -> str | int | float | bool:
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def run_query(conn, stmt) -> list[Any]:
    return conn.execute(stmt).fetchall()


async def run_query_async(engine, stmt) -> list[Any]:
    async with sem:
        if isinstance(engine, sqlalchemy.engine.Engine):
            with engine.connect() as conn:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, run_query, conn, stmt)
        else:
            async with engine.connect() as conn:
                return await conn.run_sync(run_query, stmt)


async def build_column_async(
    engine, column: dict[str, Any], table_name: str, schema_name: str, num_rows: int
) -> SQLColumnSchema:
    col = sqlalchemy.column(column["name"])  # type: ignore
    tbl = sqlalchemy.table(table_name, schema=schema_name)

    if num_rows > 0:
        num_null = (await run_query_async(engine, select(func.count()).select_from(tbl).where(col.is_(None))))[0][0]
        null_ratio = num_null / num_rows
        num_unique = (await run_query_async(engine, select(func.count(col.distinct())).select_from(tbl)))[0][0]
        unique_ratio = num_unique / num_rows
    else:
        null_ratio = unique_ratio = 0.0
        num_unique = 0

    # Note: examples will contain all possible values if cardinality <= 20
    examples = [
        row[0]
        for row in await run_query_async(
            engine, select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(21)
        )
    ]
    examples = [_convert(v) for v in examples]
    return SQLColumnSchema(
        name=column["name"],
        dtype=column["type"].__visit_name__,
        nullable=column["nullable"],
        null_ratio=null_ratio,
        num_unique=num_unique,
        unique_ratio=unique_ratio,
        examples=examples,
    )


class AsyncInspector:
    def __init__(self, engine: AsyncEngine | sqlalchemy.engine.Engine):
        self.engine = engine

    def _run_inspector(self, conn, method: str, args, kwargs) -> Any:
        inspector = inspect(conn)
        return getattr(inspector, method)(*args, **kwargs)

    def __getattr__(self, method: str) -> Any:
        async def _stub_async(*args, **kwargs) -> Any:
            async with sem:
                if isinstance(self.engine, sqlalchemy.engine.Engine):
                    with self.engine.connect() as conn:
                        loop = asyncio.get_running_loop()
                        return await loop.run_in_executor(None, self._run_inspector, conn, method, args, kwargs)
                else:
                    async with self.engine.connect() as conn:
                        return await conn.run_sync(self._run_inspector, method, args, kwargs)

        return _stub_async


async def build_table_async(engine, table_name: str, schema_name: str) -> SQLTableSchema:
    tbl = sqlalchemy.table(table_name, schema=schema_name)
    num_rows = (await run_query_async(engine, select(func.count()).select_from(tbl)))[0][0]

    async_inspector = AsyncInspector(engine)

    col_dicts = await async_inspector.get_columns(table_name, schema=schema_name)

    columns = await asyncio.gather(
        *[build_column_async(engine, col, table_name, schema_name, num_rows) for col in col_dicts]
    )

    primary_key = (await async_inspector.get_pk_constraint(table_name, schema=schema_name))["constrained_columns"]

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
    return SQLTableSchema(
        name=table_name,
        schema_name=schema_name,
        columns=columns,
        primary_key=primary_key,
        num_rows=num_rows,
        foreign_keys=foreign_keys,
    )


async def build_schema_async(engine, name: str, dbms_supports_schema: bool) -> SQLSchema:
    async_inspector = AsyncInspector(engine)

    if not dbms_supports_schema:
        schema_names = [None]
    else:
        schema_names = await async_inspector.get_schema_names()  # type: ignore

    tasks = []
    for schema_name in schema_names:
        if schema_name and schema_name.lower() == "information_schema":
            continue

        for table_name in await async_inspector.get_table_names(schema=schema_name):
            tasks.append(asyncio.create_task(build_table_async(engine, table_name, schema_name)))

    tables = await asyncio.gather(*tasks)

    return SQLSchema(name=name, tables=tables)
