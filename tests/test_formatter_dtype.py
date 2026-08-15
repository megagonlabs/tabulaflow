"""Tests for native_dtype rendering in schema formatters."""

from tabulaflow.core import ForeignKeySchema, SQLColumnSchema, SQLSchema, SQLTableSchema
from tabulaflow.output.formatting import render_column_dtype
from tabulaflow.output.schema_formatters.sql_basic import SQLBasicSchemaFormatter
from tabulaflow.output.schema_formatters.sql_ddl import SQLDDLSchemaFormatter


def _col(name: str, dtype: str, native_dtype: str | None) -> SQLColumnSchema:
    return SQLColumnSchema(
        name=name,
        dtype=dtype,
        native_dtype=native_dtype,
        nullable=True,
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


def test_render_column_dtype_prefers_short_native() -> None:
    assert render_column_dtype(_col("a", "VARCHAR", "VARCHAR(100)")) == "VARCHAR(100)"
    assert render_column_dtype(_col("b", "DECIMAL", "DECIMAL(18, 2)")) == "DECIMAL(18, 2)"


def test_render_column_dtype_falls_back_when_native_missing() -> None:
    assert render_column_dtype(_col("a", "VARCHAR", None)) == "VARCHAR"


def test_render_column_dtype_falls_back_when_native_too_long() -> None:
    long_native = "STRUCT(" + ", ".join(f"f{i} VARCHAR" for i in range(40)) + ")"
    assert len(long_native) > 80
    col = _col("a", "STRUCT", long_native)
    assert render_column_dtype(col, max_native_dtype_chars=80) == "STRUCT"


def test_render_column_dtype_cap_is_configurable() -> None:
    col = _col("a", "VARCHAR", "VARCHAR(100)")
    assert render_column_dtype(col, max_native_dtype_chars=5) == "VARCHAR"
    assert render_column_dtype(col, max_native_dtype_chars=20) == "VARCHAR(100)"


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


def test_formatters_derive_primary_and_foreign_key_markers_from_table() -> None:
    foreign_key = ForeignKeySchema(
        columns=["customer_id"],
        referenced_schema_name="public",
        referenced_table="customers",
        referenced_columns=["id"],
    )
    table = SQLTableSchema(
        name="orders",
        schema_name="public",
        is_view=False,
        columns=[_col("id", "INTEGER", None), _col("customer_id", "INTEGER", None)],
        primary_key=["id"],
        foreign_keys=[foreign_key],
    )

    basic = SQLBasicSchemaFormatter().format_table(table, dialect="postgres")
    ddl = SQLDDLSchemaFormatter().format_table(table, dialect="postgres")

    assert '"id": INTEGER' in basic and "[PK]" in basic
    assert '"customer_id": INTEGER' in basic and '[FK -> public.customers."id"]' in basic
    assert '"id" INTEGER NULL PRIMARY KEY' in ddl
    assert 'FOREIGN KEY ("customer_id") REFERENCES public.customers("id")' in ddl


def test_format_table_uses_explicit_dialect_without_retaining_state() -> None:
    table = _table(_col("item name", "INTEGER", None))
    formatter = SQLDDLSchemaFormatter()

    bigquery = formatter.format_table(table, dialect="bigquery")
    postgres = formatter.format_table(table, dialect="postgres")

    assert "CREATE TABLE items (\n    `item name` INTEGER" in bigquery
    assert 'CREATE TABLE items (\n    "item name" INTEGER' in postgres


def test_schema_column_limit_prioritizes_complete_key_relationships() -> None:
    foreign_key = ForeignKeySchema(
        columns=["customer_id"],
        referenced_schema_name="public",
        referenced_table="customers",
        referenced_columns=["id"],
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
    schema = SQLSchema(name="shop", dialect="postgres", tables=[customers, orders])

    formatted = SQLDDLSchemaFormatter(max_total_columns=2).format(schema)

    assert 'CREATE TABLE public.customers (\n    "id" INTEGER NULL PRIMARY KEY' in formatted
    assert (
        'CREATE TABLE public.orders (\n    "id" INTEGER NULL PRIMARY KEY,\n    "customer_id" INTEGER NULL,' in formatted
    )
    assert 'FOREIGN KEY ("customer_id") REFERENCES public.customers("id")' in formatted
    assert '"name"' not in formatted
    assert '"total"' not in formatted
