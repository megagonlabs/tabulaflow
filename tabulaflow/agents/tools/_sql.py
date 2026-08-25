"""Shared SQL lookup, quoting, and error-formatting helpers for agent tools."""

import re
from typing import Any

import sqlalchemy

from tabulaflow.core.schema import SQLColumnSchema, SQLSchema, SQLTableSchema


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


def format_sqlalchemy_error_msg(error_msg: str) -> str:
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
