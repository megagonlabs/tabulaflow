"""Tests for native_dtype rendering in schema formatters."""

from mintq.schema import SQLColumnSchema
from mintq.utils import render_column_dtype
from mintq.formatters.sql_basic import SQLBasicSchemaFormatter
from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter


def _col(name: str, dtype: str, native_dtype: str | None) -> SQLColumnSchema:
    return SQLColumnSchema(
        name=name,
        dtype=dtype,
        native_dtype=native_dtype,
        nullable=True,
        examples=[],
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
    fmt.set_dialect(None)
    line = fmt.format_column(_col("price", "DECIMAL", "DECIMAL(18, 2)"))
    assert "DECIMAL(18, 2)" in line


def test_sql_basic_falls_back_for_long_native() -> None:
    long_native = "STRUCT(" + ", ".join(f"f{i} VARCHAR" for i in range(40)) + ")"
    fmt = SQLBasicSchemaFormatter()
    fmt.set_dialect(None)
    line = fmt.format_column(_col("events", "STRUCT", long_native))
    assert long_native not in line
    assert "STRUCT" in line


def test_sql_ddl_uses_native_dtype_when_short() -> None:
    fmt = SQLDDLSchemaFormatter()
    fmt.set_dialect(None)
    line = fmt.format_column(_col("price", "DECIMAL", "DECIMAL(18, 2)"))
    assert "DECIMAL(18, 2)" in line


def test_sql_ddl_falls_back_for_long_native() -> None:
    long_native = "STRUCT(" + ", ".join(f"f{i} VARCHAR" for i in range(40)) + ")"
    fmt = SQLDDLSchemaFormatter()
    fmt.set_dialect(None)
    line = fmt.format_column(_col("events", "STRUCT", long_native))
    assert long_native not in line


def test_sql_ddl_cap_override_at_format_time() -> None:
    """Verify the cap is a per-instance knob, not a hardcoded constant."""
    native = "VARCHAR(100)"
    col = _col("name", "VARCHAR", native)

    fmt_strict = SQLDDLSchemaFormatter(max_native_dtype_chars=5)
    fmt_strict.set_dialect(None)
    assert native not in fmt_strict.format_column(col)

    fmt_default = SQLDDLSchemaFormatter()
    fmt_default.set_dialect(None)
    assert native in fmt_default.format_column(col)


def test_existing_columns_without_native_dtype_render_unchanged() -> None:
    """Schemas loaded from old caches won't have native_dtype set —
    must still render via the canonical dtype token."""
    fmt_basic = SQLBasicSchemaFormatter()
    fmt_basic.set_dialect(None)
    fmt_ddl = SQLDDLSchemaFormatter()
    fmt_ddl.set_dialect(None)

    col = _col("age", "INTEGER", None)
    assert "INTEGER" in fmt_basic.format_column(col)
    assert "INTEGER" in fmt_ddl.format_column(col)
