import copy
from collections.abc import Iterator
from typing import Any, Literal, TypeAlias, Union

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from tabulaflow.core.serialization import _deserialize_dataframe, _sanitize_df, _serialize_dataframe

NumericOrNull: TypeAlias = Union[float, int, None]

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

    def get_node(self, label: str) -> NodeSchema:
        for n in self.nodes:
            if n.label == label:
                return n
        raise ValueError(f"Node type {label!r} not found.")

    def get_relationship(self, label: str) -> RelationshipSchema:
        for r in self.relationships:
            if r.label == label:
                return r
        raise ValueError(f"Relationship type {label!r} not found.")

    def iter_patterns(self) -> Iterator[tuple[str, str, str]]:
        """Yield ``(label, source_label, target_label)`` for every endpoint."""
        for rel in self.relationships:
            for endpoint in rel.endpoints:
                yield (rel.label, endpoint.source_label, endpoint.target_label)


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
    detailed_description_markdown: str | None = None
    """Markdown-formatted detailed description of the column"""
    json_schema: dict[str, Any] | None = None
    """JSON Schema describing the internal structure of JSON/VARIANT columns (nested objects, arrays, etc.)"""
    not_used: bool = False
    """Indicates that the column contains no valid data or has been explicitly marked as not useful"""
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

    def trim(
        self,
        column_names: list[str],
        case_insensitive: bool = True,
        keep_pk: bool = True,
    ) -> "SQLTableSchema | None":
        """Return a trimmed copy keeping only the specified columns.

        Args:
            column_names: Column names to retain.
            case_insensitive: If True, column name matching ignores case.
            keep_pk: If True, primary-key columns are always retained.

        Returns:
            A deep-copied ``SQLTableSchema`` with only the matched columns,
            or ``None`` if no columns remain after trimming.
        """

        def normalize(s: str) -> str:
            return s.lower() if case_insensitive else s

        normalized_names = {normalize(n) for n in column_names}

        new_columns = [
            col for col in self.columns if normalize(col.name) in normalized_names or (keep_pk and col.primary_key_type)
        ]
        if not new_columns:
            return None

        table = copy.deepcopy(self)
        table.columns = new_columns

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

    def get_all_table_refs(self) -> list[TableRef]:
        return [TableRef(schema_name=table.schema_name, table_name=table.name) for table in self.tables]

    def get_table_by_ref(self, table_ref: TableRef) -> SQLTableSchema:
        for table in self.tables:
            if table.schema_name == table_ref.schema_name and table.name == table_ref.table_name:
                return table
        raise ValueError(f"Table {table_ref.table_name} not found.")

    def get_all_column_refs(self) -> list[ColumnRef]:
        return [
            ColumnRef(schema_name=table.schema_name, table_name=table.name, column_name=column.name)
            for table in self.tables
            for column in table.columns
        ]

    def get_column_by_ref(self, column_ref: ColumnRef) -> SQLColumnSchema:
        for table in self.tables:
            if table.schema_name == column_ref.schema_name and table.name == column_ref.table_name:
                for column in table.columns:
                    if column.name == column_ref.column_name:
                        return column
        raise ValueError(f"Column {column_ref.column_name} not found in table {column_ref.table_name}.")

    def get_pk_column_refs(self) -> list[ColumnRef]:
        return [
            ColumnRef(schema_name=table.schema_name, table_name=table.name, column_name=column.name)
            for table in self.tables
            for column in table.columns
            if column.primary_key_type is not None
        ]

    def get_fk_column_refs(self) -> list[ColumnRef]:
        """Get columns involved in foreign key relationships (both outgoing and incoming)."""
        result: list[ColumnRef] = []
        seen: set[tuple[str | None, str, str]] = set()

        for table in self.tables:
            for fk in table.foreign_keys:
                # Outgoing FK columns
                for col in fk.columns:
                    key = (table.schema_name, table.name, col)
                    if key not in seen:
                        seen.add(key)
                        result.append(ColumnRef(schema_name=table.schema_name, table_name=table.name, column_name=col))
                # Incoming FK columns
                for col in fk.foreign_columns:
                    key = (fk.foreign_schema_name, fk.foreign_table, col)
                    if key not in seen:
                        seen.add(key)
                        result.append(
                            ColumnRef(schema_name=fk.foreign_schema_name, table_name=fk.foreign_table, column_name=col)
                        )

        return result

    def trim(self, column_refs: list[ColumnRef], case_insensitive: bool = True, keep_pk: bool = True) -> "SQLSchema":
        def normalize(s: str | None) -> str | None:
            return s.lower() if case_insensitive and s is not None else s

        # Group column names by (schema_name, table_name)
        columns_by_table: dict[tuple[str | None, str], set[str]] = {}
        for ref in column_refs:
            key = (normalize(ref.schema_name), normalize(ref.table_name))
            columns_by_table.setdefault(key, set()).add(ref.column_name)  # type: ignore[arg-type]

        new_tables: list[SQLTableSchema] = []
        for table in self.tables:
            table_key = (normalize(table.schema_name), normalize(table.name))
            col_names = columns_by_table.get(table_key)  # type: ignore[arg-type]
            if col_names is None:
                continue
            trimmed = table.trim(list(col_names), case_insensitive=case_insensitive, keep_pk=keep_pk)
            if trimmed is not None:
                new_tables.append(trimmed)

        schema = self.model_copy(deep=False)
        schema.tables = new_tables
        return schema
