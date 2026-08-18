import pytest

from tabulaflow.core import SQLColumnSchema, SQLSchema, SQLTableSchema
from tabulaflow.output.schema_compression import SchemaCompressor


def _table(name: str, *, null_ratio: float, examples: list[str]) -> SQLTableSchema:
    return SQLTableSchema(
        name=name,
        is_view=False,
        columns=[
            SQLColumnSchema(
                name="event",
                dtype="VARCHAR",
                nullable=True,
                null_ratio=null_ratio,
                num_unique=len(examples),
                unique_ratio=0.5,
                examples=examples,
            )
        ],
        primary_key=[],
        foreign_keys=[],
    )


def test_compress_groups_structurally_identical_partitioned_tables() -> None:
    schema = SQLSchema(
        name="analytics",
        dialect="duckdb",
        tables=[
            _table("events_20240101", null_ratio=0.2, examples=["open"]),
            _table("events_20240102", null_ratio=0.4, examples=["closed"]),
        ],
    )

    compressed = SchemaCompressor().compress(schema)

    assert len(compressed.tables) == 1
    table = compressed.tables[0]
    assert len(table.name_patterns) == 1
    assert table.name_patterns[0].pattern == "events_{YYYYMMDD}"
    assert table.name_patterns[0].original_names == ["events_20240101", "events_20240102"]
    assert table.columns[0].null_ratio == pytest.approx(0.3)
    assert table.columns[0].examples == ["open", "closed"]


def test_compress_does_not_mutate_source_schema() -> None:
    schema = SQLSchema(
        name="analytics",
        dialect="duckdb",
        tables=[
            _table("events_2024", null_ratio=0.0, examples=["open"]),
            _table("events_2025", null_ratio=0.0, examples=["closed"]),
        ],
    )

    SchemaCompressor().compress(schema)

    assert [table.name for table in schema.tables] == ["events_2024", "events_2025"]
    assert all(not table.name_patterns for table in schema.tables)
