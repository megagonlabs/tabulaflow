import asyncio
from typing import Any, Sequence
import snowflake.connector
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
from mintq.schema import SQLSchema
from mintq.db_connector.sqlalchemy_utils import load_schema_with_cache_async
from urllib.parse import quote_plus


class SnowflakeConnector:
    def __init__(
        self,
        name: str,
        engine: sqlalchemy.engine.Engine,
        schema: SQLSchema,
        sf_user: str,
        sf_password: str,
        sf_account: str,
        sf_database: str,
    ):
        self.name = name
        self.engine = engine
        self.schema = schema
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self.sf_database = sf_database

    @classmethod
    async def from_credentials_async(
        cls,
        name: str,
        sf_user: str,
        sf_password: str,
        sf_account: str,
        sf_database: str,
        pool_size: int = 10,
        **engine_kwargs: Any,
    ) -> "SnowflakeConnector":
        encoded_user = quote_plus(sf_user)
        encoded_password = quote_plus(sf_password)
        url = f"snowflake://{encoded_user}:{encoded_password}@{sf_account}/{sf_database}"
        engine = create_engine(url, connect_args={"disable_ocsp_checks": True}, pool_size=pool_size, **engine_kwargs)
        schema = await load_schema_with_cache_async(name, engine)
        return cls(name, engine, schema, sf_user, sf_password, sf_account, sf_database)

    def _run_query(
        self, query: str, parameters: Sequence[Any] | dict[str, Any] = (), timeout: int = 30, return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        with snowflake.connector.connect(
            user=self.sf_user,
            password=self.sf_password,
            account=self.sf_account,
            database=self.sf_database,
            disable_ocsp_checks=True,
        ) as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters, timeout=timeout)
            results = cursor.fetchall()
            if return_df:
                return pd.DataFrame(results, columns=[desc[0] for desc in cursor.description])
            else:
                return results

    def _run_statement(
        self,
        statement: sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | dict[str, Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        with self.engine.connect() as conn:
            try:
                result = conn.execute(statement, parameters)
                rows = result.fetchall()
                if return_df:
                    return pd.DataFrame(rows, columns=result.keys())
                return rows
            except asyncio.TimeoutError:
                raise TimeoutError(f"Statement {statement} timed out after {timeout} seconds")

    async def run_query_async(
        self,
        query: str | sqlalchemy.sql.expression.Executable,
        parameters: Sequence[Any] | dict[str, Any] = (),
        timeout: int = 30,
        return_df: bool = False,
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        loop = asyncio.get_running_loop()

        if isinstance(query, str):
            return await loop.run_in_executor(None, self._run_query, query, parameters, timeout, return_df)
        else:
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(None, self._run_statement, query, parameters, timeout, return_df),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
