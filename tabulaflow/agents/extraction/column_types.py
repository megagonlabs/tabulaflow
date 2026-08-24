"""Resolve target-table columns to the Python types an LLM should emit for them.

Shared by the structured-output tools (``extract_rows_from_documents`` and
``run_subagent_for_each_row``): both force an LLM to produce native typed values
keyed by output column, so the database receives an ``int``/``date``/… rather
than a string it must coerce on write (an unparseable string would otherwise
abort the write). The mapping is best-effort off the connector's introspected
schema; columns it can't resolve default to ``str``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TypeAlias

from tabulaflow.core.schema import SQLSchema
from tabulaflow.agents.tools.engines.sql import find_table

# The Python types a structured-output model can emit for a column. Restricted to
# what an LLM produces and pydantic can put in a JSON schema: JSON scalars plus
# date / datetime (serialized as ISO strings). Richer pydantic-supported types
# (Decimal, time, UUID, ...) are intentionally out of scope.
ColumnType: TypeAlias = type[str] | type[int] | type[float] | type[bool] | type[date] | type[datetime]
ALLOWED_COLUMN_TYPES: tuple[ColumnType, ...] = (str, int, float, bool, date, datetime)

# ``SQLColumnSchema.dtype`` tokens (uppercase, parameter-stripped) that map to each Python
# type. The schema stores *canonical* SQLAlchemy visit-names (e.g. DuckDB ``BIGINT`` →
# ``BIG_INTEGER``, ``VARCHAR`` → ``STRING``, ``DOUBLE`` → ``FLOAT``, ``DECIMAL`` →
# ``NUMERIC``), so these sets must list the canonical forms — raw SQL names (``BIGINT``)
# are kept too as a harmless cross-dialect fallback. Remaining text-castable tokens (TIME,
# UUID, ENUM, CHAR variants, …) fall through to ``str``; non-scalar tokens are rejected.
_INT_DTYPES = {
    "TINY_INTEGER", "SMALL_INTEGER", "INTEGER", "BIG_INTEGER",  # canonical (DuckDB workspace)
    "TINYINT", "SMALLINT", "INT", "INT2", "INT4", "INT8", "BIGINT",  # raw-SQL fallback
}  # fmt: skip
_FLOAT_DTYPES = {
    "FLOAT", "DOUBLE", "NUMERIC", "DECIMAL",  # canonical
    "REAL", "DOUBLE_PRECISION", "BIGNUMERIC",  # raw-SQL fallback
}  # fmt: skip
_BOOL_DTYPES = {"BOOLEAN", "BOOL"}

# Non-scalar column types these tools refuse to target. Structured output yields flat
# scalar values, so semi-structured (JSON/variant/array/struct/map) and binary columns are
# a category error — stringifying into them is fragile and aborts the write on strict
# backends. Rejected with an actionable error instead of a silent str fallback.
UNSUPPORTED_DTYPES = {
    "JSON", "JSONB", "VARIANT", "OBJECT", "ARRAY", "STRUCT", "MAP", "SUPER", "SQL_VARIANT",
    "BINARY", "VARBINARY", "BYTES", "BLOB", "BYTEA",  # BYTEA: DuckDB/Postgres canonical for BLOB
}  # fmt: skip


def python_type_for_dtype(dtype: str) -> ColumnType:
    """Map a canonical SQL dtype token to the Python type the LLM should emit.

    Numeric, boolean, and date/timestamp columns get a native type; ``TIMESTAMP*``
    variants all flatten to a naive ``datetime`` (timezone precision is out of scope).
    Unknown or non-scalar tokens map to ``str``, so the default arm covers every type the
    model can't represent natively (TIME, JSON/ARRAY/STRUCT, UUID, BINARY, …) without
    regressing them.
    """
    token = dtype.upper()
    if token in _BOOL_DTYPES:
        return bool
    if token in _INT_DTYPES:
        return int
    if token in _FLOAT_DTYPES:
        return float
    if token == "DATE":
        return date
    if token == "DATETIME" or token.startswith("TIMESTAMP"):
        return datetime
    return str


def resolve_column_types(
    schema: SQLSchema,
    schema_name: str | None,
    table_name: str,
    output_columns: list[str],
) -> tuple[dict[str, ColumnType], list[str]]:
    """Resolve each output column's emit-type off the introspected schema.

    Args:
        schema: The connector's introspected schema.
        schema_name: Schema containing ``table_name`` (``None`` if unqualified).
        table_name: Target table whose columns are being written.
        output_columns: Columns the LLM will populate.

    Returns:
        ``(column_types, unsupported)`` where ``column_types`` maps each resolved
        column to its Python emit-type (unresolved columns are simply absent and
        default to ``str`` downstream), and ``unsupported`` is a list of
        ``"name (dtype)"`` strings for non-scalar columns that cannot be targeted
        (caller should error out when non-empty).
    """
    table = find_table(schema, schema_name, table_name)
    if table is None:
        return {}, []
    cols = [c for c in table.columns if c.name in output_columns]
    unsupported = [f"{c.name} ({c.dtype})" for c in cols if c.dtype in UNSUPPORTED_DTYPES]
    column_types = {c.name: python_type_for_dtype(c.dtype) for c in cols}
    return column_types, unsupported
