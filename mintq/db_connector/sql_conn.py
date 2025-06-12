from typing import Any, Sequence, Mapping
from dataclasses import dataclass
import pandas as pd
import asyncio
import sqlalchemy
from sqlalchemy.engine.url import URL as SQLAlchemyURL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine
from mintq.db_connector.sqlalchemy_utils import load_schema_with_cache_async, get_switch_db_stmt
from mintq.schema import SQLSchema
from mintq.db_connector.engine_factory import get_engine_async


@dataclass
class SQLAlchemyConnector:
    name: str
    sqlalchemy_engine: AsyncEngine
    schema: SQLSchema
    db_to_attach: str | None = None

    @classmethod
    async def from_url_async(
        cls, name: str, url: str | SQLAlchemyURL, pool_size: int = 8, **engine_kwargs: Any
    ) -> "SQLAlchemyConnector":
        engine_kwargs.setdefault("echo", False)  # avoid excessive logging from engine
        dbms_supports_switch_db = any(url.startswith(dbms) for dbms in ("mysql", "snowflake"))
        engine = await get_engine_async(
            "async", url, mask_database=dbms_supports_switch_db, pool_size=pool_size, **engine_kwargs
        )
        db_to_attach = make_url(url).database if dbms_supports_switch_db else None
        schema = await load_schema_with_cache_async(name, engine, db_to_attach=db_to_attach)
        return cls(name, engine, schema, db_to_attach=db_to_attach)

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        statement = sqlalchemy.text(query) if isinstance(query, str) else query
        async with self.engine.connect() as conn:
            if self.db_to_attach:
                conn.execute(get_switch_db_stmt(self.engine, self.db_to_attach))
            try:
                result = await asyncio.wait_for(conn.execute(statement, parameters), timeout=timeout)
                rows = result.fetchall()
                if return_df:
                    return pd.DataFrame(rows, columns=result.keys())
                return rows
            except asyncio.TimeoutError:
                raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
