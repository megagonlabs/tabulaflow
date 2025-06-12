from typing import Any, Sequence, Mapping, Literal
from dataclasses import dataclass
import pandas as pd
import asyncio
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine
from mintq.db_connector.sqlalchemy_utils import load_schema_with_cache_async, ThrottledEngine
from mintq.schema import SQLSchema


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
