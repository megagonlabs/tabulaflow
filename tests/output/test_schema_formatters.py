"""Tests for SQL schema formatting."""

import pandas as pd

from tabulaflow.core import ForeignKeySchema, RDFSchema, SQLColumnSchema, SQLSchema, SQLTableSchema
from tabulaflow.output.formatting._sql import format_column_type
from tabulaflow.output.formatting import SPARQLSchemaFormatter, SQLBasicSchemaFormatter, SQLDDLSchemaFormatter


def _col(name: str, dtype: str, native_dtype: str | None, *, nullable: bool = True) -> SQLColumnSchema:
    return SQLColumnSchema(
        name=name,
        dtype=dtype,
        native_dtype=native_dtype,
        nullable=nullable,
        examples=[],
    )


def _table(column: SQLColumnSchema) -> SQLTableSchema:
    return SQLTableSchema(
        name="items",
        is_view=False,
        columns=[column],
        primary_key=[],
        foreign_keys=[],
    )


def _family_table(name: str, example: str, num_rows: int) -> SQLTableSchema:
    return SQLTableSchema(
        name=name,
        schema_name="analytics",
        is_view=False,
        columns=[
            SQLColumnSchema(
                name="event",
                dtype="VARCHAR",
                native_dtype="VARCHAR(100)",
                nullable=True,
                null_ratio=0.25,
                num_unique=2,
                unique_ratio=0.1,
                examples=[example],
            )
        ],
        primary_key=[],
        num_rows=num_rows,
        foreign_keys=[],
        sampled_df=pd.DataFrame({"event": [example]}),
    )


def test_sparql_formatter_renders_source_description() -> None:
    schema = RDFSchema(
        display_name="example",
        description="An example knowledge graph.",
    )

    formatted = SPARQLSchemaFormatter().format(schema)

    assert "RDF source: example (Query Language: sparql)" in formatted
    assert "Description: An example knowledge graph." in formatted
    assert "Declare any required prefixes in the SPARQL query." in formatted


def test_format_column_type_prefers_short_native() -> None:
    assert format_column_type(_col("a", "VARCHAR", "VARCHAR(100)")) == "VARCHAR(100)"
    assert format_column_type(_col("b", "DECIMAL", "DECIMAL(18, 2)")) == "DECIMAL(18, 2)"


def test_format_column_type_falls_back_when_native_missing() -> None:
    assert format_column_type(_col("a", "VARCHAR", None)) == "VARCHAR"


def test_format_column_type_falls_back_when_native_too_long() -> None:
    long_native = "STRUCT(" + ", ".join(f"f{i} VARCHAR" for i in range(40)) + ")"
    assert len(long_native) > 80
    col = _col("a", "STRUCT", long_native)
    assert format_column_type(col, max_native_dtype_chars=80) == "STRUCT"


def test_format_column_type_cap_is_configurable() -> None:
    col = _col("a", "VARCHAR", "VARCHAR(100)")
    assert format_column_type(col, max_native_dtype_chars=5) == "VARCHAR"
    assert format_column_type(col, max_native_dtype_chars=20) == "VARCHAR(100)"


def test_sql_basic_uses_native_dtype_when_short() -> None:
    fmt = SQLBasicSchemaFormatter()
    line = fmt.format_table(_table(_col("price", "DECIMAL", "DECIMAL(18, 2)")), dialect=None)
    assert "DECIMAL(18, 2)" in line


def test_sql_basic_falls_back_for_long_native() -> None:
    long_native = "STRUCT(" + ", ".join(f"f{i} VARCHAR" for i in range(40)) + ")"
    fmt = SQLBasicSchemaFormatter()
    line = fmt.format_table(_table(_col("events", "STRUCT", long_native)), dialect=None)
    assert long_native not in line
    assert "STRUCT" in line


def test_sql_ddl_uses_native_dtype_when_short() -> None:
    fmt = SQLDDLSchemaFormatter()
    line = fmt.format_table(_table(_col("price", "DECIMAL", "DECIMAL(18, 2)")), dialect=None)
    assert "DECIMAL(18, 2)" in line


