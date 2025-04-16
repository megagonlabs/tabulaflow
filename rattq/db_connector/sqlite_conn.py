import sqlalchemy
from sqlalchemy import create_engine, inspect, select, func
import sqlite3
from func_timeout import func_timeout, FunctionTimedOut
from rattq.db_connector.base_sql_conn import BaseSQLConnector
from rattq.schema import *


class SQLiteConnector(BaseSQLConnector):
    def __init__(self, name: str, sqlite_db_path: str):
        super().__init__(name, create_engine(f"sqlite:///{sqlite_db_path}"))
        self.sqlite_db_path = sqlite_db_path

    def _run_query_without_timeout(self, query: str, parameters=()) -> list:
        with sqlite3.connect(self.sqlite_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            result = cursor.fetchall()
        return result

    def run_query(self, query: str, parameters=(), timeout: int = 30) -> list:
        try:
            return func_timeout(
                timeout, self._run_query_without_timeout, args=(query, parameters)
            )
        except FunctionTimedOut:
            raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
        except Exception as e:
            raise


if __name__ == "__main__":
    import json
    from rattq.schema_formatter import get_schema_formatter

    connector = SQLiteConnector("california_school", "test.db")
    schema = connector.schema
    formatter = get_schema_formatter("sql_default")
    print(formatter.format(schema))
