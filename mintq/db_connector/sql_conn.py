from typing import Any, Sequence, Mapping
from dataclasses import dataclass
import pandas as pd
import asyncio
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from mintq.db_connector.sqlalchemy_utils import load_schema_with_cache_async
from mintq.schema import SQLSchema


@dataclass
class SQLAlchemyConnector:
    name: str
    sqlalchemy_engine: AsyncEngine
    schema: SQLSchema

    @classmethod
    async def from_url_async(
        cls, name: str, url: str | SQLAlchemyURL, pool_size: int = 8, **engine_kwargs: Any
    ) -> "SQLAlchemyConnector":
        engine_kwargs.setdefault("echo", False)  # avoid excessive logging from engine
        engine = create_async_engine(url, pool_size=pool_size, **engine_kwargs)
        schema = await load_schema_with_cache_async(name, engine)
        return cls(name, engine, schema)

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        statement = sqlalchemy.text(query) if isinstance(query, str) else query
        async with self.engine.connect() as conn:
            try:
                result = await asyncio.wait_for(conn.execute(statement, parameters), timeout=timeout)
                rows = result.fetchall()
                if return_df:
                    return pd.DataFrame(rows, columns=result.keys())
                return rows
            except asyncio.TimeoutError:
                raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
