from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Tree

from tabulaflow.app.tui.screens.results import DataBrowserScreen
from tabulaflow.app.tui.screens.schema import ExplorerState, SchemaBrowserScreen
from tabulaflow.core import ErrorInfo, ExecResult
from tabulaflow.data import DataConnectorRegistry, SQLConnector
from tabulaflow.data.config import SQLConnectorConfig


class ExplorerApp(App[None]):
    def __init__(self, registry: DataConnectorRegistry, state: ExplorerState) -> None:
        super().__init__()
        self.registry = registry
        self.state = state

    def compose(self) -> ComposeResult:
        yield SchemaBrowserScreen(registry=self.registry, state=self.state)


@pytest.fixture
async def connector() -> AsyncIterator[SQLConnector]:
    connector = await SQLConnector.from_url_async(
        "duckdb:///:memory:",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    try:
        await connector.write_dataframe_async(pd.DataFrame({"value": range(75)}), "items")
        yield connector
    finally:
        await connector.close_async()


def make_app(connector: SQLConnector, state: ExplorerState | None = None) -> ExplorerApp:
    registry = DataConnectorRegistry()
    registry.register("data", connector)
    return ExplorerApp(registry, state or ExplorerState())


def table_node(screen: SchemaBrowserScreen) -> Any:
    tree = screen.query_one(Tree)
    return next(
        node
        for source in tree.root.children
        for schema in source.children
        for node in schema.children
        if node.data is not None and node.data.kind == "table"
    )


async def test_count_starts_on_preview_and_is_cached_across_reopening(connector: SQLConnector) -> None:
    state = ExplorerState()
    with patch.object(connector, "count_rows_async", wraps=connector.count_rows_async) as count:
        app = make_app(connector, state)
        async with app.run_test() as pilot:
            screen = app.query_one(SchemaBrowserScreen)
            node = table_node(screen)
            screen.query_one(Tree).select_node(node)
            await pilot.pause()
            assert "rows" not in str(screen._status.render())
            assert "Count rows" not in str(screen._hint.render())
            count.assert_not_called()
            await screen.action_open_preview()
            await app.workers.wait_for_complete()
            await pilot.press("escape")
            assert node.label.plain == "items  75 rows"
            assert "75 rows (last counted)" in str(screen._status.render())
            assert connector.schema.tables[0].num_rows is None
            await screen.action_open_preview()
            await app.workers.wait_for_complete()
            await pilot.press("escape")
        async with make_app(connector, state).run_test() as reopened:
            screen = reopened.app.query_one(SchemaBrowserScreen)
            assert table_node(screen).label.plain == "items  75 rows"
        assert count.call_count == 1


async def test_refresh_invalidates_count(connector: SQLConnector) -> None:
    app = make_app(connector)
    async with app.run_test() as pilot:
        screen = app.query_one(SchemaBrowserScreen)
        screen.query_one(Tree).select_node(table_node(screen))
        await screen.action_open_preview()
        await app.workers.wait_for_complete()
        await pilot.press("escape")
        await screen.action_refresh_schema()
        assert table_node(screen).label.plain == "items"


@pytest.mark.parametrize("total", [None, 75, 0, 3])
async def test_preview_distinguishes_sample_and_total(connector: SQLConnector, total: int | None) -> None:
    if total == 0:
        await connector.run_query_async("DELETE FROM items")
    elif total == 3:
        await connector.run_query_async("DELETE FROM items WHERE value >= 3")
    connector.schema.tables[0].num_rows = total
    app = make_app(connector)
    async with app.run_test() as pilot:
        screen = app.query_one(SchemaBrowserScreen)
        screen.query_one(Tree).select_node(table_node(screen))
        await pilot.pause()
        assert "Preview table" in str(screen._hint.render())
        await screen.action_open_preview()
        await app.workers.wait_for_complete()
        await pilot.pause()
        preview = app.screen
        assert isinstance(preview, DataBrowserScreen)
        assert preview._title == "data: main.items"
        status = str(preview._status.render())
        assert f"{75 if total is None else total} total rows" in status
        if total == 0:
            assert "No rows returned" in status
        elif total == 3:
            assert "3 preview rows" in status
        else:
            assert "50 preview rows" in status
        assert "Preview rows" in status


async def test_cached_total_does_not_trigger_count(connector: SQLConnector) -> None:
    connector.schema.tables[0].num_rows = 75
    app = make_app(connector)
    with patch.object(connector, "count_rows_async", new=AsyncMock()) as count:
        async with app.run_test():
            screen = app.query_one(SchemaBrowserScreen)
            screen.query_one(Tree).select_node(table_node(screen))
            await screen.action_open_preview()
            await app.workers.wait_for_complete()
            preview = app.screen
            assert isinstance(preview, DataBrowserScreen)
            assert "75 total rows" in str(preview._status.render())
            count.assert_not_called()


async def test_count_failure_keeps_preview_usable(connector: SQLConnector) -> None:
    app = make_app(connector)
    result = ExecResult(error=ErrorInfo(exc_type="TimeoutError", message="Timed out"))
    with patch.object(connector, "count_rows_async", new=AsyncMock(return_value=result)):
        async with app.run_test() as pilot:
            screen = app.query_one(SchemaBrowserScreen)
            screen.query_one(Tree).select_node(table_node(screen))
            await screen.action_open_preview()
            await app.workers.wait_for_complete()
            preview = app.screen
            assert isinstance(preview, DataBrowserScreen)
            assert "Total unavailable" in str(preview._status.render())
            assert len(preview._df) == 50
            await pilot.press("escape")
            assert table_node(screen).label.plain == "items"
            assert "rows" not in str(screen._status.render())


async def test_count_does_not_block_preview_and_cancels_on_close(connector: SQLConnector) -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def count(*args: Any, **kwargs: Any) -> ExecResult:
        started.set()
        try:
            await asyncio.Event().wait()
            raise AssertionError("Count should be cancelled")
        finally:
            cancelled.set()

    app = make_app(connector)
    with patch.object(connector, "count_rows_async", new=count):
        async with app.run_test() as pilot:
            screen = app.query_one(SchemaBrowserScreen)
            screen.query_one(Tree).select_node(table_node(screen))
            await screen.action_open_preview()
            await asyncio.wait_for(started.wait(), 5)
            preview = app.screen
            assert isinstance(preview, DataBrowserScreen)
            assert "Counting total" in str(preview._status.render())
            await pilot.press("down")
            assert preview._table.cursor_coordinate.row == 1
            await pilot.press("escape")
            await asyncio.wait_for(cancelled.wait(), 5)
            assert not app.state.row_counts


async def test_live_count_bypasses_query_cache_and_supports_views(connector: SQLConnector) -> None:
    await connector.run_query_async('CREATE VIEW "items view" AS SELECT * FROM items')
    connector.read_only = True
    connector.config = connector.config.model_copy(update={"sql_query_cache_mode": "read_write"})
    with patch.object(connector, "run_query_async", new=AsyncMock(side_effect=AssertionError("cached query"))):
        result = await connector.count_rows_async("items view", schema_name="main")
        assert result.error is None
        assert result.df is not None
        assert result.df.iloc[0, 0] == 75
        await connector._execute_query_async("INSERT INTO items VALUES (100)", (), 30)
        result = await connector.count_rows_async("items view", schema_name="main")
        assert result.df is not None
        assert result.df.iloc[0, 0] == 76


async def test_count_error_is_returned_and_empty_table_counts_zero(connector: SQLConnector) -> None:
    result = await connector.count_rows_async("missing table", schema_name="main")
    assert result.error is not None
    await connector.run_query_async("DELETE FROM items")
    result = await connector.count_rows_async("items", schema_name="main")
    assert result.df is not None and result.df.iloc[0, 0] == 0


async def test_count_finishing_after_refresh_is_discarded(connector: SQLConnector) -> None:
    started = asyncio.Event()
    finish = asyncio.Event()

    async def count(*args: Any, **kwargs: Any) -> ExecResult:
        started.set()
        await finish.wait()
        return ExecResult(df=pd.DataFrame({"count": [75]}))

    app = make_app(connector)
    with patch.object(connector, "count_rows_async", new=count):
        async with app.run_test():
            screen = app.query_one(SchemaBrowserScreen)
            screen.query_one(Tree).select_node(table_node(screen))
            await screen.action_open_preview()
            await asyncio.wait_for(started.wait(), 5)
            await screen.action_refresh_schema()
            finish.set()
            await app.workers.wait_for_complete()
            assert table_node(screen).label.plain == "items"
            assert not app.state.row_counts


async def test_regular_result_browser_keeps_result_row_wording() -> None:
    screen = DataBrowserScreen(title="Result", df=pd.DataFrame({"value": [1]}))
    app: App[None] = App()
    async with app.run_test() as pilot:
        app.push_screen(screen)
        await pilot.pause()
        assert "Rows 1-1 of 1" in str(screen._status.render())
        assert "Preview rows" not in str(screen._status.render())
