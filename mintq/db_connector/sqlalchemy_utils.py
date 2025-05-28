import aiofiles
import aiofiles.os
import os
import hashlib
from typing import Any
import sqlalchemy
from sqlalchemy import select, func, inspect
from sqlalchemy.ext.asyncio import AsyncEngine
from mintq.schema import SQLSchema, SQLColumnSchema, SQLTableSchema, ForeignKeySchema
from mintq.config import config


async def load_schema_with_cache_async(name: str, engine: AsyncEngine | sqlalchemy.engine.Engine) -> SQLSchema:
    """
    Loads the database schema, utilizing a cache if available and enabled.
    """
    schema_cache_dir = os.path.join(config.cache_dir, "schemas")

    await aiofiles.os.makedirs(schema_cache_dir, exist_ok=True)

    engine_url_str = str(engine.url)
    hashed = hashlib.sha256(engine_url_str.encode()).hexdigest()
    cache_path = os.path.join(schema_cache_dir, f"{name}.{hashed}.json")

    if config.cache_refresh and await aiofiles.os.path.exists(cache_path):
        await aiofiles.os.remove(cache_path)

    if config.cache_enabled and await aiofiles.os.path.exists(cache_path):
        async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
            content = await f.read()
            return SQLSchema.model_validate_json(content)

    dbms_supports_schema = engine.dialect.name not in ("sqlite", "mysql")
    if isinstance(engine, sqlalchemy.engine.Engine):
        with engine.connect() as conn:
            schema = build_schema(conn, name, dbms_supports_schema)
    else:
        async with engine.connect() as conn:
            schema = await conn.run_sync(build_schema, name, dbms_supports_schema)

    if config.cache_enabled:
        async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
            await f.write(schema.model_dump_json(indent=2))
    return schema


def _convert(value: Any) -> str | int | float | bool:
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def build_schema(conn: sqlalchemy.engine.Connection, name: str, dbms_supports_schema: bool) -> SQLSchema:
    tables = []
    foreign_keys = []

    inspector = inspect(conn)  # sqlalchemy does not support async inspect yet as of May 2025

    # if sqlite, there is no schema
    if not dbms_supports_schema:
        schema_names = [None]
    else:
        schema_names = inspector.get_schema_names()  # type: ignore

    for schema_name in schema_names:
        if schema_name and schema_name.lower() == "information_schema":
            continue

        for table_name in inspector.get_table_names(schema=schema_name):
            # print(f"table_name: {table_name}, schema_name: {schema_name}")
            columns = []
            for column in inspector.get_columns(table_name, schema=schema_name):
                col = sqlalchemy.column(column["name"])  # type: ignore
                tbl = sqlalchemy.table(table_name, schema=schema_name)

                # Note: examples will contain all possible values if cardinality <= 20
                examples = [
                    row[0]
                    for row in conn.execute(
                        select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(21)
                    ).fetchall()
                ]
                examples = [_convert(v) for v in examples]
                columns.append(
                    SQLColumnSchema(
                        name=column["name"],
                        dtype=column["type"].__visit_name__,
                        examples=examples,
                    )
                )

            primary_key = inspector.get_pk_constraint(table_name, schema=schema_name)["constrained_columns"]
            num_rows = conn.execute(select(func.count()).select_from(tbl)).scalar_one()
            for fk in inspector.get_foreign_keys(table_name, schema=schema_name):
                foreign_keys.append(
                    ForeignKeySchema(
                        schema_name=schema_name,
                        table=table_name,
                        columns=fk["constrained_columns"],
                        foreign_schema_name=fk["referred_schema"],
                        foreign_table=fk["referred_table"],
                        foreign_columns=fk["referred_columns"],
                    )
                )

            tables.append(
                SQLTableSchema(
                    name=table_name,
                    schema_name=schema_name,
                    columns=columns,
                    primary_key=primary_key,
                    num_rows=num_rows,
                )
            )

    return SQLSchema(name=name, tables=tables, foreign_keys=foreign_keys)
