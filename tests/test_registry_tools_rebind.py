"""Registry tools must not serve a stale connector after its alias is unregistered or re-bound."""

from pathlib import Path

import pytest
import sqlalchemy
from pydantic_ai import ToolReturn
from sqlalchemy.ext.asyncio import create_async_engine

from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.db_connector.sql_conn import SQLConnector
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
