import sqlalchemy
from sqlalchemy import create_engine, text, inspect, select, distinct, func
import sqlite3
from enum import Enum
from func_timeout import func_timeout, FunctionTimedOut
from rattq.db_connector.base import BaseDBConnector
from rattq.utils import truncate_content
from pydantic import BaseModel
from typing import List, Any


class SQLColumnSchema(BaseModel):
    name: str
    type: str
    cardinality: int
    count: int
    examples: List[Any]


class SQLTableSchema(BaseModel):
    name: str
    columns: List[SQLColumnSchema]
    primary_key: List[str]
    num_rows: int


class ForeignKeySchema(BaseModel):
    table: str
    column: str
    foreign_table: str
    foreign_column: str


class SQLSchema(BaseModel):
    name: str
    tables: List[SQLTableSchema]
    foreign_keys: List[ForeignKeySchema]


class SQLiteConnector(BaseDBConnector):
    def __init__(self, name: str, db_path: str):
        self.name = name
        self.db_path = db_path
        self._engine = create_engine(f"sqlite:///{self.db_path}")
        self._inspector = inspect(self._engine)
        self._schema = self._init_schema()

    def get_schema(self) -> SQLSchema:
        return self._schema

    def _init_schema(self) -> SQLSchema:
        """Initialize and return the database schema."""
        tables = []
        foreign_keys = []

        for table_name in self._inspector.get_table_names():
            columns = []
            for column in self._inspector.get_columns(table_name):
                col = sqlalchemy.column(column["name"])
                tbl = sqlalchemy.table(table_name)
                stmt = (
                    select(func.count(distinct(col)))
                    .select_from(tbl)
                    .where(col.isnot(None))
                )
                with self._engine.connect() as conn:
                    cardinality = conn.execute(stmt).fetchone()[0]
                    count = conn.execute(
                        select(func.count()).select_from(tbl).where(col.isnot(None))
                    ).fetchone()[0]
                stmt = (
                    select(distinct(col))
                    .select_from(tbl)
                    .where(col.isnot(None))
                    .limit(20)
                )
                with self._engine.connect() as conn:
                    examples = [row[0] for row in conn.execute(stmt).fetchall()]

                columns.append(
                    SQLColumnSchema(
                        name=column["name"],
                        type=str(column["type"]).upper(),
                        cardinality=cardinality,
                        count=count,
                        examples=examples,
                    )
                )

            primary_key = self._inspector.get_pk_constraint(table_name)[
                "constrained_columns"
            ]
            with self._engine.connect() as conn:
                num_rows = conn.execute(
                    select(func.count()).select_from(tbl)
                ).fetchone()[0]
            for fk in self._inspector.get_foreign_keys(table_name):
                foreign_keys.append(
                    ForeignKeySchema(
                        table=table_name,
                        column=fk["constrained_columns"][0],
                        foreign_table=fk["referred_table"],
                        foreign_column=fk["referred_columns"][0],
                    )
                )

            tables.append(
                SQLTableSchema(
                    name=table_name,
                    columns=columns,
                    primary_key=primary_key,
                    num_rows=num_rows,
                )
            )

        return SQLSchema(name=self.name, tables=tables, foreign_keys=foreign_keys)

    def _run_query_without_timeout(self, query: str, args: tuple = ()) -> list:
        # db_engine = create_engine(f"sqlite:///{self.db_path}")
        # with db_engine.connect() as conn:
        #     result = conn.execute(text(query))
        #     return result.fetchall()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, args)
        result = cursor.fetchall()
        conn.close()
        return result

    def run_query(self, query: str, args: tuple = (), timeout: int = 30) -> list:
        try:
            return func_timeout(
                timeout, self._run_query_without_timeout, args=(query, args)
            )
        except FunctionTimedOut:
            raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
        except Exception as e:
            raise


if __name__ == "__main__":
    import json

    connector = SQLiteConnector("test", "test.db")
    schema = connector.get_schema()
    print(json.dumps(schema.model_dump(), indent=2))
