from sqlalchemy import create_engine
import os
import snowflake.connector
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
    ):
        super().__init__(
            name,
            create_engine(f"snowflake://{sf_user}:{sf_password}@{sf_account}/{sf_database}"),
        )
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self.sf_database = sf_database

    def run_query(self, query: str, parameters=(), timeout: int = 30) -> list:
        with snowflake.connector.connect(
            user=self.sf_user,
            password=self.sf_password,
            account=self.sf_account,
        ) as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters, timeout=timeout)
            return cursor.fetchall()


if __name__ == "__main__":
    import json
    import time
    from rattq.schema_formatter import get_schema_formatter

    t0 = time.time()
    connector = SnowflakeConnector(
        "AIRLINES", os.environ["SF_USER"], os.environ["SF_PASSWORD"], os.environ["SF_ACCOUNT"], "AIRLINES"
    )
    formatter = get_schema_formatter("sql_default")
    print(formatter.format(connector.schema))
    print(f"Time taken: {time.time() - t0} seconds")
