"""Registry tools must not serve a stale connector after its alias is unregistered or re-bound."""

from pathlib import Path
from typing import Any, ClassVar, Literal, cast

import asyncio
import pandas as pd
import pytest
import sqlalchemy
from pydantic_ai import ToolReturn
from sqlalchemy.ext.asyncio import create_async_engine

from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.core.types import ExecResult
from tabulaflow.toolhub.registry_run_query import RegistryRunQueryTool


def _text(result: ToolReturn) -> str:
    value = result.return_value
    assert isinstance(value, str)
    return value


async def _make_connector(tmp_path: Path, name: str, value: str) -> SQLConnector:
    """Create a sqlite connector whose single table holds one distinctive value."""
    db_path = tmp_path / f"{name}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.execute(sqlalchemy.text("CREATE TABLE t (val TEXT);"))
        await conn.execute(sqlalchemy.text(f"INSERT INTO t VALUES ('{value}');"))
    await engine.dispose()
    return await SQLConnector.from_url_async(
        global_id=f"test_{name}",
        url=f"sqlite+aiosqlite:///{db_path}",
        db_name=name,
    )


@pytest.mark.asyncio
async def test_run_query_fails_after_disconnect(tmp_path: Path) -> None:
    """After unregistering an alias, a previously used run_query tool must reject it."""
    registry = DBRegistry()
    registry.register("mydb", await _make_connector(tmp_path, "db_a", "alpha"))
    tool = RegistryRunQueryTool(registry)

    assert "alpha" in _text(await tool("mydb", "SELECT val FROM t"))

    assert await registry.unregister_async("mydb")
    result_text = _text(await tool("mydb", "SELECT val FROM t"))
    assert "unknown db_alias" in result_text
    assert "alpha" not in result_text


@pytest.mark.asyncio
async def test_run_query_uses_new_connector_after_rebind(tmp_path: Path) -> None:
    """Re-binding an alias to a different connector must not serve the old one from cache."""
    registry = DBRegistry()
    registry.register("mydb", await _make_connector(tmp_path, "db_a", "alpha"))
    tool = RegistryRunQueryTool(registry)
    assert "alpha" in _text(await tool("mydb", "SELECT val FROM t"))

    await registry.unregister_async("mydb")
    registry.register("mydb", await _make_connector(tmp_path, "db_b", "bravo"))

    result_text = _text(await tool("mydb", "SELECT val FROM t"))
    assert "bravo" in result_text
    assert "alpha" not in result_text


class RefreshBlockingConnector:
    connector_type: ClassVar[Literal["sql"]] = "sql"
    global_id = "refresh_blocking"
    language = "sqlite"
    schema = None

    def __init__(self) -> None:
        self.refresh_started = asyncio.Event()
        self.release_refresh = asyncio.Event()

    async def run_query_async(self, query: Any, parameters: Any = (), timeout: int | None = None) -> ExecResult:
        return ExecResult(df=pd.DataFrame({"query": [query]}))

    async def refresh_schema_async(self, tables: Any = None) -> Any:
        self.refresh_started.set()
        await self.release_refresh.wait()
        return self.schema

    async def disconnect_async(self) -> None:
        pass


@pytest.mark.asyncio
async def test_concurrent_run_query_records_each_invocation_query() -> None:
    """Registry recording must not read a shared last-query slot after another call overwrites it."""
    connector = RefreshBlockingConnector()
    registry = DBRegistry()
    registry.register("mydb", cast(Any, connector))
    tool = RegistryRunQueryTool(registry, enable_refresh=True)

    first_task = asyncio.create_task(tool("mydb", "SELECT 'first' AS label", refresh=True))
    await connector.refresh_started.wait()

    second_result = await tool("mydb", "SELECT 'second' AS label")
    connector.release_refresh.set()
    first_result = await first_task

    assert "SELECT 'second' AS label" in _text(second_result)
    assert "SELECT 'first' AS label" in _text(first_result)

    second_payload = await tool._output_store.get_payload("R1")  # noqa: SLF001
    first_payload = await tool._output_store.get_payload("R2")  # noqa: SLF001
    assert second_payload.metadata.query == "SELECT 'second' AS label"
    assert first_payload.metadata.query == "SELECT 'first' AS label"
