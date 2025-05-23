import os
from typing import Any, Sequence
import pandas as pd
import hashlib
import sqlalchemy
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine, inspect, func, select
from func_timeout import func_timeout, FunctionTimedOut
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


class GenericSQLConnector:
    def __init__(self, name: str, sqlalchemy_engine: sqlalchemy.engine.Engine, schema: SQLSchema):
        self.name = name
        self.schema = schema
        self.engine = sqlalchemy_engine

    @classmethod
    def from_url(cls, name: str, url: str | SQLAlchemyURL, **engine_kwargs: Any) -> "GenericSQLConnector":
        engine = create_engine(url, **engine_kwargs)
        schema = cls._load_schema_with_cache(name, engine)
        return cls(name, engine, schema)

    @classmethod
    def _load_schema_with_cache(cls, name: str, engine: sqlalchemy.engine.Engine) -> SQLSchema:
        cache_dir = os.getenv("MINTQ_CACHE_DIR", "cache")
        cache_enabled = os.getenv("MINTQ_CACHE_ENABLED", "1") == "1"
        cache_refresh = os.getenv("MINTQ_CACHE_REFRESH", "0") == "1"
        schema_cache_dir = os.path.join(cache_dir, "schemas")
        os.makedirs(schema_cache_dir, exist_ok=True)
        hashed = hashlib.sha256(str(engine.url).encode()).hexdigest()
        cache_path = os.path.join(schema_cache_dir, f"{name}.{hashed}.json")

        if cache_refresh and os.path.exists(cache_path):
            os.remove(cache_path)

        if cache_enabled and os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                return SQLSchema.model_validate_json(f.read())

        schema = cls._init_schema(name, engine)
        if cache_enabled:
            with open(cache_path, "w") as f:
                f.write(schema.model_dump_json(indent=2))
        return schema

    @staticmethod
    def _convert(value: Any) -> str | int | float | bool:
        if isinstance(value, (int, float, str, bool)):
            return value
        return str(value)

    @classmethod
    def _init_schema(cls, name: str, engine: sqlalchemy.engine.Engine) -> SQLSchema:
        """Initialize and return the database schema."""
        tables = []
        foreign_keys = []

        inspector = inspect(engine)

        with engine.connect() as conn:
            # if sqlite, there is no schema
            if engine.dialect.name in ("sqlite", "mysql"):
                schema_names = [None]
            else:
                schema_names = inspector.get_schema_names()  # type: ignore

            for schema_name in schema_names:
                if schema_name and schema_name.lower() == "information_schema":
                    continue
                for table_name in inspector.get_table_names(schema=schema_name):
                    # print(f"table_name: {table_name}, schema_name: {schema_name}")
                    columns = []
                    for column in inspector.get_columns(table_name, schema=schema_name):
                        col = sqlalchemy.column(column["name"])  # type: ignore
                        tbl = sqlalchemy.table(table_name, schema=schema_name)

                        # Note: examples will contain all possible values if cardinality <= 20
                        examples = [
                            row[0]
                            for row in conn.execute(
                                select(col).distinct().select_from(tbl).where(col.isnot(None)).limit(21)
                            ).fetchall()
                        ]
                        examples = [cls._convert(v) for v in examples]
                        columns.append(
                            SQLColumnSchema(
                                name=column["name"],
                                dtype=column["type"].__visit_name__,
                                examples=examples,
                            )
                        )

                    primary_key = inspector.get_pk_constraint(table_name, schema=schema_name)["constrained_columns"]
                    num_rows = conn.execute(select(func.count()).select_from(tbl)).scalar_one()
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

        return SQLSchema(name=name, tables=tables, foreign_keys=foreign_keys)

    def _run_query_without_timeout(
        self, query: str, parameters: Sequence[Any] = (), return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        with self.engine.connect() as conn:
            if return_df:
                return pd.read_sql_query(sqlalchemy.text(query), conn, params=parameters)
            return conn.execute(sqlalchemy.text(query), parameters).fetchall()

    def run_query(
        self, query: str, parameters: Sequence[Any] = (), timeout: int = 30, return_df: bool = False
    ) -> list[tuple[Any, ...]] | pd.DataFrame:
        try:
            return func_timeout(timeout, self._run_query_without_timeout, args=(query, parameters, return_df))
        except FunctionTimedOut:
            raise TimeoutError(f"Query {query} timed out after {timeout} seconds")
