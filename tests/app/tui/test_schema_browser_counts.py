from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static, Tree

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


async def test_count_is_explicit_and_cached_across_reopening(connector: SQLConnector) -> None:
    state = ExplorerState()
    with patch.object(connector, "count_rows_async", wraps=connector.count_rows_async) as count:
        app = make_app(connector, state)
        async with app.run_test() as pilot:
            screen = app.query_one(SchemaBrowserScreen)
            node = table_node(screen)
            screen.query_one(Tree).select_node(node)
            await pilot.pause()
            assert "unknown" in str(screen._status.render())
            count.assert_not_called()
            await screen.action_count_rows().wait()
            assert node.label.plain == "items  75 rows"
            assert "75 rows (last counted)" in str(screen._status.render())
            assert connector.schema.tables[0].num_rows is None
        async with make_app(connector, state).run_test() as reopened:
            screen = reopened.app.query_one(SchemaBrowserScreen)
            assert table_node(screen).label.plain == "items  75 rows"
        assert count.call_count == 1


async def test_refresh_invalidates_count(connector: SQLConnector) -> None:
    app = make_app(connector)
    async with app.run_test():
        screen = app.query_one(SchemaBrowserScreen)
        screen.query_one(Tree).select_node(table_node(screen))
        await screen.action_count_rows().wait()
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
        await pilot.pause()
        preview = app.screen
        assert isinstance(preview, DataBrowserScreen)
        if total is None:
            assert "Preview: 50 rows · total unknown" in preview._title
        elif total == 0:
            assert "No rows returned" in preview._title
        elif total == 3:
            assert "Preview: 3 of 3 rows" in preview._title
        else:
            assert "Preview: 50 of 75 rows" in preview._title
        assert "Preview rows" in str(preview._status.render())


async def test_count_failure_preserves_previous_count(connector: SQLConnector) -> None:
    app = make_app(connector)
    async with app.run_test():
        screen = app.query_one(SchemaBrowserScreen)
        node = table_node(screen)
        screen.query_one(Tree).select_node(node)
        await screen.action_count_rows().wait()
        result = ExecResult(error=ErrorInfo(exc_type="TimeoutError", message="Timed out"))
        with patch.object(connector, "count_rows_async", new=AsyncMock(return_value=result)):
            await screen.action_count_rows().wait()
        assert node.label.plain == "items  75 rows"
        assert "Count failed: Timed out" in str(screen._status.render())


async def test_count_does_not_block_navigation_and_cancels_on_close(connector: SQLConnector) -> None:
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
            await pilot.press("c")
            await asyncio.wait_for(started.wait(), 5)
            await pilot.press("up")
            node = screen.query_one(Tree).cursor_node
            assert node is not None and node.data is not None and node.data.kind != "table"
        await asyncio.wait_for(cancelled.wait(), 5)


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
            worker = screen.action_count_rows()
            await asyncio.wait_for(started.wait(), 5)
            await screen.action_refresh_schema()
            finish.set()
            await worker.wait()
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


@pytest.mark.parametrize("size", [(80, 24), (160, 40)])
async def test_explorer_is_a_right_side_drawer(connector: SQLConnector, size: tuple[int, int]) -> None:
    registry = DataConnectorRegistry()
    registry.register("data", connector)

    class ChatApp(App[None]):
        def compose(self) -> ComposeResult:
            yield Static("Chat stays visible", id="chat")

    app = ChatApp()
    async with app.run_test(size=size) as pilot:
        chat_screen = app.screen
        explorer = SchemaBrowserScreen(registry=registry)
        await app.push_screen(explorer)
        await pilot.pause()
        drawer = explorer.query_one("#explorer-drawer")
        assert 0 < drawer.region.x < size[0]
        assert drawer.region.right == size[0]
        assert drawer.region.width <= 100
        assert drawer.region.height == size[1]
        assert explorer.query_one(Tree).region.x >= drawer.region.x
        assert chat_screen.query_one("#chat").is_mounted
        await pilot.press("escape")
        assert app.screen is chat_screen
