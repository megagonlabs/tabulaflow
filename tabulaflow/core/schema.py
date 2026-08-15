from typing import Any, Literal, TypeAlias

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from tabulaflow.core.serialization import _deserialize_dataframe, _sanitize_df, _serialize_dataframe

SQLDialect: TypeAlias = Literal[
    "athena",
    "bigquery",
    "clickhouse",
    "databricks",
    "doris",
    "duckdb",
    "hive",
    "mysql",
    "oracle",
    "postgres",
    "presto",
    "redshift",
    "snowflake",
    "spark",
    "sqlite",
    "starrocks",
    "teradata",
    "trino",
    "tsql",
]

NonSQLLanguage: TypeAlias = Literal["cypher", "mongo"]


# ---------------------------------------------------------------------------
# Property-graph schema (Neo4j, Neptune, etc.)
# ---------------------------------------------------------------------------


class GraphPropertySchema(BaseModel):
    """A single property on a node type or relationship type."""

    name: str
    dtype: str
    """Database-reported type string (e.g. ``"STRING"``, ``"INTEGER"``, ``"LIST OF STRING"``)."""
    description: str | None = None


class NodeSchema(BaseModel):
    """Schema for one node label."""

    label: str
    description: str | None = None
    properties: list[GraphPropertySchema] = Field(default_factory=list)


class RelationshipEndpoint(BaseModel):
    """One (source, target) connectivity pattern for a relationship type."""

    source_label: str
    target_label: str


class RelationshipSchema(BaseModel):
    """Schema for one relationship type and all node patterns it connects."""

    label: str
    endpoints: list[RelationshipEndpoint] = Field(default_factory=list)
    description: str | None = None
    properties: list[GraphPropertySchema] = Field(default_factory=list)


class PropertyGraphSchema(BaseModel):
    """Property-graph schema usable with any graph database."""

    name: str
    description: str | None = None
    nodes: list[NodeSchema] = Field(default_factory=list)
    relationships: list[RelationshipSchema] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SQL schema (MySQL, PostgreSQL, Snowflake, BigQuery, etc.)
# ---------------------------------------------------------------------------


class ForeignKeySchema(BaseModel):
    columns: list[str]
    foreign_schema_name: str | None = None
    foreign_table: str
    foreign_columns: list[str]


class SQLColumnSchema(BaseModel):
    name: str
    dtype: str
    """Canonical atomic type token (e.g. ``VARCHAR``, ``BIGINT``, ``ARRAY``, ``STRUCT``).
    Used for categorical type-class checks. See ``native_dtype`` for the dialect-native string."""
    native_dtype: str | None = None
    """Dialect-native type string preserving parameters/nested shape
    (e.g. ``VARCHAR(100)`` on Postgres, ``STRUCT(a INT, b VARCHAR)`` on DuckDB,
    ``ARRAY<STRING>`` on BigQuery). Best-effort: ``None`` when neither SQLAlchemy
    nor the dialect catalog could resolve it."""
    description: str | None = None
    """Concise description of the column"""
    json_schema: dict[str, Any] | None = None
    """JSON Schema describing the internal structure of JSON/VARIANT columns (nested objects, arrays, etc.)"""
    nullable: bool
    null_ratio: float | None = None
    num_unique: int | None = None  # Only for text or integer columns
    unique_ratio: float | None = None  # Only for text or integer columns
    examples: list[Any]
    primary_key_type: Literal["single", "composite"] | None = None
    foreign_keys: list[ForeignKeySchema] = Field(default_factory=list)  # Includes composite foreign keys


class NamePattern(BaseModel):
    pattern: str
    """(e.g. "events_{YYYYMMDD}")"""
    comment: str | None = None
    """(e.g. "YYYYMMDD from 20200101 to 20200102")"""
    original_names: list[str] = Field(default_factory=list)
    """The original table names in the compressed schema (e.g. ["events_20200101", "events_20200102"])"""


class SQLTableSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    name_patterns: list[NamePattern] = Field(default_factory=list)
    """All variations of the table name in the compressed schema."""
    schema_name: str | None = None
    """null for DBMS that does not support schemas such as SQLite"""
    description: str | None = None
    is_view: bool
    columns: list[SQLColumnSchema]
    primary_key: list[str]
    num_rows: int | None = None
    foreign_keys: list[ForeignKeySchema]
    sampled_df: pd.DataFrame | None = None

    @field_serializer("sampled_df", when_used="always")
    def serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        return _serialize_dataframe(df)

    @field_validator("sampled_df", mode="before")
    @classmethod
    def deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)

    @model_validator(mode="after")
    def sanitize_sampled_df(self) -> "SQLTableSchema":
        if self.sampled_df is not None:
            self.sampled_df = _sanitize_df(self.sampled_df)
        return self

    def select_columns(
        self,
        column_names: list[str],
        *,
        case_insensitive: bool = True,
        include_primary_key: bool = True,
    ) -> "SQLTableSchema":
        """Return a copy containing only the selected columns.

        Args:
            column_names: Column names to retain.
            case_insensitive: If True, column name matching ignores case.
            include_primary_key: If True, primary-key columns are always retained.

        Returns:
            A deep-copied table with only the selected columns and applicable constraints.
        """

        def normalize(s: str) -> str:
            return s.lower() if case_insensitive else s

        normalized_names = {normalize(n) for n in column_names}
        if include_primary_key:
            normalized_names.update(normalize(name) for name in self.primary_key)

        table = self.model_copy(deep=True)
        table.columns = [column for column in table.columns if normalize(column.name) in normalized_names]
        selected_names = {normalize(column.name) for column in table.columns}

        if not all(normalize(name) in selected_names for name in table.primary_key):
            table.primary_key = []
        table.foreign_keys = [
            foreign_key
            for foreign_key in table.foreign_keys
            if all(normalize(name) in selected_names for name in foreign_key.columns)
        ]

        primary_key_type: Literal["single", "composite"] | None = None
        if table.primary_key:
            primary_key_type = "single" if len(table.primary_key) == 1 else "composite"
        primary_key_names = {normalize(name) for name in table.primary_key}
        for column in table.columns:
            column.primary_key_type = primary_key_type if normalize(column.name) in primary_key_names else None
            column.foreign_keys = [
                foreign_key
                for foreign_key in table.foreign_keys
                if normalize(column.name) in {normalize(name) for name in foreign_key.columns}
            ]

        if table.sampled_df is not None:
            remaining_col_names = [col.name for col in table.columns]
            cols_to_keep = [c for c in remaining_col_names if c in table.sampled_df.columns]
            table.sampled_df = table.sampled_df[cols_to_keep] if cols_to_keep else pd.DataFrame()

        return table


class ColumnRef(BaseModel):
    schema_name: str | None = None
    table_name: str
    column_name: str


class TableRef(BaseModel):
    schema_name: str | None = None
    table_name: str


class SQLSchema(BaseModel):
    name: str
    """Database name, or project name for BigQuery."""
    dialect: SQLDialect | None = None
    description: str | None = None
    tables: list[SQLTableSchema]

    def num_total_columns(self) -> int:
        return sum(len(table.columns) for table in self.tables)

    def table_refs(self) -> list[TableRef]:
        return [TableRef(schema_name=table.schema_name, table_name=table.name) for table in self.tables]

    def column_refs(self) -> list[ColumnRef]:
        return [
            ColumnRef(schema_name=table.schema_name, table_name=table.name, column_name=column.name)
            for table in self.tables
            for column in table.columns
        ]

    def select_columns(
        self,
        column_refs: list[ColumnRef],
        *,
        case_insensitive: bool = True,
        include_primary_keys: bool = True,
    ) -> "SQLSchema":
        def normalize(name: str) -> str:
            return name.lower() if case_insensitive else name

        def normalize_schema(name: str | None) -> str | None:
            return normalize(name) if name is not None else None

        columns_by_table: dict[tuple[str | None, str], set[str]] = {}
        for ref in column_refs:
            key = (normalize_schema(ref.schema_name), normalize(ref.table_name))
            columns_by_table.setdefault(key, set()).add(ref.column_name)

        new_tables: list[SQLTableSchema] = []
        for table in self.tables:
            table_key = (normalize_schema(table.schema_name), normalize(table.name))
            col_names = columns_by_table.get(table_key)
            if col_names is None:
                continue
            selected = table.select_columns(
                list(col_names),
                case_insensitive=case_insensitive,
                include_primary_key=include_primary_keys,
            )
            if selected.columns:
                new_tables.append(selected)

        schema = self.model_copy(deep=False)
        schema.tables = new_tables
        return schema
