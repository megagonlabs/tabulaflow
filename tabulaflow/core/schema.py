"""Schema models for SQL, property-graph, and RDF data sources."""

from typing import Annotated, Any, Literal, TypeAlias

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tabulaflow.core.dataframe import SerializableDataFrame

# Canonical TabulaFlow names; integrations translate library-specific aliases.
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
    "postgresql",
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

GraphQueryLanguage: TypeAlias = Literal["cypher", "sparql"]
QueryLanguage: TypeAlias = SQLDialect | GraphQueryLanguage
SchemaKind: TypeAlias = Literal["sql", "property_graph", "rdf"]


# ---------------------------------------------------------------------------
# Property-graph schema (Neo4j, Neptune, etc.)
# ---------------------------------------------------------------------------


class GraphPropertySchema(BaseModel):
    """A property on a node or relationship type.

    Attributes:
        types: Database-reported value types. Most properties have one type;
            schemaless graphs may contain several observed types.
    """

    name: str
    types: list[str] = Field(min_length=1)
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

    kind: Literal["property_graph"] = "property_graph"
    display_name: str
    description: str | None = None
    nodes: list[NodeSchema] = Field(default_factory=list)
    relationships: list[RelationshipSchema] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# RDF schema
# ---------------------------------------------------------------------------


class RDFSchema(BaseModel):
    """Minimal description of an RDF data source."""

    kind: Literal["rdf"] = "rdf"
    display_name: str
    description: str | None = None


# ---------------------------------------------------------------------------
# SQL schema (MySQL, PostgreSQL, Snowflake, BigQuery, etc.)
# ---------------------------------------------------------------------------


class ForeignKeySchema(BaseModel):
    """An ordered mapping from local columns to columns in a referenced table."""

    columns: list[str]
    foreign_schema_name: str | None = None
    foreign_table: str
    foreign_columns: list[str]

    @model_validator(mode="after")
    def validate_columns(self) -> "ForeignKeySchema":
        if not self.columns:
            raise ValueError("foreign key columns must not be empty")
        if len(self.columns) != len(self.foreign_columns):
            raise ValueError("foreign key columns and referenced columns must have the same length")
        return self


class SQLColumnSchema(BaseModel):
    """Structural and profiling metadata for a SQL column.

    Attributes:
        dtype: Canonical atomic type used for category checks, such as ``VARCHAR``,
            ``BIGINT``, ``ARRAY``, or ``STRUCT``.
        native_dtype: Dialect-native type preserving parameters and nested shape,
            such as ``VARCHAR(100)``, ``STRUCT(a INT, b VARCHAR)``, or
            ``ARRAY<STRING>``.
        json_schema: Inferred structure of JSON, JSONB, or VARIANT values.
        enum_values: Native enum labels, or ``None`` if unavailable. An empty
            list permits no non-null values.
        null_ratio: Fraction of rows whose value is null.
        num_unique: Number of distinct non-null values when computed.
        unique_ratio: Number of distinct non-null values divided by row count.
        examples: Representative non-null values.
    """

    name: str
    dtype: str
    native_dtype: str | None = None
    description: str | None = None
    json_schema: dict[str, Any] | None = None
    enum_values: list[str] | None = None
    nullable: bool
    null_ratio: float | None = None
    num_unique: int | None = None
    unique_ratio: float | None = None
    examples: list[Any]


class SQLTableSchema(BaseModel):
    """Structural and profiling metadata for a SQL table or view.

    Attributes:
        schema_name: Namespace containing the table, or ``None`` for databases
            without schemas, such as SQLite.
        primary_key: Ordered primary-key column names.
        num_rows: Exact physical-table row count when exhaustive profiling was
            enabled and completed successfully.
        foreign_keys: Outgoing foreign-key constraints.
        sampled_df: Sample rows used by schema browsers and formatters.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    schema_name: str | None = None
    description: str | None = None
    is_view: bool
    columns: list[SQLColumnSchema]
    primary_key: list[str]
    num_rows: int | None = None
    foreign_keys: list[ForeignKeySchema]
    sampled_df: SerializableDataFrame | None = None

    def select_columns(
        self,
        column_names: list[str],
        *,
        case_insensitive: bool = True,
        include_primary_key: bool = True,
    ) -> "SQLTableSchema":
        """Return a deep copy containing the selected columns.

        Incomplete primary- and foreign-key constraints are removed, and sample
        rows are projected to the remaining columns.

        Args:
            column_names: Column names to retain.
            case_insensitive: If True, column name matching ignores case.
            include_primary_key: If True, primary-key columns are always retained.

        Returns:
            The projected table schema.
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

        if table.sampled_df is not None:
            remaining_col_names = [col.name for col in table.columns]
            cols_to_keep = [c for c in remaining_col_names if c in table.sampled_df.columns]
            table.sampled_df = table.sampled_df[cols_to_keep] if cols_to_keep else pd.DataFrame()

        return table


class ColumnRef(BaseModel):
    """A column identifier scoped to one database."""

    schema_name: str | None = None
    table_name: str
    column_name: str


class TableRef(BaseModel):
    """A table identifier scoped to one database."""

    schema_name: str | None = None
    table_name: str


class SQLSchema(BaseModel):
    """A database-level SQL schema document.

    Attributes:
        display_name: Human-readable name for the data source.
        dialect: SQL dialect when known.
    """

    kind: Literal["sql"] = "sql"
    display_name: str
    dialect: SQLDialect | None = None
    description: str | None = None
    tables: list[SQLTableSchema]

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
        """Return a copy containing the referenced columns.

        Unreferenced tables and tables with no matching columns are omitted.

        Args:
            column_refs: Qualified columns to retain.
            case_insensitive: If True, schema, table, and column matching ignores case.
            include_primary_keys: If True, primary-key columns are retained for selected tables.

        Returns:
            The projected database schema.
        """

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


DataSourceSchema: TypeAlias = Annotated[SQLSchema | PropertyGraphSchema | RDFSchema, Field(discriminator="kind")]
