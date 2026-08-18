from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pandas as pd
import pytest

from tabulaflow.core import SQLSchema
from tabulaflow.data import Neo4jConnector, Neo4jConnectorConfig, SQLConnector, SQLConnectorConfig


async def _connector(
    tmp_path: Path,
    *,
    global_id: str,
    config: SQLConnectorConfig,
    schema: SQLSchema | None = None,
) -> SQLConnector:
    db_path = tmp_path / f"{global_id}.sqlite"
    if schema is None:
        with sqlite3.connect(db_path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS items (value INTEGER)")
    return await SQLConnector.from_url_async(
        global_id=global_id,
        url=f"sqlite+aiosqlite:///{db_path}",
        db_name=global_id,
        schema=schema,
        read_only=False,
        config=config,
    )


async def test_schema_cache_modes(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    read_write = SQLConnectorConfig(
        cache_dir=cache_dir,
        schema_cache_mode="read_write",
    )
    connector = await _connector(tmp_path, global_id="cached", config=read_write)
    await connector.disconnect_async()

    cache_path = cache_dir / "schemas" / "cached.json"
    assert cache_path.is_file()

    cached_schema = SQLSchema(name="from-cache", dialect="sqlite", tables=[])
    cache_path.write_text(cached_schema.model_dump_json())

    connector = await _connector(tmp_path, global_id="cached", config=read_write)
    try:
        assert connector.schema.name == "from-cache"
    finally:
        await connector.disconnect_async()

    refresh = SQLConnectorConfig(
        cache_dir=cache_dir,
        schema_cache_mode="refresh",
    )
    connector = await _connector(tmp_path, global_id="cached", config=refresh)
    try:
        assert connector.schema.name == "cached"
    finally:
        await connector.disconnect_async()

    off = SQLConnectorConfig(
        cache_dir=tmp_path / "off-cache",
        schema_cache_mode="off",
    )
    connector = await _connector(tmp_path, global_id="uncached", config=off)
    await connector.disconnect_async()
    assert not off.cache_dir.exists()

    cache_only = SQLConnectorConfig(
        cache_dir=tmp_path / "missing-cache",
        schema_cache_mode="cache_only",
    )
    with pytest.raises(FileNotFoundError, match="Schema cache required"):
        await _connector(tmp_path, global_id="missing", config=cache_only)
    assert not cache_only.cache_dir.exists()


async def test_connector_timeout_uses_config_unless_explicitly_overridden(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = SQLConnectorConfig(
        query_timeout_seconds=17,
        schema_cache_mode="off",
    )
    connector = await _connector(
        tmp_path,
        global_id="timeout",
        config=config,
        schema=SQLSchema(name="timeout", dialect="sqlite", tables=[]),
    )
    captured: list[int | None] = []

    async def execute(
        _query: object,
        _parameters: object,
        timeout: int | None,
        *,
        return_df: bool,
        max_rows: int | None,
    ) -> object:
        captured.append(timeout)
        return SimpleNamespace(
            result=pd.DataFrame({"value": [1]}),
            latency_seconds=0.0,
            affected_rows=None,
        )

    monkeypatch.setattr(connector._t_eng, "execute_async", execute)
    try:
        await connector.run_query_async("SELECT 1")
        await connector.run_query_async("SELECT 1", timeout=None)
        await connector.run_query_async("SELECT 1", timeout=5)
    finally:
        await connector.disconnect_async()

    assert captured == [17, None, 5]


async def test_query_cache_mode_controls_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = SQLConnectorConfig(
        cache_dir=tmp_path / "cache",
        schema_cache_mode="off",
        query_cache_mode="read_write",
    )
    connector = await _connector(
        tmp_path,
        global_id="query-cache",
        config=config,
        schema=SQLSchema(name="query-cache", dialect="sqlite", tables=[]),
    )
    first = await connector.run_query_async("SELECT 1 AS value")
    assert first.df is not None

    async def fail_if_executed(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("cached query was executed")

    monkeypatch.setattr(connector._t_eng, "execute_async", fail_if_executed)
    try:
        second = await connector.run_query_async("SELECT 1 AS value")
    finally:
        await connector.disconnect_async()

    assert second.df is not None
    assert second.df.to_dict(orient="records") == [{"value": 1}]
    assert list((config.cache_dir / "query_results").glob("query-cache_*.json"))


async def test_neo4j_uses_configured_timeout_and_result_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    connector = object.__new__(Neo4jConnector)
    connector.read_only = False
    connector.config = Neo4jConnectorConfig(
        max_result_rows=2,
        query_timeout_seconds=17,
        schema_cache_mode="off",
    )
    captured: list[tuple[int | None, int | None]] = []

    async def run_cypher(
        _query: str,
        _parameters: object,
        timeout: int | None,
        *,
        return_df: bool,
        max_rows: int | None,
    ) -> pd.DataFrame:
        captured.append((timeout, max_rows))
        return pd.DataFrame({"value": [1]})

    monkeypatch.setattr(connector, "_run_cypher", run_cypher)

    await connector.run_query_async("RETURN 1")
    await connector.run_query_async("RETURN 1", timeout=None)

    assert captured == [(17, 2), (None, 2)]
