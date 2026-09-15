"""In-memory DuckDB connection lifetime, isolation, and concurrency."""

import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
from threading import Barrier
from typing import Any
from uuid import uuid4

import duckdb
import pandas as pd
import pytest
from sqlalchemy import Connection
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool, QueuePool, SingletonThreadPool, StaticPool

from tabulaflow.data import SQLConnector
from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import ThrottledEngine


@pytest.mark.parametrize("database", [None, "", ":memory:"])
async def test_memory_database_roundtrip_and_isolation(database: str | None, tmp_path: Path) -> None:
    config = SQLConnectorConfig(
        cache_dir=tmp_path,
        schema_cache_mode="read_write",
        sql_query_cache_mode="off",
        max_query_concurrency=3,
    )
    async with AsyncExitStack() as cleanup:
        connectors = []
        for value in (1, 2):
            connector = await SQLConnector.from_url_async(
                make_url("duckdb://" if database is None else f"duckdb:///{database}"),
                read_only=False,
                config=config,
            )
            cleanup.push_async_callback(connector.close_async)
            assert connector.schema.display_name == (database or "duckdb")
            assert connector.schema.tables == []
            assert await connector.write_dataframe_async(pd.DataFrame({"value": [value]}), "items") == 1
            assert connector.schema.tables[0].name == "items"
            connectors.append(connector)

        assert connectors[0].global_id != connectors[1].global_id
        assert len(list((tmp_path / "schemas").glob("*.json"))) == 2
        for value, connector in enumerate(connectors, start=1):
            barrier = Barrier(3)

            def read_on_worker(conn: Connection) -> Any:
                barrier.wait(timeout=10)
                return conn.exec_driver_sql("SELECT value FROM items").scalar_one()

            results = await asyncio.gather(*(connector._t_eng.run_with_conn_async(read_on_worker) for _ in range(3)))
            assert results == [value] * 3
            with pytest.raises(ValueError, match="destroying the database"):
                await connector.release_connections_async()
            result = await connector.run_query_async("SELECT value FROM items")
            assert result.error is None and result.df is not None
            assert result.df["value"].tolist() == [value]

        name = connectors[0]._t_eng.engine.url.database
        assert name is not None
        await connectors[0].close_async()
        await connectors[0].close_async()
        with pytest.raises(RuntimeError, match="closed"):
            await connectors[0].run_query_async("SELECT 1")
        with duckdb.connect(name) as reopened:
            assert reopened.execute("SELECT table_name FROM information_schema.tables").fetchall() == []


@pytest.mark.parametrize("url", ["duckdb://", "duckdb:///", "duckdb:///:memory:"])
async def test_memory_database_preserves_explicit_identity_and_read_only(url: str) -> None:
    connector = await SQLConnector.from_url_async(
        url,
        display_name="example",
        global_id="explicit-memory",
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    try:
        assert connector.global_id == "explicit-memory"
        assert connector.schema.display_name == "example"
        result = await connector.run_query_async("CREATE TABLE items (value INTEGER)")
        assert result.error is not None and result.error.exc_type == "ReadOnlyViolationError"
        with pytest.raises(ValueError, match="read_only"):
            await connector.write_dataframe_async(pd.DataFrame({"value": [1]}), "items")
    finally:
        await connector.close_async()


async def test_named_memory_database_can_be_shared_explicitly() -> None:
    url = f"duckdb:///:memory:{uuid4().hex}"
    config = SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off")
    async with AsyncExitStack() as cleanup:
        writer = await SQLConnector.from_url_async(url, read_only=False, config=config)
        cleanup.push_async_callback(writer.close_async)
        await writer.write_dataframe_async(pd.DataFrame({"value": [42]}), "items")
        reader = await SQLConnector.from_url_async(url, config=config)
        cleanup.push_async_callback(reader.close_async)
        assert reader._t_eng.engine.url == make_url(url)
        assert reader.schema.tables[0].name == "items"
        await writer.close_async()
        result = await reader.run_query_async("SELECT value FROM items")
        assert result.error is None and result.df is not None
        assert result.df["value"].tolist() == [42]
        with pytest.raises(ValueError, match="destroying the database"):
            await reader.release_connections_async()


@pytest.mark.parametrize("pool_class", [NullPool, StaticPool, SingletonThreadPool])
def test_memory_database_rejects_unsafe_pools(pool_class: Any) -> None:
    with pytest.raises(ValueError, match="requires QueuePool"):
        ThrottledEngine.from_url("duckdb:///:memory:", poolclass=pool_class)


def test_memory_database_rejects_connection_recycling() -> None:
    with pytest.raises(ValueError, match="cannot recycle connections"):
        ThrottledEngine.from_url("duckdb:///:memory:", pool_recycle=0)


async def test_file_database_preserves_pool_read_only_and_search_path(tmp_path: Path) -> None:
    directory = tmp_path / "user's data"
    directory.mkdir()
    path = directory / "items.duckdb"
    duckdb.connect(str(path)).close()
    pd.DataFrame({"value": [42]}).to_csv(directory / "items.csv", index=False)
    engine = ThrottledEngine.from_url(f"duckdb:///{path}", read_only=True, max_concurrency_per_db=3)
    try:
        assert isinstance(engine.engine.pool, QueuePool)
        assert engine.engine.pool.size() == 3
        result = await engine.execute_async("SELECT current_setting('access_mode')")
        assert result.rows == [("read_only",)]
        result = await engine.execute_async("SELECT value FROM read_csv_auto('items.csv')")
        assert result.rows == [(42,)]
    finally:
        await engine.aclose()
