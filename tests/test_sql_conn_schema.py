"""Tests for schema introspection in :class:`SQLConnector`.

Covers the dialect-gap fallback that kicks in when SQLAlchemy's inspector
returns ``NullType`` for a column (e.g. duckdb_engine on ``LIST`` /
``STRUCT`` / ``MAP`` — Mause/duckdb_engine#654).
"""

from pathlib import Path

import duckdb
import pytest

from mintq.db_connector.sql_conn import SQLConnector, _normalize_duckdb_native_dtype


def test_normalize_duckdb_native_dtype_scalars() -> None:
    assert _normalize_duckdb_native_dtype("VARCHAR") == "VARCHAR"
    assert _normalize_duckdb_native_dtype("BIGINT") == "BIGINT"
    assert _normalize_duckdb_native_dtype("DECIMAL(18,2)") == "DECIMAL"


def test_normalize_duckdb_native_dtype_composites() -> None:
    assert _normalize_duckdb_native_dtype("JSON[]") == "ARRAY"
    assert _normalize_duckdb_native_dtype("VARCHAR[]") == "ARRAY"
    assert _normalize_duckdb_native_dtype("STRUCT(id VARCHAR, n BIGINT)") == "STRUCT"
    assert _normalize_duckdb_native_dtype("STRUCT(id VARCHAR)[]") == "ARRAY"
    assert _normalize_duckdb_native_dtype("MAP(VARCHAR, BIGINT)") == "MAP"


@pytest.mark.asyncio
async def test_duckdb_list_and_struct_dtype_resolved(tmp_path: Path) -> None:
    """duckdb_engine returns NullType for LIST/STRUCT columns; the
    information_schema fallback should recover a usable dtype and let
    JSON schema inference run.
    """
    db_path = str(tmp_path / "composite.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute(
        """
        CREATE TABLE t AS
        SELECT
            'a' AS name,
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
        enable_schema_caching=False,
    )
    try:
        table = sql_conn.schema.tables[0]
        cols = {c.name: c for c in table.columns}

        assert cols["name"].dtype in ("VARCHAR", "STRING")
        assert cols["int_list"].dtype == "ARRAY"
        assert cols["struct_list"].dtype == "ARRAY"
        assert cols["info"].dtype == "STRUCT"

        # JSON schema inference should run for ARRAY / STRUCT columns.
        assert cols["int_list"].json_schema is not None
        assert cols["int_list"].json_schema["type"] == "array"
        assert cols["struct_list"].json_schema is not None
        assert cols["info"].json_schema is not None
        assert cols["info"].json_schema["type"] == "object"
    finally:
        await sql_conn.disconnect_async()
