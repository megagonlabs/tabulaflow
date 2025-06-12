from typing import Any, Sequence, Mapping, Literal
from dataclasses import dataclass
import pandas as pd
import asyncio
from contextlib import asynccontextmanager
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine
from mintq.db_connector.sqlalchemy_utils import load_schema_with_cache_async, ThrottledEngine
from mintq.schema import SQLSchema


@dataclass
class SQLConnector:
    name: str
    schema: SQLSchema
    _t_eng: ThrottledEngine

    @property
    def engine_type(self) -> Literal["async", "sync"]:
        return self._t_eng.engine_type

    @property
    def engine(self) -> AsyncEngine | sqlalchemy.engine.Engine:
        return self._t_eng.engine

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

        with self._t_eng.throttle():
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
