from sqlalchemy import create_engine
import sqlite3
import pandas as pd
from func_timeout import func_timeout, FunctionTimedOut
from mintq.db_connector.sql_conn import GenericSQLConnector


class SQLiteConnector(GenericSQLConnector):
    def __init__(self, name: str, sqlite_db_path: str):
        super().__init__(name, create_engine(f"sqlite:///{sqlite_db_path}"))
        self.sqlite_db_path = sqlite_db_path

    def _run_query_without_timeout(self, query: str, parameters=(), return_df: bool = False) -> list:
        with sqlite3.connect(self.sqlite_db_path) as conn:
            if return_df:
                return pd.read_sql_query(query, conn, params=parameters)
            else:
                cursor = conn.cursor()
                cursor.execute(query, parameters)
                return cursor.fetchall()

    def run_query(self, query: str, parameters=(), timeout: int = 30, return_df: bool = False) -> list:
        try:
            return func_timeout(timeout, self._run_query_without_timeout, args=(query, parameters, return_df))
        except FunctionTimedOut:
            raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
        except Exception as e:
            raise


if __name__ == "__main__":
    import json
    from mintq.schema_formatter import get_schema_formatter

    connector = SQLiteConnector("california_school", "test.db")
    schema = connector.schema
    formatter = get_schema_formatter("sql_default")
    print(formatter.format(schema))