def test_sql_ddl_falls_back_for_long_native() -> None:
    long_native = "STRUCT(" + ", ".join(f"f{i} VARCHAR" for i in range(40)) + ")"
    fmt = SQLDDLSchemaFormatter()
    line = fmt.format_table(_table(_col("events", "STRUCT", long_native)), dialect=None)
    assert long_native not in line


def test_sql_ddl_cap_override_at_format_time() -> None:
    """Verify the cap is a per-instance knob, not a hardcoded constant."""
    native = "VARCHAR(100)"
    col = _col("name", "VARCHAR", native)

    fmt_strict = SQLDDLSchemaFormatter(max_native_dtype_chars=5)
    assert native not in fmt_strict.format_table(_table(col), dialect=None)

    fmt_default = SQLDDLSchemaFormatter()
    assert native in fmt_default.format_table(_table(col), dialect=None)


def test_existing_columns_without_native_dtype_render_unchanged() -> None:
    """Schemas loaded from old caches won't have native_dtype set —
    must still render via the canonical dtype token."""
    fmt_basic = SQLBasicSchemaFormatter()
    fmt_ddl = SQLDDLSchemaFormatter()

    col = _col("age", "INTEGER", None)
    assert "INTEGER" in fmt_basic.format_table(_table(col), dialect=None)
    assert "INTEGER" in fmt_ddl.format_table(_table(col), dialect=None)


def test_format_table_uses_explicit_dialect_without_retaining_state() -> None:
    table = _table(_col("item name", "INTEGER", None))
    formatter = SQLDDLSchemaFormatter()

    bigquery = formatter.format_table(table, dialect="bigquery")
    postgres = formatter.format_table(table, dialect="postgresql")

    assert "CREATE TABLE items (\n    `item name` INTEGER" in bigquery
    assert 'CREATE TABLE items (\n    "item name" INTEGER' in postgres


def test_schema_column_limit_prioritizes_complete_key_relationships() -> None:
    foreign_key = ForeignKeySchema(
        columns=["customer_id"],
        foreign_schema_name="public",
        foreign_table="customers",
        foreign_columns=["id"],
    )
    customers = SQLTableSchema(
        name="customers",
        schema_name="public",
        is_view=False,
        columns=[_col("name", "VARCHAR", None), _col("id", "INTEGER", None)],
        primary_key=["id"],
        foreign_keys=[],
    )
    orders = SQLTableSchema(
        name="orders",
        schema_name="public",
        is_view=False,
        columns=[
            _col("total", "DECIMAL", None),
            _col("id", "INTEGER", None),
            _col("customer_id", "INTEGER", None),
        ],
        primary_key=["id"],
        foreign_keys=[foreign_key],
    )
    schema = SQLSchema(display_name="shop", dialect="postgresql", tables=[customers, orders])

    formatted = SQLDDLSchemaFormatter(max_total_columns=2).format(schema)

    assert 'CREATE TABLE public.customers (\n    "id" INTEGER NULL PRIMARY KEY' in formatted
    assert (
        'CREATE TABLE public.orders (\n    "id" INTEGER NULL PRIMARY KEY,\n    "customer_id" INTEGER NULL,' in formatted
    )
    assert 'FOREIGN KEY ("customer_id") REFERENCES public.customers("id")' in formatted
    assert '"name"' not in formatted
    assert '"total"' not in formatted


