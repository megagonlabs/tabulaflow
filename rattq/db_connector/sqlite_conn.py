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
        self._conn = None

    def _run_query_without_timeout(self, query: str, args: tuple = ()) -> list:
        cursor = self._conn.cursor()
        cursor.execute(query, args)
        result = cursor.fetchall()
        return result

    def run_query(self, query: str, args: tuple = (), timeout: int = 30) -> list:
        if self._conn is None:
            self._conn = sqlite3.connect(self.sqlite_db_path)
        try:
            return func_timeout(
                timeout, self._run_query_without_timeout, args=(query, args)
            )
        except FunctionTimedOut:
            raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
        except Exception as e:
            raise

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None


if __name__ == "__main__":
    import json
    from rattq.schema_formatter import get_schema_formatter

    connector = SQLiteConnector("california_school", "test.db")
    schema = connector.schema
    formatter = get_schema_formatter("sql_default")
    print(formatter.format(schema))
