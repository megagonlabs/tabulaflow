import pandas as pd

from tabulaflow.core import ForeignKeySchema, SQLColumnSchema, SQLSchema, SQLTableSchema
from tabulaflow.output.formatting import SQLBasicSchemaFormatter, SQLDDLSchemaFormatter
from tabulaflow.output.formatting._table_grouping import group_tables_for_formatting


def _column(
    name: str = "event",
    *,
    native_dtype: str | None = "VARCHAR(100)",
    nullable: bool = True,
    example: str = "open",
) -> SQLColumnSchema:
    return SQLColumnSchema(
        name=name,
        dtype="VARCHAR",
        native_dtype=native_dtype,
        nullable=nullable,
        null_ratio=0.25,
        num_unique=2,
        unique_ratio=0.1,
        examples=[example],
    )


def _table(
    name: str,
    *,
    columns: list[SQLColumnSchema] | None = None,
    is_view: bool = False,
    num_rows: int | None = 10,
    foreign_keys: list[ForeignKeySchema] | None = None,
) -> SQLTableSchema:
    return SQLTableSchema(
        name=name,
        schema_name="analytics",
        is_view=is_view,
        columns=columns or [_column()],
        primary_key=[],
        num_rows=num_rows,
        foreign_keys=foreign_keys or [],
        sampled_df=pd.DataFrame({"event": ["open"]}),
    )


def _schema(*tables: SQLTableSchema) -> SQLSchema:
    return SQLSchema(display_name="warehouse", dialect="duckdb", tables=list(tables))


def test_dense_date_family_is_grouped_without_mutating_schema() -> None:
    schema = _schema(_table("events_20240101"), _table("events_20240102"))

    groups = group_tables_for_formatting(schema)

    assert len(groups) == 1
    assert groups[0].display_name == "events_{YYYYMMDD}"
    assert groups[0].member_summary == "Partitions: YYYYMMDD from 20240101 to 20240102 (2 total)"
    assert [table.name for table in schema.tables] == ["events_20240101", "events_20240102"]


def test_sparse_family_summary_is_bounded_and_truthful() -> None:
    names = ["events_20240101", "events_20240201", "events_20240301"]
    group = group_tables_for_formatting(_schema(*(_table(name) for name in names)))[0]

    assert group.member_summary == "Available YYYYMMDD values: 20240101, 20240201, 20240301"


def test_name_pattern_and_structure_both_participate_in_grouping() -> None:
    schema = _schema(
        _table("revenue_20240101"),
        _table("revenue_20240102"),
        _table("profit_20240101"),
        _table("profit_20240102"),
        _table("customers", columns=[_column("id")]),
        _table("products", columns=[_column("id")]),
    )

    groups = group_tables_for_formatting(schema)

    assert [group.display_name for group in groups] == [
        "revenue_{YYYYMMDD}",
        "profit_{YYYYMMDD}",
        "customers",
        "products",
    ]


def test_table_kind_native_type_and_nullability_must_match() -> None:
    schema = _schema(
        _table("kind_2024"),
        _table("kind_2025", is_view=True),
        _table("native_2024", columns=[_column(native_dtype="TEXT")]),
        _table("native_2025", columns=[_column(native_dtype="VARCHAR(100)")]),
        _table("nullable_2024", columns=[_column(nullable=True)]),
        _table("nullable_2025", columns=[_column(nullable=False)]),
    )

    assert all(not group.is_family for group in group_tables_for_formatting(schema))


def test_identical_outgoing_foreign_keys_group_but_incoming_references_prevent_grouping() -> None:
    foreign_key = ForeignKeySchema(columns=["event"], foreign_table="types", foreign_columns=["name"])
    grouped = _schema(
        _table("events_2024", foreign_keys=[foreign_key]),
        _table("events_2025", foreign_keys=[foreign_key]),
    )
    assert len(group_tables_for_formatting(grouped)) == 1

    incoming = _table(
        "audit",
        foreign_keys=[
            ForeignKeySchema(
                columns=["event"],
                foreign_schema_name="analytics",
                foreign_table="events_2024",
                foreign_columns=["event"],
            )
        ],
    )
    not_grouped = _schema(_table("events_2024"), _table("events_2025"), incoming)
    assert [group.display_name for group in group_tables_for_formatting(not_grouped)][:2] == [
        "events_2024",
        "events_2025",
    ]


