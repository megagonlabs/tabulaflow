import sqlalchemy
from sqlalchemy import create_engine, inspect, select, func
import os
import rattq.db_connector.snowflake_conn as snowflake_conn
import snowflake.connector
from func_timeout import func_timeout, FunctionTimedOut
from rattq.db_connector.base_sql_conn import BaseSQLConnector
from rattq.schema import *


class SnowflakeConnector(BaseSQLConnector):
    def __init__(
        self,
        name: str,
        sf_user: str,
        sf_password: str,
        sf_account: str,
        sf_database: str,
        sf_schema: str,
    ):
        super().__init__(
            name,
            create_engine(
                f"snowflake://{sf_user}:{sf_password}@{sf_account}/{sf_database}/{sf_schema}"
            ),
        )
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self.sf_database = sf_database
        self.sf_schema = sf_schema
        self._conn = None

    def run_query(self, query: str, parameters=(), timeout: int = 30) -> list:
        if self._conn is None:
            self._conn = snowflake.connector.connect(
                user=self.user,
                password=self.password,
                account=self.account,
            )
        return self._conn.execute(query, parameters, timeout=timeout)

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None


if __name__ == "__main__":
    import json
    from rattq.schema_formatter import get_schema_formatter

    connector = SnowflakeConnector(
        "AIRLINES",
        os.environ["SF_USER"],
        os.environ["SF_PASSWORD"],
        os.environ["SF_ACCOUNT"],
        "AIRLINES",
        "AIRLINES",
    )
    formatter = get_schema_formatter("sql_default")
    print(formatter.format(connector.schema))
