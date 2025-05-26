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
from mintq.db_connector.sqlalchemy_utils import load_schema_with_cache_async
from mintq.schema import SQLSchema


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
        schema = await load_schema_with_cache_async(name, engine)
        return cls(name, engine, schema)

    async def run_query_async(
        self,
        query: str,
        parameters: Sequence[Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        return await self.run_statement_async(sqlalchemy.text(query), parameters, timeout, return_df)

    async def run_statement_async(
        self,
        statement: sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        async with self.engine.connect() as conn:
            try:
                result = await asyncio.wait_for(conn.execute(statement, parameters), timeout=timeout)
                rows = result.fetchall()
                if return_df:
                    return pd.DataFrame(rows, columns=result.keys())
                return rows
            except asyncio.TimeoutError:
                raise TimeoutError(f"Statement {statement} timed out after {timeout} seconds")
