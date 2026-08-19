"""Tests for schema introspection in :class:`SQLConnector`.

Covers the dialect-gap fallback that kicks in when SQLAlchemy's inspector
returns ``NullType`` for a column (e.g. duckdb_engine on ``LIST`` /
``STRUCT`` / ``MAP`` — Mause/duckdb_engine#654).
"""

from pathlib import Path
import sqlite3
from typing import Any

import duckdb
import pytest

from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector, ThrottledEngine, _canonicalize_dtype
from tabulaflow.core import SQLSchema, TableRef


def test_canonicalize_dtype_scalars() -> None:
    assert _canonicalize_dtype("VARCHAR") == "VARCHAR"
    assert _canonicalize_dtype("BIGINT") == "BIGINT"
    assert _canonicalize_dtype("DECIMAL(18,2)") == "DECIMAL"
    assert _canonicalize_dtype("VARCHAR(100)") == "VARCHAR"


def test_canonicalize_dtype_composites() -> None:
    assert _canonicalize_dtype("JSON[]") == "ARRAY"
    assert _canonicalize_dtype("VARCHAR[]") == "ARRAY"
    assert _canonicalize_dtype("STRUCT(id VARCHAR, n BIGINT)") == "STRUCT"
    assert _canonicalize_dtype("STRUCT(id VARCHAR)[]") == "ARRAY"
    assert _canonicalize_dtype("MAP(VARCHAR, BIGINT)") == "MAP"


async def test_preloaded_connector_schema_requires_dialect(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must declare its dialect"):
        await SQLConnector.from_url_async(
            global_id="missing-dialect",
            url=f"sqlite+aiosqlite:///{tmp_path / 'missing-dialect.sqlite'}",
            db_name="missing-dialect",
            schema=SQLSchema(name="missing-dialect", tables=[]),
            config=SQLConnectorConfig(schema_cache_mode="off"),
        )


async def test_connector_rejects_unsafe_global_id_before_opening_database(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="global_id must be"):
        await SQLConnector.from_url_async(
            global_id="../unsafe",
            url=f"sqlite+aiosqlite:///{tmp_path / 'unsafe.sqlite'}",
            db_name="unsafe",
        )

    assert not (tmp_path / "unsafe.sqlite").exists()
    # BigQuery-style angle bracket notation
    assert _canonicalize_dtype("ARRAY<STRING>") == "ARRAY"
    assert _canonicalize_dtype("STRUCT<a INT64, b STRING>") == "STRUCT"


async def test_table_without_column_stats_uses_one_bounded_sample(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "table-sample.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE items (value INTEGER)")
        connection.executemany("INSERT INTO items VALUES (?)", [(1,), (2,), (2,)])

    original_execute = ThrottledEngine.execute_async
    table_queries: list[tuple[str, int | None, bool]] = []

    async def execute(
        self: ThrottledEngine,
        query: Any,
        parameters: Any = (),
        timeout: int | None = None,
        return_df: bool = False,
        max_rows: int | None = None,
    ) -> Any:
        rendered = str(query)
        if "FROM items" in rendered:
            table_queries.append((rendered, timeout, return_df))
        return await original_execute(self, query, parameters, timeout, return_df, max_rows)

    monkeypatch.setattr(ThrottledEngine, "execute_async", execute)
    connector = await SQLConnector.from_url_async(
        global_id="table-sample",
        url=f"sqlite+aiosqlite:///{db_path}",
        db_name="table-sample",
        config=SQLConnectorConfig(schema_cache_mode="off", query_timeout_seconds=7),
    )
    try:
        table = connector.schema.tables[0]
        column = table.columns[0]
        assert table.num_rows is None
        assert column.null_ratio is None
        assert column.num_unique is None
        assert column.unique_ratio is None
        assert column.examples == [1, 2]
        assert table.sampled_df is not None
    finally:
        await connector.disconnect_async()

    assert len(table_queries) == 1
    assert "LIMIT" in table_queries[0][0]
    assert table_queries[0][1:] == (7, True)


async def test_view_profiling_uses_one_bounded_sample(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "view.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE items (value INTEGER)")
        connection.executemany("INSERT INTO items VALUES (?)", [(1,), (2,), (2,)])
        connection.execute("CREATE VIEW item_view AS SELECT value FROM items")

    original_execute = ThrottledEngine.execute_async
    view_queries: list[tuple[str, int | None, bool]] = []

    async def execute(
        self: ThrottledEngine,
        query: Any,
        parameters: Any = (),
        timeout: int | None = None,
        return_df: bool = False,
        max_rows: int | None = None,
    ) -> Any:
        rendered = str(query)
        if "FROM item_view" in rendered:
            view_queries.append((rendered, timeout, return_df))
        return await original_execute(self, query, parameters, timeout, return_df, max_rows)

    monkeypatch.setattr(ThrottledEngine, "execute_async", execute)
    connector = await SQLConnector.from_url_async(
        global_id="view-profile",
        url=f"sqlite+aiosqlite:///{db_path}",
        db_name="view-profile",
        config=SQLConnectorConfig(
            schema_cache_mode="off",
            collect_column_stats=True,
            query_timeout_seconds=7,
        ),
    )
    try:
        view = next(table for table in connector.schema.tables if table.name == "item_view")
        column = view.columns[0]
        assert view.num_rows is None
        assert column.null_ratio is None
        assert column.num_unique is None
        assert column.unique_ratio is None
        assert column.examples == [1, 2]
        assert view.sampled_df is not None
        assert view.sampled_df["value"].tolist() == [1, 2, 2]
    finally:
        await connector.disconnect_async()

    assert len(view_queries) == 1
    assert "LIMIT" in view_queries[0][0]
    assert view_queries[0][1:] == (7, True)


async def test_view_sample_timeout_preserves_structural_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    db_path = tmp_path / "view-timeout.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE items (value INTEGER)")
        connection.execute("CREATE VIEW item_view AS SELECT value FROM items")

    original_execute = ThrottledEngine.execute_async

    async def execute(
        self: ThrottledEngine,
        query: Any,
        parameters: Any = (),
        timeout: int | None = None,
        return_df: bool = False,
        max_rows: int | None = None,
    ) -> Any:
        if "FROM item_view" in str(query):
            raise TimeoutError("too expensive")
        return await original_execute(self, query, parameters, timeout, return_df, max_rows)

    monkeypatch.setattr(ThrottledEngine, "execute_async", execute)
    connector = await SQLConnector.from_url_async(
        global_id="view-timeout",
        url=f"sqlite+aiosqlite:///{db_path}",
        db_name="view-timeout",
        config=SQLConnectorConfig(schema_cache_mode="off", query_timeout_seconds=7),
    )
    try:
        view = next(table for table in connector.schema.tables if table.name == "item_view")
        assert view.num_rows is None
        assert view.sampled_df is None
        assert view.columns[0].examples == []
    finally:
        await connector.disconnect_async()

    assert "Could not sample relation" in caplog.text


