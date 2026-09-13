"""In-memory SQLite connection lifetime, isolation, and concurrency."""

import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

from tabulaflow.data import SQLConnector
from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import ThrottledEngine


@pytest.mark.parametrize("driver", ["sqlite", "sqlite+aiosqlite"])
@pytest.mark.parametrize("database", [None, "", ":memory:"])
async def test_memory_database_roundtrip_and_isolation(driver: str, database: str | None, tmp_path: Path) -> None:
    config = SQLConnectorConfig(
        cache_dir=tmp_path,
        schema_cache_mode="read_write",
        sql_query_cache_mode="off",
    )
    async with AsyncExitStack() as cleanup:
        connectors = []
        for value in (1, 2):
            connector = await SQLConnector.from_url_async(
                make_url(f"{driver}://" if database is None else f"{driver}:///{database}"),
                read_only=False,
                config=config,
            )
            cleanup.push_async_callback(connector.close_async)
            assert connector.schema.display_name == (database or "sqlite")
            assert connector.schema.tables == []
            assert isinstance(connector._t_eng.engine.pool, StaticPool)
            assert await connector.write_dataframe_async(pd.DataFrame({"value": [value]}), "items") == 1
            assert connector.schema.tables[0].name == "items"
            assert [column.name for column in connector.schema.tables[0].columns] == ["value"]
            connectors.append(connector)

        assert connectors[0].global_id != connectors[1].global_id
        for value, connector in enumerate(connectors, start=1):
            results = await asyncio.gather(*(connector.run_query_async("SELECT value FROM items") for _ in range(12)))
            for result in results:
                assert result.error is None
                assert result.df is not None
                assert result.df["value"].tolist() == [value]
            with pytest.raises(ValueError, match="destroying the database"):
                await connector.release_connections_async()
            result = await connector.run_query_async("SELECT value FROM items")
            assert result.error is None

        await connectors[0].close_async()
        await connectors[0].close_async()
        with pytest.raises(RuntimeError, match="closed"):
            await connectors[0].run_query_async("SELECT 1")


async def test_memory_database_serializes_transactions() -> None:
    engine = ThrottledEngine.from_url("sqlite+aiosqlite:///:memory:")
    active = 0
    peak = 0

    def checkout(*args: Any) -> None:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)

    def checkin(*args: Any) -> None:
        nonlocal active
        active -= 1

    event.listen(engine.engine.pool, "checkout", checkout)
    event.listen(engine.engine.pool, "checkin", checkin)
    try:
        await asyncio.gather(*(engine.execute_async("SELECT 1") for _ in range(12)))
        assert peak == 1
        assert active == 0
    finally:
        await engine.aclose()


async def test_memory_database_preserves_explicit_identity_and_read_only() -> None:
    connector = await SQLConnector.from_url_async(
        "sqlite+aiosqlite:///:memory:",
        display_name="example",
        global_id="explicit-memory",
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    try:
        assert connector.global_id == "explicit-memory"
        with pytest.raises(ValueError, match="read_only"):
            await connector.write_dataframe_async(pd.DataFrame({"value": [1]}), "items")
    finally:
        await connector.close_async()


def test_memory_database_rejects_discarding_connections() -> None:
    with pytest.raises(ValueError, match="requires StaticPool"):
        ThrottledEngine.from_url("sqlite+aiosqlite:///:memory:", poolclass=NullPool)


async def test_file_database_keeps_configured_pool_size(tmp_path: Path) -> None:
    engine = ThrottledEngine.from_url(f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite'}", max_concurrency_per_db=3)
    try:
        assert isinstance(engine.engine.pool, QueuePool)
        assert engine.engine.pool.size() == 3
    finally:
        await engine.aclose()
