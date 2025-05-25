import os
from typing import Any, Sequence
import pandas as pd
import hashlib
import aiofiles
import aiofiles.os
import asyncio
import sqlalchemy
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import create_engine, inspect, func, select
from func_timeout import func_timeout, FunctionTimedOut
from mintq.schema import SQLSchema, SQLTableSchema, SQLColumnSchema, ForeignKeySchema


class SQLAlchemyConnector:
    def __init__(self, name: str, sqlalchemy_engine: AsyncEngine, schema: SQLSchema):
        self.name = name
        self.engine = sqlalchemy_engine
        self.schema = schema

    @classmethod
    async def from_url_async(cls, name: str, url: str | SQLAlchemyURL, **engine_kwargs: Any) -> "SQLAlchemyConnector":
        # Ensure echo is False by default if not specified, to avoid excessive logging from engine
        engine_kwargs.setdefault("echo", False)
        engine = create_async_engine(url, **engine_kwargs)
        schema = await cls._load_schema_with_cache_async(name, engine)
        return cls(name, engine, schema)

    @classmethod
    async def _load_schema_with_cache_async(cls, name: str, engine: AsyncEngine) -> SQLSchema:
        """
        Loads the database schema, utilizing a cache if available and enabled.
        Sets the `self.schema` attribute.
        """
        cache_dir = os.getenv("MINTQ_CACHE_DIR", "cache")
        cache_enabled = os.getenv("MINTQ_CACHE_ENABLED", "1") == "1"
        cache_refresh = os.getenv("MINTQ_CACHE_REFRESH", "0") == "1"
        schema_cache_dir = os.path.join(cache_dir, "schemas")

        await aiofiles.os.makedirs(schema_cache_dir, exist_ok=True)

        engine_url_str = str(engine.url)
        hashed = hashlib.sha256(engine_url_str.encode()).hexdigest()
        cache_path = os.path.join(schema_cache_dir, f"{name}.{hashed}.json")

        if cache_refresh and await aiofiles.os.path.exists(cache_path):
            await aiofiles.os.remove(cache_path)

        if cache_enabled and await aiofiles.os.path.exists(cache_path):
            async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
                content = await f.read()
                return SQLSchema.model_validate_json(content)

        async with engine.connect() as conn:
            dbms_supports_schema = engine.dialect not in ("sqlite", "mysql")
            schema = await conn.run_sync(cls._init_schema, name, dbms_supports_schema)

        if cache_enabled:
            async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
                await f.write(schema.model_dump_json(indent=2))
        return schema

    @staticmethod
    def _convert(value: Any) -> str | int | float | bool:
        if isinstance(value, (int, float, str, bool)):
            return value
        return str(value)

    @classmethod
    def _init_schema(cls, sync_conn: sqlalchemy.engine.Connection, name: str, dbms_supports_schema: bool) -> SQLSchema:
        tables = []
        foreign_keys = []

        inspector = inspect(sync_conn)  # sqlalchemy does not support async inspect yet as of May 2025

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
                        for row in sync_conn.execute(
                            select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(21)
                        ).fetchall()
                    ]
                    examples = [cls._convert(v) for v in examples]
                    columns.append(
                        SQLColumnSchema(
                            name=column["name"],
                            dtype=column["type"].__visit_name__,
                            examples=examples,
                        )
                    )

                primary_key = inspector.get_pk_constraint(table_name, schema=schema_name)["constrained_columns"]
                num_rows = sync_conn.execute(select(func.count()).select_from(tbl)).scalar_one()
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

    async def _run_query_without_timeout_async(
        self, query: str, parameters: Sequence[Any] = (), return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        async with self.engine.connect() as conn:  # AsyncConnection
            result = await conn.execute(sqlalchemy.text(query), parameters)
            rows = result.fetchall()
            if return_df:
                return pd.DataFrame(rows, columns=result.keys())
            return rows

    async def run_query_async(
        self,
        query: str,
        parameters: Sequence[Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        try:
            return await asyncio.wait_for(
                self._run_query_without_timeout_async(query, parameters, return_df), timeout=timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