def test_complete_primary_and_foreign_key_formatting() -> None:
    customers = SQLTableSchema(
        name="customers",
        schema_name="public",
        is_view=False,
        columns=[_col("id", "INTEGER", None, nullable=False)],
        primary_key=["id"],
        foreign_keys=[],
    )
    orders = SQLTableSchema(
        name="orders",
        schema_name="public",
        is_view=False,
        columns=[
            _col("tenant_id", "INTEGER", None, nullable=False),
            _col("order_id", "INTEGER", None, nullable=False),
            _col("customer_id", "INTEGER", None, nullable=False),
        ],
        primary_key=["tenant_id", "order_id"],
        foreign_keys=[
            ForeignKeySchema(
                columns=["customer_id"],
                foreign_schema_name="public",
                foreign_table="customers",
                foreign_columns=["id"],
            ),
            ForeignKeySchema(
                columns=["tenant_id", "customer_id"],
                foreign_schema_name="public",
                foreign_table="customer_keys",
                foreign_columns=["tenant_id", "id"],
            ),
        ],
    )
    schema = SQLSchema(display_name="shop", dialect="postgresql", tables=[customers, orders])

    basic = SQLBasicSchemaFormatter().format(schema)
    ddl = SQLDDLSchemaFormatter(
        include_examples=False,
        include_sampled_df=False,
        include_null_ratio=False,
        include_json_schema=False,
    ).format(schema)

    assert (
        basic
        == """Database: shop (SQL Dialect: postgresql)

=== (SCHEMA: public) TABLE: customers ===
- "id": INTEGER [PK]
=== END OF TABLE ===

=== (SCHEMA: public) TABLE: orders ===
[Composite FKs]
* ("tenant_id", "customer_id") -> public.customer_keys.("tenant_id", "id")

- "tenant_id": INTEGER [PK-composite] [FK-composite]
- "order_id": INTEGER [PK-composite]
- "customer_id": INTEGER [FK -> public.customers."id"] [FK-composite]
=== END OF TABLE ==="""
    )
    assert (
        ddl
        == """**Database:** `shop`
**SQL Dialect:** `postgresql`

```sql
/*
Schema: public
Table: customers
*/
CREATE TABLE public.customers (
    "id" INTEGER NOT NULL PRIMARY KEY
);

/*
Schema: public
Table: orders
*/
CREATE TABLE public.orders (
    "tenant_id" INTEGER NOT NULL,
        -- <fk>composite</fk>
    "order_id" INTEGER NOT NULL,
    "customer_id" INTEGER NOT NULL,
        -- <fk> -> public.customers."id"</fk>
        -- <fk>composite</fk>
    PRIMARY KEY ("tenant_id", "order_id"),
    FOREIGN KEY ("customer_id") REFERENCES public.customers("id"),
    FOREIGN KEY ("tenant_id", "customer_id") REFERENCES public.customer_keys("tenant_id", "id")
);
```"""
    )


def test_sql_basic_compacted_family_format() -> None:
    schema = SQLSchema(
        display_name="warehouse",
        dialect="duckdb",
        tables=[
            _family_table("events_20240101", "open", 5),
            _family_table("events_20240102", "closed", 7),
        ],
    )

    formatted = SQLBasicSchemaFormatter(compact_table_families=True).format(schema)

    assert (
        formatted
        == """Database: warehouse (SQL Dialect: duckdb)

=== (SCHEMA: analytics) TABLE FAMILY: "events_{YYYYMMDD}" ===
Partitions: YYYYMMDD from 20240101 to 20240102 (2 total)

Representative table: events_20240101
The schema, row count, descriptions, and column profiles below come from this physical table.
Rows: 5
- "event": VARCHAR(100) NULLABLE (null_ratio=25%) {"open"}
=== END OF TABLE ==="""
    )


def test_sql_ddl_compacted_family_format() -> None:
    schema = SQLSchema(
        display_name="warehouse",
        dialect="duckdb",
        tables=[
            _family_table("events_20240101", "open", 5),
            _family_table("events_20240102", "closed", 7),
        ],
    )

    formatted = SQLDDLSchemaFormatter(compact_table_families=True).format(schema)

    assert (
        formatted
        == """**Database:** `warehouse`
**SQL Dialect:** `duckdb`

```sql
/*
Schema: analytics
Table family: "events_{YYYYMMDD}"
Partitions: YYYYMMDD from 20240101 to 20240102 (2 total)

Representative table: events_20240101
The schema, row count, descriptions, column profiles, and samples below come from this physical table.
Rows: 5
Sample rows:
| event   |
|---------|
| open    |
| ...     |
*/
CREATE TABLE analytics.events_20240101 (
    "event" VARCHAR(100) NULL
        -- <null_ratio>25%</null_ratio>
        -- <values>{'open'}</values>
);
```"""
    )
