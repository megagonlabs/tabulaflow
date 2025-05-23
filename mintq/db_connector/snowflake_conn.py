from typing import Any, Sequence
import snowflake.connector
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
from mintq.db_connector.sql_conn import GenericSQLConnector
from mintq.schema import SQLSchema


class SnowflakeConnector(GenericSQLConnector):
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
    def from_credentials(
        cls, name: str, sf_user: str, sf_password: str, sf_account: str, sf_database: str
    ) -> "SnowflakeConnector":
        url = f"snowflake://{sf_user}:{sf_password}@{sf_account}/{sf_database}"
        engine = create_engine(url, connect_args={"disable_ocsp_checks": True})
        schema = cls._load_schema_with_cache(name, engine)
        return cls(name, engine, schema, sf_user, sf_password, sf_account, sf_database)

    def run_query(
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
