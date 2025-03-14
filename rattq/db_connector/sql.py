from sqlalchemy import create_engine, text
import sqlite3
from func_timeout import func_timeout, FunctionTimedOut
from rattq.db_connector.mschema_utils import MSchema, SchemaEngine
from rattq.db_connector.base import BaseDBConnector


class SQLiteConnector(BaseDBConnector):
    def __init__(self, name: str, db_path: str):
        self.name = name
        self.db_path = db_path
        self._schema = self._get_mschema()

    def _get_mschema(self):
        # adapted from https://github.com/XGenerationLab/M-Schema
        db_engine = create_engine(f'sqlite:///{self.db_path}')
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
        db_engine = create_engine(f'sqlite:///{self.db_path}')
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
