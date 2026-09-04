from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pandas as pd
import pytest
from sqlalchemy.exc import IntegrityError

from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector


async def _connector(tmp_path: Path) -> SQLConnector:
    return await SQLConnector.from_url_async(
        global_id="test_write_dataframe",
        url=f"duckdb:///{tmp_path / 'workspace.duckdb'}",
        db_name="workspace",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
    )


async def test_duckdb_native_write_preserves_logical_types(tmp_path: Path) -> None:
    connector = await _connector(tmp_path)
    identifier = UUID("12345678-1234-5678-1234-567812345678")
    timestamp = pd.Timestamp("2025-01-02 03:04:05.123456789")
    df = pd.DataFrame(
        {
            "payload": [b"\x00\xffmedia"],
            "amount": [Decimal("123.450")],
            "day": [date(2025, 1, 2)],
            "identifier": [identifier],
            "items": [[1, 2]],
            "metadata": [{"name": "sample", "score": 7}],
            "timestamp": [timestamp],
        }
    )
    df["nullable_integer"] = pd.Series([1], dtype="Int64")
    df["nullable_boolean"] = pd.Series([True], dtype="boolean")

    assert await connector.write_dataframe_async(df, "typed_data") == 1

    schema = await connector.run_query_async("DESCRIBE typed_data")
    assert schema.error is None and schema.df is not None
    types = dict(zip(schema.df["column_name"], schema.df["column_type"]))
    assert types == {
        "payload": "BLOB",
        "amount": "DECIMAL(6,3)",
        "day": "DATE",
        "identifier": "UUID",
        "items": "BIGINT[]",
        "metadata": 'STRUCT("name" VARCHAR, score BIGINT)',
        "timestamp": "TIMESTAMP_NS",
        "nullable_integer": "BIGINT",
        "nullable_boolean": "BOOLEAN",
    }

    result = await connector.run_query_async(
        "SELECT payload, amount, day, identifier, items, metadata, epoch_ns(timestamp) AS timestamp_ns FROM typed_data"
    )
    assert result.error is None and result.df is not None
    row = result.df.iloc[0]
    assert row["payload"] == b"\x00\xffmedia"
    assert row["amount"] == Decimal("123.450")
    assert row["day"] == date(2025, 1, 2)
    assert row["identifier"] == identifier
    assert row["items"] == [1, 2]
    assert row["metadata"] == {"name": "sample", "score": 7}
    assert row["timestamp_ns"] == timestamp.value


async def test_dataframe_write_modes_are_distinct(tmp_path: Path) -> None:
    connector = await _connector(tmp_path)

    await connector.write_dataframe_async(pd.DataFrame({"id": [1], "label": ["first"]}), "items")
    with pytest.raises(ValueError, match="already exists"):
        await connector.write_dataframe_async(pd.DataFrame({"id": [2]}), "items", mode="create")
    with pytest.raises(ValueError, match="missing table"):
        await connector.write_dataframe_async(pd.DataFrame({"id": [1]}), "missing", mode="append")

    await connector.write_dataframe_async(
        pd.DataFrame({"label": ["second"], "id": [2]}),
        "items",
        mode="append",
    )
    appended = await connector.run_query_async("SELECT * FROM items ORDER BY id")
    assert appended.error is None and appended.df is not None
    assert appended.df.to_dict(orient="records") == [
        {"id": 1, "label": "first"},
        {"id": 2, "label": "second"},
    ]

    await connector.write_dataframe_async(pd.DataFrame({"replacement": [True]}), "items", mode="replace")
    replaced = await connector.run_query_async("SELECT * FROM items")
    assert replaced.error is None and replaced.df is not None
    assert replaced.df.to_dict(orient="records") == [{"replacement": True}]


async def test_duckdb_overwrite_preserves_table_definition_and_rolls_back(tmp_path: Path) -> None:
    connector = await _connector(tmp_path)
    created = await connector.run_query_async(
        """
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            label VARCHAR NOT NULL DEFAULT 'default label'
        );
        CREATE INDEX items_label_idx ON items(label);
        INSERT INTO items VALUES (1, 'first');
        """
    )
    assert created.error is None

    await connector.write_dataframe_async(
        pd.DataFrame({"id": [2]}),
        "items",
        mode="overwrite",
    )

    schema = await connector.run_query_async("DESCRIBE items")
    assert schema.error is None and schema.df is not None
    assert schema.df[["column_name", "column_type", "null", "key", "default"]].to_dict(orient="records") == [
        {"column_name": "id", "column_type": "INTEGER", "null": "NO", "key": "PRI", "default": None},
        {
            "column_name": "label",
            "column_type": "VARCHAR",
            "null": "NO",
            "key": None,
            "default": "'default label'",
        },
    ]
    indexes = await connector.run_query_async(
        "SELECT index_name FROM duckdb_indexes() WHERE table_name = 'items' ORDER BY index_name"
    )
    assert indexes.error is None and indexes.df is not None
    assert indexes.df["index_name"].tolist() == ["items_label_idx"]

    with pytest.raises(IntegrityError):
        await connector.write_dataframe_async(pd.DataFrame({"id": [3, 3]}), "items", mode="overwrite")

    rows = await connector.run_query_async("SELECT * FROM items")
    assert rows.error is None and rows.df is not None
    assert rows.df.to_dict(orient="records") == [{"id": 2, "label": "default label"}]


async def test_dataframe_write_rejects_unsupported_values(tmp_path: Path) -> None:
    connector = await _connector(tmp_path)

    with pytest.raises(ValueError, match="unsupported value type object"):
        await connector.write_dataframe_async(pd.DataFrame({"value": [object()]}), "invalid")
    with pytest.raises(ValueError, match="without coercion"):
        await connector.write_dataframe_async(pd.DataFrame({"value": [1, "one"]}), "heterogeneous")
    with pytest.raises(ValueError, match="all-NULL columns"):
        await connector.write_dataframe_async(pd.DataFrame({"value": [None]}), "untyped_null")


async def test_dataframe_write_modes_apply_to_pandas_fallback(tmp_path: Path) -> None:
    connector = await SQLConnector.from_url_async(
        global_id="test_write_dataframe_sqlite",
        url=f"sqlite+aiosqlite:///{tmp_path / 'fallback.sqlite'}",
        db_name="fallback",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
    )

    await connector.write_dataframe_async(pd.DataFrame({"value": [1]}), "items")
    with pytest.raises(ValueError, match="already exists"):
        await connector.write_dataframe_async(pd.DataFrame({"value": [2]}), "items")
    with pytest.raises(ValueError, match="missing table"):
        await connector.write_dataframe_async(pd.DataFrame({"value": [2]}), "missing", mode="append")
    with pytest.raises(ValueError, match="missing table"):
        await connector.write_dataframe_async(pd.DataFrame({"value": [2]}), "missing", mode="overwrite")

    created = await connector.run_query_async("CREATE TABLE preserved (value INTEGER PRIMARY KEY)")
    assert created.error is None
    inserted = await connector.run_query_async("INSERT INTO preserved VALUES (1)")
    assert inserted.error is None
    await connector.write_dataframe_async(pd.DataFrame({"value": [2]}), "preserved", mode="overwrite")
    schema = await connector.run_query_async("PRAGMA table_info(preserved)")
    assert schema.error is None and schema.df is not None
    assert schema.df[["name", "type", "notnull", "pk"]].to_dict(orient="records") == [
        {"name": "value", "type": "INTEGER", "notnull": 0, "pk": 1}
    ]
