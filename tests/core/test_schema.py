from __future__ import annotations

import pandas as pd
import pytest
from pydantic import TypeAdapter

from tabulaflow.core import (
    ColumnRef,
    ForeignKeySchema,
    GraphPropertySchema,
    PropertyGraphSchema,
    SourceSchema,
    SQLColumnSchema,
    SQLSchema,
    SQLTableSchema,
)


def test_source_schema_uses_kind_discriminator() -> None:
    adapter: TypeAdapter[SourceSchema] = TypeAdapter(SourceSchema)

    sql_schema = adapter.validate_python({"kind": "sql", "name": "db", "dialect": "sqlite", "tables": []})
    graph_schema = adapter.validate_python({"kind": "property_graph", "name": "graph"})

    assert isinstance(sql_schema, SQLSchema)
    assert isinstance(graph_schema, PropertyGraphSchema)


def test_foreign_key_requires_matching_column_counts() -> None:
    with pytest.raises(ValueError, match="same length"):
        ForeignKeySchema(
            columns=["a", "b"],
            foreign_table="target",
            foreign_columns=["id"],
        )


def test_graph_property_requires_at_least_one_type() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        GraphPropertySchema(name="id", types=[])


def _table(name: str = "orders") -> SQLTableSchema:
    foreign_key = ForeignKeySchema(
        columns=["customer_id"],
        foreign_schema_name="public",
        foreign_table="customers",
        foreign_columns=["id"],
    )
    return SQLTableSchema(
        name=name,
        schema_name="public",
        is_view=False,
        columns=[
            SQLColumnSchema(
                name="id",
                dtype="INTEGER",
                nullable=False,
                examples=[],
            ),
            SQLColumnSchema(
                name="customer_id",
                dtype="INTEGER",
                nullable=False,
                examples=[],
            ),
            SQLColumnSchema(name="total", dtype="DECIMAL", nullable=False, examples=[]),
        ],
        primary_key=["id"],
        foreign_keys=[foreign_key],
        sampled_df=pd.DataFrame({"id": [1], "customer_id": [2], "total": [10]}),
    )


def test_table_select_columns_copies_and_updates_metadata() -> None:
    table = _table()

    selected = table.select_columns(["total"])

    assert [column.name for column in selected.columns] == ["id", "total"]
    assert selected.primary_key == ["id"]
    assert selected.foreign_keys == []
    assert selected.sampled_df is not None
    assert list(selected.sampled_df.columns) == ["id", "total"]
    assert selected.columns[0] is not table.columns[0]


def test_table_select_columns_can_return_an_empty_table() -> None:
    selected = _table().select_columns(["missing"], include_primary_key=False)

    assert selected.columns == []
    assert selected.primary_key == []
    assert selected.foreign_keys == []
    assert selected.sampled_df is not None
    assert selected.sampled_df.empty
    assert list(selected.sampled_df.columns) == []


def test_schema_select_columns_drops_unselected_tables() -> None:
    schema = SQLSchema(name="shop", dialect="postgresql", tables=[_table(), _table("archived_orders")])

    selected = schema.select_columns(
        [ColumnRef(schema_name="PUBLIC", table_name="ORDERS", column_name="CUSTOMER_ID")],
        include_primary_keys=False,
    )

    assert [table.name for table in selected.tables] == ["orders"]
    assert [column.name for column in selected.tables[0].columns] == ["customer_id"]
    assert selected.tables[0].primary_key == []
    assert len(selected.tables[0].foreign_keys) == 1
