"""Tests for schema introspection in :class:`SQLConnector`.

Covers the dialect-gap fallback that kicks in when SQLAlchemy's inspector
returns ``NullType`` for a column (e.g. duckdb_engine on ``LIST`` /
``STRUCT`` / ``MAP`` — Mause/duckdb_engine#654).
"""

from pathlib import Path

import duckdb
import pytest

from tabulaflow.db_connector.sql_conn import SQLConnector, _canonicalize_dtype


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
    # BigQuery-style angle bracket notation
    assert _canonicalize_dtype("ARRAY<STRING>") == "ARRAY"
    assert _canonicalize_dtype("STRUCT<a INT64, b STRING>") == "STRUCT"


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
        enable_schema_caching=False,
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
