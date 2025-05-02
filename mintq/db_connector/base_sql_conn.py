from abc import ABC, abstractmethod
import os
import json
import hashlib
import sqlalchemy
from sqlalchemy import create_engine, inspect, func, select
from mintq.db_connector.base import BaseDBConnector
from mintq.schema import SQLSchema, SQLTableSchema, SQLColumnSchema, ForeignKeySchema


# def get_base_type(col_type) -> str:
#     """
#     Given a SQLAlchemy column type instance (like VARCHAR),
#     return an its CamelCase base type (like String).

#     References:
#         - https://docs.sqlalchemy.org/en/20/core/type_basics.html
#     """
#     # Get the MRO (inheritance chain)
#     for cls in type(col_type).__mro__:
#         if cls.__name__[0].isupper() and cls.__name__ != cls.__name__.upper():  # is camelcase
#             return cls.__name__
#     return col_type.__name__


class BaseSQLConnector(BaseDBConnector):
    def __init__(self, name: str, sqlalchemy_engine_str: str):
        self._name = name
        self._schema = self._load_schema_with_cache(name, sqlalchemy_engine_str)

    @property
    def name(self) -> str:
        return self._name

    @property
    def schema(self) -> SQLSchema:
        return self._schema

    def _load_schema_with_cache(self, name: str, sqlalchemy_engine_str: str) -> SQLSchema:
        cache_dir = os.getenv("MINTQ_CACHE_DIR", "cache")
        cache_enabled = os.getenv("MINTQ_CACHE_ENABLED", "1") == "1"
        schema_cache_dir = os.path.join(cache_dir, "schemas")
        os.makedirs(schema_cache_dir, exist_ok=True)
        hashed = hashlib.sha256(sqlalchemy_engine_str.encode()).hexdigest()
        cache_path = os.path.join(schema_cache_dir, f"{name}.{hashed}.json")

        if cache_enabled and os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                return SQLSchema.model_validate_json(f.read())

        schema = self._init_schema(sqlalchemy_engine_str)
        if cache_enabled:
            with open(cache_path, "w") as f:
                f.write(schema.model_dump_json(indent=2))
        return schema

    def _convert(self, value):
        if isinstance(value, (int, float, str, bool)):
            return value
        return str(value)

    def _init_schema(self, sqlalchemy_engine_str: str) -> SQLSchema:
        """Initialize and return the database schema."""
        tables = []
        foreign_keys = []

        engine = create_engine(sqlalchemy_engine_str)
        inspector = inspect(engine)

        with engine.connect() as conn:
            # if sqlite, there is no schema
            if engine.dialect.name == "sqlite":
                schema_names = [None]
            else:
                schema_names = inspector.get_schema_names()

            for schema_name in schema_names:
                if schema_name.lower() == "information_schema":
                    continue
                for table_name in inspector.get_table_names(schema=schema_name):
                    # print(f"table_name: {table_name}, schema_name: {schema_name}")
                    columns = []
                    for column in inspector.get_columns(table_name, schema=schema_name):
                        col = sqlalchemy.column(column["name"])
                        tbl = sqlalchemy.table(table_name, schema=schema_name)

                        cardinality = conn.execute(
                            select(func.count(col.distinct())).select_from(tbl).where(col.isnot(None))
                        ).fetchone()[0]
                        examples = [
                            row[0]
                            for row in conn.execute(
                                select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(20)
                            ).fetchall()
                        ]
                        examples = [self._convert(v) for v in examples]
                        columns.append(
                            SQLColumnSchema(
                                name=column["name"],
                                type=column["type"].__class__.__name__,
                                cardinality=cardinality,
                                examples=examples,
                            )
                        )

                    primary_key = inspector.get_pk_constraint(table_name, schema=schema_name)["constrained_columns"]
                    num_rows = conn.execute(select(func.count()).select_from(tbl)).fetchone()[0]
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
