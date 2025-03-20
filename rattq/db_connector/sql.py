from sqlalchemy import create_engine, text
import sqlite3
from func_timeout import func_timeout, FunctionTimedOut
from rattq.db_connector.mschema_utils import MSchema, SchemaEngine
from rattq.db_connector.base import BaseDBConnector
from smolagents import tool
from rattq.utils import truncate_content

class SQLiteConnector(BaseDBConnector):
    def __init__(self, name: str, db_path: str):
        self.name = name
        self.db_path = db_path
        self._schema = self._get_mschema()

    def _get_mschema(self):
        # adapted from https://github.com/XGenerationLab/M-Schema
        db_engine = create_engine(f"sqlite:///{self.db_path}")
        schema_engine = SchemaEngine(engine=db_engine, db_name=self.name)
        mschema = schema_engine.mschema
        mschema_str = mschema.to_mschema()
        return mschema_str

    def get_schema(self) -> str:
        return self._schema

    def _run_query_without_timeout(self, query: str) -> list:
        # conn = sqlite3.connect(self.db_path)
        # cursor = conn.cursor()
        # cursor.execute(query)
        # result = cursor.fetchall()
        # conn.close()
        # return result
        db_engine = create_engine(f"sqlite:///{self.db_path}")
        with db_engine.connect() as conn:
            result = conn.execute(text(query))
            return result.fetchall()

    def run_query(self, query: str, timeout: int = 30) -> list:
        try:
            return func_timeout(timeout, self._run_query_without_timeout, args=(query,))
        except FunctionTimedOut:
            raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
        except Exception as e:
            raise

    def as_smolagent_tools(self, max_length_chars: int = 1000):
        def _format_result(result: list) -> str:
            res = "\n".join([str(row) for row in result])
            if max_length_chars > 0 and len(res) > max_length_chars:
                res = truncate_content(res, max_length_chars)
            if res == "":
                res = "QUERY RESULT IS EMPTY"
            return res
        
        @tool
        def query_db(query: str) -> str:
            """
            Query the database with the given SQL query.

            Args:
                query: The SQL query to execute.
            """
            result = self.run_query(query)
            return _format_result(result)
        
        @tool
        def search_value(table_name: str, column_name: str, value: str) -> str:
            """
            Fuzzy search for a value in a table and column, case-insensitive.

            Args:
                table_name: The name of the table to search.
                column_name: The name of the column to search.
                value: The value to search for.
            """
            column_name = column_name.strip('"')
            query = f"SELECT DISTINCT \"{column_name}\" FROM {table_name} WHERE \"{column_name}\" LIKE '%{value}%'"
            result = self.run_query(query)
            return _format_result(result)

        return [query_db, search_value]