def test_formatter_uses_concrete_representative_and_labels_its_profile() -> None:
    schema = _schema(
        _table("events_20240101", columns=[_column(example="first")]),
        _table("events_20240102", columns=[_column(example="second")]),
    )

    formatted = SQLDDLSchemaFormatter(compact_table_families=True).format(schema)

    assert 'Table family: "events_{YYYYMMDD}"' in formatted
    assert "Representative table: events_20240101" in formatted
    assert (
        "The schema, row count, descriptions, column profiles, and samples below come from this physical table."
        in formatted
    )
    assert "CREATE TABLE analytics.events_20240101" in formatted
    assert "CREATE TABLE analytics.events_{YYYYMMDD}" not in formatted
    assert "'first'" in formatted
    assert "'second'" not in formatted
    assert "Sample rows:" in formatted


def test_disabling_compaction_renders_every_physical_table() -> None:
    schema = _schema(_table("events_1"), _table("events_2"))

    formatted = SQLBasicSchemaFormatter(compact_table_families=False).format(schema)

    assert "TABLE: events_1" in formatted
    assert "TABLE: events_2" in formatted
    assert "TABLE FAMILY" not in formatted


def test_pattern_replaces_only_the_recognized_span() -> None:
    schema = _schema(_table("tenant_12_events_202401"), _table("tenant_12_events_202402"))

    group = group_tables_for_formatting(schema)[0]

    assert group.display_name == "tenant_12_events_{YYYYMM}"


def test_month_sparsity_uses_month_count() -> None:
    schema = _schema(_table("events_202401"), _table("events_202403"))

    group = group_tables_for_formatting(schema)[0]

    assert group.member_summary == "Partitions: YYYYMM from 202401 to 202403, except 202402"


def test_generic_numeric_family_is_supported() -> None:
    schema = _schema(_table("events_1"), _table("events_2"), _table("events_4"))

    group = group_tables_for_formatting(schema)[0]

    assert group.display_name == "events_{NUM}"
    assert group.member_summary == "Members: NUM from 1 to 4, except 3"


def test_numeric_tokens_with_different_widths_group_with_exact_values() -> None:
    schema = _schema(_table("events_1"), _table("events_01"))

    group = group_tables_for_formatting(schema)[0]

    assert group.is_family
    assert group.display_name == "events_{NUM}"
    assert group.member_summary == "Available NUM values: 1, 01"


def test_large_mixed_width_numeric_summary_is_bounded() -> None:
    names = ["events_1", *(f"events_{value:02d}" for value in range(2, 22))]

    group = group_tables_for_formatting(_schema(*(_table(name) for name in names)))[0]

    assert group.member_summary == (
        "Members: 21 mixed-width NUM values; examples: 1, 02, 03, 04, 05, 17, 18, 19, 20, 21"
    )


def test_column_budget_is_applied_after_compaction() -> None:
    columns = [_column("a"), _column("b"), _column("c")]
    schema = _schema(
        _table("events_1", columns=columns),
        _table("events_2", columns=columns),
        _table("customers", columns=columns),
    )

    formatted = SQLBasicSchemaFormatter(compact_table_families=True, max_total_columns=4).format(schema)

    assert formatted.count("1 more columns omitted") == 2


def test_format_table_always_renders_one_physical_table() -> None:
    table = _table("events_1")

    formatted = SQLDDLSchemaFormatter(compact_table_families=True).format_table(table, dialect="duckdb")

    assert "Table family" not in formatted
    assert "CREATE TABLE analytics.events_1" in formatted
