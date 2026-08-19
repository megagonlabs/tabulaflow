import asyncio
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pandas as pd
import pytest

from tabulaflow.core import SQLSchema
from tabulaflow.data import Neo4jConnector, Neo4jConnectorConfig, SQLConnector, SQLConnectorConfig
from tabulaflow.data._cache import query_cache_key, query_cache_path, read_cached_model, schema_cache_path


async def _connector(
    tmp_path: Path,
    *,
    global_id: str,
    config: SQLConnectorConfig,
    schema: SQLSchema | None = None,
    read_only: bool = False,
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
        read_only=read_only,
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

    cache_path = schema_cache_path(cache_dir, "cached")
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

    cache_path.write_text("not json")
    connector = await _connector(tmp_path, global_id="cached", config=read_write)
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

    invalid_required_path = schema_cache_path(cache_only.cache_dir, "invalid-required")
    invalid_required_path.parent.mkdir(parents=True)
    invalid_required_path.write_text("not json")
    with pytest.raises(RuntimeError, match="Required schema cache is invalid"):
        await _connector(tmp_path, global_id="invalid-required", config=cache_only)


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
        read_only=True,
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
    assert second.latency_seconds is None
    assert list((config.cache_dir / "query_results").glob("v1@query-cache@*.json"))


async def test_query_cache_rejects_writable_connector(tmp_path: Path) -> None:
    config = SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="read_write")

    with pytest.raises(ValueError, match="Query caching requires read_only=True"):
        await _connector(
            tmp_path,
            global_id="writable-query-cache",
            config=config,
            schema=SQLSchema(name="query-cache", dialect="sqlite", tables=[]),
        )


async def test_invalid_query_cache_entry_is_rebuilt(tmp_path: Path) -> None:
    config = SQLConnectorConfig(
        cache_dir=tmp_path / "cache",
        schema_cache_mode="off",
        query_cache_mode="read_write",
    )
    key = query_cache_key("SELECT 1 AS value", (), config.query_timeout_seconds, config.max_result_rows)
    path = query_cache_path(config.cache_dir, "invalid-query-cache", key)
    path.parent.mkdir(parents=True)
    path.write_text("not json")
    connector = await _connector(
        tmp_path,
        global_id="invalid-query-cache",
        config=config,
        schema=SQLSchema(name="query-cache", dialect="sqlite", tables=[]),
        read_only=True,
    )

    try:
        result = await connector.run_query_async("SELECT 1 AS value")
    finally:
        await connector.disconnect_async()

    assert result.error is None
    assert (await read_cached_model(path, type(result))).df is not None


async def test_query_cache_coalesces_concurrent_identical_queries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = SQLConnectorConfig(
        cache_dir=tmp_path / "cache",
        schema_cache_mode="off",
        query_cache_mode="read_write",
    )
    connector = await _connector(
        tmp_path,
        global_id="concurrent-query-cache",
        config=config,
        schema=SQLSchema(name="query-cache", dialect="sqlite", tables=[]),
        read_only=True,
    )
    executions = 0

    async def execute(*_args: object, **_kwargs: object) -> object:
        nonlocal executions
        executions += 1
        await asyncio.sleep(0.01)
        return SimpleNamespace(
            result=pd.DataFrame({"value": [1]}),
            latency_seconds=0.01,
            affected_rows=None,
        )

    monkeypatch.setattr(connector._t_eng, "execute_async", execute)
    try:
        results = await asyncio.gather(
            connector.run_query_async("SELECT 1 AS value"),
            connector.run_query_async("SELECT 1 AS value"),
        )
    finally:
        await connector.disconnect_async()

    assert executions == 1
    assert sum(result.latency_seconds is None for result in results) == 1


async def test_query_cache_does_not_store_successful_no_result_statements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = SQLConnectorConfig(
        cache_dir=tmp_path / "cache",
        schema_cache_mode="off",
        query_cache_mode="read_write",
    )
    connector = await _connector(
        tmp_path,
        global_id="no-result-query-cache",
        config=config,
        schema=SQLSchema(name="query-cache", dialect="sqlite", tables=[]),
        read_only=True,
    )
    executions = 0

    async def execute(*_args: object, **_kwargs: object) -> object:
        nonlocal executions
        executions += 1
        return SimpleNamespace(result=None, latency_seconds=0.01, affected_rows=None)

    monkeypatch.setattr(connector._t_eng, "execute_async", execute)
    try:
        first = await connector.run_query_async("SET some_session_option = 1")
        second = await connector.run_query_async("SET some_session_option = 1")
    finally:
        await connector.disconnect_async()

    assert first.df is None and first.error is None
    assert second.df is None and second.error is None
    assert executions == 2
    assert not list((config.cache_dir / "query_results").glob("*.json"))


async def test_query_cache_does_not_store_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = SQLConnectorConfig(
        cache_dir=tmp_path / "cache",
        schema_cache_mode="off",
        query_cache_mode="read_write",
    )
    connector = await _connector(
        tmp_path,
        global_id="error-query-cache",
        config=config,
        schema=SQLSchema(name="query-cache", dialect="sqlite", tables=[]),
        read_only=True,
    )
    executions = 0

    async def execute(*_args: object, **_kwargs: object) -> object:
        nonlocal executions
        executions += 1
        raise RuntimeError("query failed")

    monkeypatch.setattr(connector._t_eng, "execute_async", execute)
    try:
        first = await connector.run_query_async("SELECT broken")
        second = await connector.run_query_async("SELECT broken")
    finally:
        await connector.disconnect_async()

    assert first.error is not None
    assert second.error is not None
    assert executions == 2
    assert not list((config.cache_dir / "query_results").glob("*.json"))


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
