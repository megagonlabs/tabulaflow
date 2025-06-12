from typing import Any, Sequence, Mapping, Literal
from dataclasses import dataclass
import pandas as pd
import asyncio
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine
from mintq.db_connector.sqlalchemy_utils import load_schema_with_cache_async
from mintq.schema import SQLSchema


@dataclass
class SQLConnector:
    name: str
    engine_type: Literal["async", "sync"]
    engine: AsyncEngine | sqlalchemy.engine.Engine
    schema: SQLSchema
    _semaphore: asyncio.Semaphore

    @classmethod
    async def from_url_async(
        cls,
        name: str,
        engine_type: Literal["async", "sync"],
        url: str | SQLAlchemyURL,
        pool_size: int = 8,
        **engine_kwargs: Any,
    ) -> "SQLConnector":
        engine_kwargs.setdefault("echo", False)  # avoid excessive logging from engine
        if engine_type == "async":
            engine = create_async_engine(url, pool_size=pool_size, **engine_kwargs)
        else:
            engine = create_engine(url, pool_size=pool_size, **engine_kwargs)
        schema = await load_schema_with_cache_async(name, engine)
        return cls(name, engine_type, engine, schema, asyncio.Semaphore(pool_size))

    def _run_statement(
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
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        statement = sqlalchemy.text(query) if isinstance(query, str) else query
        async with self._semaphore:
            try:
                if self.engine_type == "async":
                    async with self.engine.connect() as conn:
                        result = await asyncio.wait_for(conn.execute(statement, parameters), timeout=timeout)
                        rows = result.fetchall()
                        if return_df:
                            return pd.DataFrame(rows, columns=result.keys())
                        return rows
                else:
                    loop = asyncio.get_running_loop()
                    return await asyncio.wait_for(
                        loop.run_in_executor(None, self._run_statement, statement, parameters, return_df),
                        timeout=timeout,
                    )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
