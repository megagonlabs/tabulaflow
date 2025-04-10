import sqlalchemy
from sqlalchemy import create_engine, inspect, select, distinct, func
import sqlite3
from func_timeout import func_timeout, FunctionTimedOut
from rattq.db_connector.base import BaseDBConnector
from rattq.schema import *


class SQLiteConnector(BaseDBConnector):
    def __init__(self, name: str, db_path: str):
        self.name = name
        self.db_path = db_path
        self._schema = self._init_schema()

    def get_schema(self) -> SQLSchema:
        return self._schema

    def _init_schema(self) -> SQLSchema:
        """Initialize and return the database schema."""
        tables = []
        foreign_keys = []

        engine = create_engine(f"sqlite:///{self.db_path}")
        inspector = inspect(engine)

        with engine.connect() as conn:
            for table_name in inspector.get_table_names():
                columns = []
                for column in inspector.get_columns(table_name):
                    col = sqlalchemy.column(column["name"])
                    tbl = sqlalchemy.table(table_name)

                    cardinality = conn.execute(
                        select(func.count(distinct(col)))
                        .select_from(tbl)
                        .where(col.isnot(None))
                    ).fetchone()[0]
                    count = conn.execute(
                        select(func.count()).select_from(tbl).where(col.isnot(None))
                    ).fetchone()[0]
                    examples = [
                        row[0]
                        for row in conn.execute(
                            select(distinct(col))
                            .select_from(tbl)
                            .where(col.isnot(None))
                            .limit(20)
                        ).fetchall()
                    ]

                    columns.append(
                        SQLColumnSchema(
                            name=column["name"],
                            type=str(column["type"]).upper(),
                            cardinality=cardinality,
                            count=count,
                            examples=examples,
                        )
                    )

                primary_key = inspector.get_pk_constraint(table_name)[
                    "constrained_columns"
                ]
                num_rows = conn.execute(
                    select(func.count()).select_from(tbl)
                ).fetchone()[0]
                for fk in inspector.get_foreign_keys(table_name):
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
    from rattq.schema_formatter import get_schema_formatter

    connector = SQLiteConnector("california_school", "test.db")
    schema = connector.get_schema()
    formatter = get_schema_formatter("sql_default")
    print(formatter.format(schema))
