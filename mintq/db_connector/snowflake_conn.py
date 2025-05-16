import os
import snowflake.connector
import pandas as pd
from sqlalchemy import create_engine
from mintq.db_connector.sql_conn import GenericSQLConnector


class SnowflakeConnector(GenericSQLConnector):
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
            create_engine(
                f"snowflake://{sf_user}:{sf_password}@{sf_account}/{sf_database}",
                connect_args={"disable_ocsp_checks": True},
            ),
        )
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self.sf_database = sf_database

    def run_query(self, query: str, parameters=(), timeout: int = 30, return_df: bool = False) -> list | pd.DataFrame:
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


if __name__ == "__main__":
    import time
    from mintq.schema_formatter import get_schema_formatter

    t0 = time.time()
    connector = SnowflakeConnector(
        "AIRLINES", os.environ["SF_USER"], os.environ["SF_PASSWORD"], os.environ["SF_ACCOUNT"], "AIRLINES"
    )
    formatter = get_schema_formatter("sql_default")
    print(formatter.format(connector.schema))
    print(f"Time taken: {time.time() - t0} seconds")
