import asyncio
from typing import Any, Sequence
import snowflake.connector
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
from mintq.db_connector.sql_conn import SQLAlchemyConnector
from mintq.schema import SQLSchema


class SnowflakeConnector(SQLAlchemyConnector):
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
        super().__init__(name, engine, schema)
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self.sf_database = sf_database

    @classmethod
    async def from_credentials_async(
        cls, name: str, sf_user: str, sf_password: str, sf_account: str, sf_database: str
    ) -> "SnowflakeConnector":
        url = f"snowflake://{sf_user}:{sf_password}@{sf_account}/{sf_database}"
        engine = create_engine(url, connect_args={"disable_ocsp_checks": True})
        schema = await cls._load_schema_with_cache_async(name, engine)
        return cls(name, engine, schema, sf_user, sf_password, sf_account, sf_database)

    def _run_query_sync(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30, return_df: bool = False
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

    async def run_query_async(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30, return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_query_sync, query, parameters, timeout, return_df)
