from tabulaflow.agents.tools.engines.sql import find_column, find_table
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
    schema = SQLSchema(name="warehouse", tables=[table])

    assert find_table(schema, '"wrong_schema"', "`events`") is table
    assert find_column(table, '"payload"') is table.columns[0]


def test_find_table_resolves_unique_unqualified_name_across_schemas() -> None:
    events = _table("analytics", "events", "payload")
    schema = SQLSchema(name="warehouse", tables=[events, _table("public", "users", "name")])

    assert find_table(schema, None, "events") is events


def test_find_table_does_not_guess_ambiguous_unqualified_name() -> None:
    schema = SQLSchema(
        name="warehouse",
        tables=[_table("analytics", "events", "payload"), _table("public", "events", "payload")],
    )

    assert find_table(schema, None, "events") is None
    assert find_table(schema, "public", "events") is schema.tables[1]


def test_find_column_does_not_guess_case_insensitive_collision() -> None:
    table = _table(None, "events", "value", "VALUE")

    assert find_column(table, "value") is None
