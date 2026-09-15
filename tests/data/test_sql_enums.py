"""Declared enum choices survive SQL reflection and schema caching."""

import sqlite3
from pathlib import Path
from unittest.mock import Mock

import duckdb
import pytest
import sqlalchemy
from sqlalchemy.dialects import mysql, postgresql

from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector, ThrottledEngine, _native_enum_values_async


@pytest.mark.parametrize("dtype", [sqlalchemy.Enum, postgresql.ENUM, mysql.ENUM])
async def test_native_enum_reflection(dtype: type[sqlalchemy.Enum]) -> None:
    engine = Mock(spec=ThrottledEngine)
    values = ["billing", "customer's account", "technical, other"]
    assert await _native_enum_values_async(engine, {"type": dtype(*values)}, "tickets", None) == values
    engine.execute_async.assert_not_called()


@pytest.mark.parametrize("populated", [False, True])
async def test_duckdb_native_enum_labels_are_independent_of_rows_and_cached(tmp_path: Path, populated: bool) -> None:
    path = tmp_path / "enums.duckdb"
    raw = duckdb.connect(str(path))
    raw.execute("CREATE SCHEMA other")
    raw.execute("CREATE TYPE category AS ENUM ('main value')")
    raw.execute("CREATE TYPE other.category AS ENUM ('other value', 'customer''s account')")
    raw.execute("CREATE TABLE other.tickets (\"named category\" other.category, inline ENUM ('yes', 'no'))")
    if populated:
        raw.execute("INSERT INTO other.tickets DEFAULT VALUES")
    raw.close()

    connector = await SQLConnector.from_url_async(
        f"duckdb:///{path}", config=SQLConnectorConfig(schema_cache_mode="read_write", cache_dir=tmp_path / "cache")
    )
    try:
        columns = {column.name: column for column in connector.schema.tables[0].columns}
        assert columns["named category"].enum_values == ["other value", "customer's account"]
        assert columns["inline"].enum_values == ["yes", "no"]
        assert all(column.examples == [] for column in columns.values())
    finally:
        await connector.close_async()

    cached = await SQLConnector.from_url_async(
        f"duckdb:///{path}",
        config=SQLConnectorConfig(schema_cache_mode="cache_only", cache_dir=tmp_path / "cache"),
    )
    try:
        assert [column.enum_values for column in cached.schema.tables[0].columns] == [
            ["other value", "customer's account"],
            ["yes", "no"],
        ]
    finally:
        await cached.close_async()


async def test_check_constraints_are_not_inferred_as_enums(tmp_path: Path) -> None:
    path = tmp_path / "checks.sqlite"
    with sqlite3.connect(path) as raw:
        raw.execute("""
            CREATE TABLE tickets (
                category TEXT CHECK (category IN ('billing', 'account')),
                priority INTEGER CHECK (priority IN (1, 2, 3))
            )
        """)
    connector = await SQLConnector.from_url_async(
        f"sqlite+aiosqlite:///{path}", config=SQLConnectorConfig(schema_cache_mode="off")
    )
    try:
        assert all(column.enum_values is None for column in connector.schema.tables[0].columns)
    finally:
        await connector.close_async()
