"""Shared SQL schema, quoting, and error-formatting helpers for agent tools."""

import re
from datetime import date, datetime
from typing import Any, Literal, TypeAlias

import sqlalchemy
from pydantic import BaseModel, create_model

from tabulaflow.core.schema import SQLColumnSchema, SQLSchema, SQLTableSchema


_ScalarType: TypeAlias = type[str] | type[int] | type[float] | type[bool] | type[date] | type[datetime]

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


def _unquote_identifier(identifier: str) -> str:
    if len(identifier) >= 2 and identifier[0] == identifier[-1] and identifier[0] in {'"', "`"}:
        return identifier[1:-1]
    return identifier


def _identifiers_equal(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return left is right
    return left.casefold() == right.casefold()


def find_table(schema: SQLSchema, schema_name: str | None, table_name: str) -> SQLTableSchema | None:
    """Find one table using forgiving agent-facing identifier matching."""
    requested_schema = _unquote_identifier(schema_name) if schema_name is not None else None
    requested_table = _unquote_identifier(table_name)

    name_matches = [table for table in schema.tables if _identifiers_equal(table.name, requested_table)]
    if len({table.schema_name for table in schema.tables}) == 1 or requested_schema is None:
        return name_matches[0] if len(name_matches) == 1 else None

    qualified_matches = [table for table in name_matches if _identifiers_equal(table.schema_name, requested_schema)]
    return qualified_matches[0] if len(qualified_matches) == 1 else None


def find_column(table: SQLTableSchema, column_name: str) -> SQLColumnSchema | None:
    """Find one column using forgiving agent-facing identifier matching."""
    requested_column = _unquote_identifier(column_name)
    matches = [column for column in table.columns if _identifiers_equal(column.name, requested_column)]
    return matches[0] if len(matches) == 1 else None


def _python_type_for_dtype(dtype: str) -> _ScalarType:
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


def create_column_model(
    schema: SQLSchema,
    schema_name: str | None,
    table_name: str,
    output_columns: list[str],
    *,
    name: str,
) -> type[BaseModel]:
    """Build nullable output fields from SQL column types and native enum choices.

    Reject non-scalar columns. Unresolved column types default to strings.
    """
    if not output_columns or any(not column or column.startswith("_") for column in output_columns):
        raise ValueError("output_columns must contain names without leading underscores")
    table = find_table(schema, schema_name, table_name)
    columns = {column.name: column for column in table.columns} if table is not None else {}
    fields: dict[str, Any] = {}
    for column_name in output_columns:
        column = columns.get(column_name)
        dtype: Any = str
        if column is not None:
            if column.dtype in UNSUPPORTED_DTYPES:
                raise TypeError(f"cannot target non-scalar column {column_name!r} ({column.dtype}) in {table_name}")
            dtype = _python_type_for_dtype(column.dtype)
            if column.enum_values is not None:
                dtype = Literal[tuple(column.enum_values)] if column.enum_values else Literal[None]
        fields[column_name] = (dtype | None, None)
    return create_model(name, **fields)


def format_sqlalchemy_error_msg(error_msg: str) -> str:
    """Remove generated SQL, parameters, and help links from a SQLAlchemy error."""

    error_msg = re.sub(r"\[SQL:.*\]", "", error_msg, flags=re.DOTALL)
    error_msg = re.sub(r"\[parameters:.*\]", "", error_msg, flags=re.DOTALL)
    error_msg = re.sub(r"\(Background on this error at: https://sqlalche\.me/e/\S+\)", "", error_msg, flags=re.DOTALL)
    return error_msg.strip()


def qualified_table(schema: str | None, table: str) -> str:
    """Quote a ``(schema, table)`` pair as ``"schema"."table"`` for raw-text SQL.

    Correct for DuckDB / Postgres / SQLite / Snowflake; MySQL would need backticks.
    For dialect-aware rendering of structured statements, build a SQLAlchemy
    expression via :func:`sa_table` instead.
    """

    def q(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    return f"{q(schema)}.{q(table)}" if schema else q(table)


def sa_table(schema: str | None, table: str, *columns: str) -> sqlalchemy.TableClause:
    """Build a SQLAlchemy ``TableClause`` from explicit ``(schema, table)`` parts.

    Passing the schema separately lets SQLAlchemy emit dialect-correct quoting via
    its ``schema`` argument, with no parsing of qualified-string inputs.
    """
    sa_cols: list[sqlalchemy.ColumnClause[Any]] = [sqlalchemy.column(c) for c in columns]
    if schema is None:
        return sqlalchemy.table(table, *sa_cols)
    return sqlalchemy.table(table, *sa_cols, schema=schema)
