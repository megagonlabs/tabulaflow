import re
from typing import Any

import sqlalchemy


def equals_ci(a: str | None, b: str | None) -> bool:
    """
    Compare two strings case-insensitively, treating None == None.
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a.lower() == b.lower()


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