@pytest.mark.asyncio
async def test_duckdb_list_and_struct_dtype_resolved(tmp_path: Path) -> None:
    """duckdb_engine returns NullType for LIST/STRUCT columns; the
    information_schema fallback should recover a usable dtype, populate
    ``native_dtype``, and let JSON schema inference run.
    """
    db_path = str(tmp_path / "composite.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute(
        """
        CREATE TABLE t AS
        SELECT
            'a' AS name,
            CAST(1 AS DECIMAL(18,2)) AS amount,
            [1, 2, 3] AS int_list,
            [{'k': 'x', 'v': 1}, {'k': 'y', 'v': 2}] AS struct_list,
            {'id': 'q1', 'score': 0.5} AS info
        """
    )
    conn.close()

    sql_conn = await SQLConnector.from_url_async(
        global_id="test+duckdb_composite",
        url=f"duckdb:///{db_path}",
        db_name="composite",
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
    )
    try:
        table = sql_conn.schema.tables[0]
        cols = {c.name: c for c in table.columns}

        # Canonical dtype: atomic tokens used for categorical type-class checks.
        assert cols["name"].dtype in ("VARCHAR", "STRING")
        assert cols["int_list"].dtype == "ARRAY"
        assert cols["struct_list"].dtype == "ARRAY"
        assert cols["info"].dtype == "STRUCT"

        # native_dtype: dialect-native string with parameters/shape preserved.
        # Scalars come via TypeEngine.compile (dialect-agnostic SQLAlchemy path).
        # NUMERIC and DECIMAL are SQL synonyms; SQLAlchemy may normalize either way.
        # What matters is that the precision/scale parameters survive.
        assert cols["amount"].native_dtype is not None
        assert "(18, 2)" in cols["amount"].native_dtype or "(18,2)" in cols["amount"].native_dtype
        # Composites come via the duckdb information_schema fallback.
        assert cols["int_list"].native_dtype is not None
        assert cols["int_list"].native_dtype.endswith("[]")
        assert cols["struct_list"].native_dtype is not None
        assert cols["struct_list"].native_dtype.upper().startswith("STRUCT")
        assert cols["info"].native_dtype is not None
        assert cols["info"].native_dtype.upper().startswith("STRUCT")

        # JSON schema inference should run for ARRAY / STRUCT columns.
        assert cols["int_list"].json_schema is not None
        assert cols["int_list"].json_schema["type"] == "array"
        assert cols["struct_list"].json_schema is not None
        assert cols["info"].json_schema is not None
        assert cols["info"].json_schema["type"] == "object"
    finally:
        await sql_conn.disconnect_async()


@pytest.mark.asyncio
async def test_exclude_schema_names_keeps_a_schema_out_of_introspection(tmp_path: Path) -> None:
    """An excluded schema stays out of the schema on both refresh paths."""
    db_path = str(tmp_path / "excluded.duckdb")
    con = duckdb.connect(db_path)
    con.execute("CREATE TABLE visible(a INTEGER)")
    con.execute("CREATE SCHEMA bookkeeping")
    con.execute("CREATE TABLE bookkeeping.hidden(a INTEGER)")
    con.close()

    connector = await SQLConnector.from_url_async(
        global_id="excluded-test",
        url=f"duckdb:///{db_path}",
        db_name="excluded",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
        exclude_schema_names=["bookkeeping"],
    )

    assert [t.name for t in connector.schema.tables] == ["visible"]

    # A targeted refresh of an excluded table is a no-op, not an addition.
    await connector.refresh_schema_async(tables=[TableRef(schema_name="bookkeeping", table_name="hidden")])
    assert [t.name for t in connector.schema.tables] == ["visible"]

    await connector.refresh_schema_async()
    assert [t.name for t in connector.schema.tables] == ["visible"]
