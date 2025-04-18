from abc import ABC, abstractmethod
import sqlalchemy
from sqlalchemy import create_engine, inspect, func, select
from rattq.db_connector.base import BaseDBConnector
from rattq.schema import *


class BaseSQLConnector(BaseDBConnector):
    def __init__(self, name: str, sqlalchemy_engine):
        self._name = name
        self._schema = self._init_schema(sqlalchemy_engine)

    @property
    def name(self) -> str:
        return self._name

    @property
    def schema(self) -> SQLSchema:
        return self._schema

    def _init_schema(self, engine) -> SQLSchema:
        """Initialize and return the database schema."""
        tables = []
        foreign_keys = []

        inspector = inspect(engine)

        with engine.connect() as conn:
            # if sqlite, there is no schema
            if engine.dialect.name == "sqlite":
                schema_names = [None]
            else:
                schema_names = inspector.get_schema_names()

            for schema_name in schema_names:
                for table_name in inspector.get_table_names(schema=schema_name):
                    columns = []
                    for column in inspector.get_columns(table_name, schema=schema_name):
                        col = sqlalchemy.column(column["name"])
                        tbl = sqlalchemy.table(table_name, schema=schema_name)

                        cardinality = conn.execute(
                            select(func.count(col.distinct()))
                            .select_from(tbl)
                            .where(col.isnot(None))
                        ).fetchone()[0]
                        examples = [
                            row[0]
                            for row in conn.execute(
                                select(col)
                                .distinct()
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
                                examples=examples,
                            )
                        )

                    primary_key = inspector.get_pk_constraint(table_name, schema=schema_name)[
                        "constrained_columns"
                    ]
                    num_rows = conn.execute(
                        select(func.count()).select_from(tbl)
                    ).fetchone()[0]
                    for fk in inspector.get_foreign_keys(table_name, schema=schema_name):
                        foreign_keys.append(
                            ForeignKeySchema(
                                schema_name=schema_name,
                                table=table_name,
                                columns=fk["constrained_columns"],
                                foreign_schema_name=fk["referred_schema"],
                                foreign_table=fk["referred_table"],
                                foreign_columns=fk["referred_columns"],
                            )
                        )

                    tables.append(
                        SQLTableSchema(
                            name=table_name,
                            schema_name=schema_name,
                            columns=columns,
                            primary_key=primary_key,
                            num_rows=num_rows,
                        )
                    )

        return SQLSchema(name=self.name, tables=tables, foreign_keys=foreign_keys)
