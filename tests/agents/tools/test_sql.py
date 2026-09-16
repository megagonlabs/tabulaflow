from datetime import date, datetime

from tabulaflow.agents.tools._sql import _python_type_for_dtype, find_column, find_table
from tabulaflow.core import SQLColumnSchema, SQLSchema, SQLTableSchema


def _table(schema_name: str | None, name: str, *column_names: str) -> SQLTableSchema:
    return SQLTableSchema(
        name=name,
        schema_name=schema_name,
        is_view=False,
        columns=[
            SQLColumnSchema(name=column_name, dtype="VARCHAR", nullable=True, examples=[])
            for column_name in column_names
        ],
        primary_key=[],
        foreign_keys=[],
    )


def test_find_table_normalizes_case_and_quotes() -> None:
    table = _table("analytics", "Events", "Payload")
    schema = SQLSchema(display_name="warehouse", tables=[table])

    assert find_table(schema, '"wrong_schema"', "`events`") is table
    assert find_column(table, '"payload"') is table.columns[0]


def test_find_table_resolves_unique_unqualified_name_across_schemas() -> None:
    events = _table("analytics", "events", "payload")
    schema = SQLSchema(display_name="warehouse", tables=[events, _table("public", "users", "name")])

    assert find_table(schema, None, "events") is events


def test_find_table_does_not_guess_ambiguous_unqualified_name() -> None:
    schema = SQLSchema(
        display_name="warehouse",
        tables=[_table("analytics", "events", "payload"), _table("public", "events", "payload")],
    )

    assert find_table(schema, None, "events") is None
    assert find_table(schema, "public", "events") is schema.tables[1]


def test_find_column_does_not_guess_case_insensitive_collision() -> None:
    table = _table(None, "events", "value", "VALUE")

    assert find_column(table, "value") is None


def test_python_type_for_dtype() -> None:
    """Numeric/boolean/temporal canonical tokens map to native types; everything else to ``str``."""
    # Canonical SQLAlchemy visit-names the schema actually records (DuckDB workspace),
    # plus raw-SQL fallbacks. BIG_INTEGER/SMALL_INTEGER are what BIGINT/SMALLINT columns
    # introspect to — they must not fall through to str.
    for tok in ("TINY_INTEGER", "SMALL_INTEGER", "INTEGER", "BIG_INTEGER", "TINYINT", "SMALLINT", "INT", "BIGINT"):
        assert _python_type_for_dtype(tok) is int, tok
    for tok in ("FLOAT", "DOUBLE", "NUMERIC", "DECIMAL", "REAL", "DOUBLE_PRECISION"):
        assert _python_type_for_dtype(tok) is float, tok
    assert _python_type_for_dtype("BOOLEAN") is bool
    assert _python_type_for_dtype("DATE") is date
    # All TIMESTAMP variants (and DATETIME) flatten to a naive datetime.
    for tok in ("DATETIME", "TIMESTAMP", "TIMESTAMPTZ", "TIMESTAMP_NTZ", "TIMESTAMP_LTZ"):
        assert _python_type_for_dtype(tok) is datetime
    # Text, TIME, and semi-structured types all fall through to str.
    for tok in ("VARCHAR", "TEXT", "TIME", "JSON", "ARRAY", "STRUCT", "UUID", "BINARY"):
        assert _python_type_for_dtype(tok) is str
