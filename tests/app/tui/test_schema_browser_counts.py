from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from rich.text import Text
from sqlalchemy.sql.functions import count as sql_count
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
    with patch.object(connector, "run_query_async", wraps=connector.run_query_async) as query:
        app = make_app(connector, state)
        async with app.run_test() as pilot:
            screen = app.query_one(SchemaBrowserScreen)
            node = table_node(screen)
            screen.query_one(Tree).select_node(node)
            await pilot.pause()
            assert "rows" not in str(screen._status.render())
            assert "Count rows" not in str(screen._hint.render())
            query.assert_not_called()
            await screen.action_open_preview()
            await app.workers.wait_for_complete()
            await pilot.press("escape")
            assert node.label.plain == "items  75 rows"
            assert "75 rows" in str(screen._status.render())
            assert "last counted" not in str(screen._status.render())
            assert connector.schema.tables[0].num_rows is None
            await screen.action_open_preview()
            await app.workers.wait_for_complete()
            await pilot.press("escape")
        async with make_app(connector, state).run_test() as reopened:
            screen = reopened.app.query_one(SchemaBrowserScreen)
            assert table_node(screen).label.plain == "items  75 rows"
        assert sum(isinstance(call.args[0].selected_columns[0], sql_count) for call in query.call_args_list) == 1


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
        if total == 0:
            assert "No rows returned" in status
            assert "0 rows" not in status
        elif total == 3:
            assert "Showing 3 of 3 rows · 1 column" in status
        else:
            assert "Showing 50 of 75 rows · 1 column" in status
        assert "Page" not in status
        assert "Preview rows" not in status
        assert "last counted" not in status
        hint = str(preview._hint.render())
        assert "Prev/Next page" not in hint
        assert "Open in browser" in hint


async def test_cached_total_does_not_trigger_count(connector: SQLConnector) -> None:
    connector.schema.tables[0].num_rows = 75
    app = make_app(connector)
    with patch.object(connector, "run_query_async", wraps=connector.run_query_async) as query:
        async with app.run_test():
            screen = app.query_one(SchemaBrowserScreen)
            screen.query_one(Tree).select_node(table_node(screen))
            await screen.action_open_preview()
            await app.workers.wait_for_complete()
            preview = app.screen
            assert isinstance(preview, DataBrowserScreen)
            assert "Showing 50 of 75 rows" in str(preview._status.render())
            query.assert_awaited_once()
            assert not isinstance(query.call_args.args[0].selected_columns[0], sql_count)


async def test_count_failure_keeps_preview_usable(connector: SQLConnector) -> None:
    app = make_app(connector)
    result = ExecResult(error=ErrorInfo(exc_type="TimeoutError", message="Timed out"))
    preview_result = ExecResult(df=pd.DataFrame({"value": range(50)}))
    with patch.object(connector, "run_query_async", new=AsyncMock(side_effect=[preview_result, result])):
        async with app.run_test() as pilot:
            screen = app.query_one(SchemaBrowserScreen)
            screen.query_one(Tree).select_node(table_node(screen))
            await screen.action_open_preview()
            await app.workers.wait_for_complete()
            preview = app.screen
            assert isinstance(preview, DataBrowserScreen)
            assert "Showing 50 rows · 1 column · total unavailable" in str(preview._status.render())
            assert len(preview._df) == 50
            await pilot.press("escape")
            assert table_node(screen).label.plain == "items"
            assert "rows" not in str(screen._status.render())


async def test_count_does_not_block_preview_and_cancels_on_close(connector: SQLConnector) -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    run_query = connector.run_query_async

    async def query(statement: Any, **kwargs: Any) -> ExecResult:
        if not isinstance(statement.selected_columns[0], sql_count):
            return await run_query(statement, **kwargs)
        started.set()
        try:
            await asyncio.Event().wait()
            raise AssertionError("Count should be cancelled")
        finally:
            cancelled.set()

    app = make_app(connector)
    with patch.object(connector, "run_query_async", new=query):
        async with app.run_test() as pilot:
            screen = app.query_one(SchemaBrowserScreen)
            screen.query_one(Tree).select_node(table_node(screen))
            await screen.action_open_preview()
            await asyncio.wait_for(started.wait(), 5)
            preview = app.screen
            assert isinstance(preview, DataBrowserScreen)
            assert "Showing 50 rows · 1 column · counting…" in str(preview._status.render())
            await pilot.press("down")
            assert preview._table.cursor_coordinate.row == 1
            await pilot.press("escape")
            await asyncio.wait_for(cancelled.wait(), 5)
            assert not app.state.row_counts


async def test_count_supports_read_only_views_with_quoted_names(connector: SQLConnector) -> None:
    await connector.run_query_async('CREATE VIEW "items view" AS SELECT * FROM items')
    await connector.refresh_schema_async()
    connector.read_only = True
    app = make_app(connector)
    async with app.run_test():
        screen = app.query_one(SchemaBrowserScreen)
        tree = screen.query_one(Tree)
        node = next(
            node
            for source in tree.root.children
            for schema in source.children
            for node in schema.children
            if node.data is not None and node.data.table_name == "items view"
        )
        tree.select_node(node)
        await screen.action_open_preview()
        await app.workers.wait_for_complete()
        preview = app.screen
        assert isinstance(preview, DataBrowserScreen)
        assert "Showing 50 of 75 rows" in str(preview._status.render())
        assert isinstance(node.label, Text)
        assert node.label.plain == "items view  view  75 rows"


async def test_count_finishing_after_refresh_is_discarded(connector: SQLConnector) -> None:
    started = asyncio.Event()
    finish = asyncio.Event()

    run_query = connector.run_query_async

    async def query(statement: Any, **kwargs: Any) -> ExecResult:
        if not isinstance(statement.selected_columns[0], sql_count):
            return await run_query(statement, **kwargs)
        started.set()
        await finish.wait()
        return ExecResult(df=pd.DataFrame({"count": [75]}))

    app = make_app(connector)
    with patch.object(connector, "run_query_async", new=query):
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
        assert "1 row · 1 column" in str(screen._status.render())
        assert "Page" not in str(screen._status.render())
        assert "Prev/Next page" not in str(screen._hint.render())
        assert "Preview rows" not in str(screen._status.render())


@pytest.mark.parametrize("is_preview", [False, True])
async def test_pagination_only_appears_for_multiple_pages(is_preview: bool) -> None:
    screen = DataBrowserScreen(
        title="Result",
        df=pd.DataFrame({"value": range(75)}),
        is_preview=is_preview,
        total_rows=100 if is_preview else None,
    )
    app: App[None] = App()
    async with app.run_test() as pilot:
        await app.push_screen(screen)
        row_label = "Preview rows" if is_preview else "Rows"
        assert f"{row_label} 1–50 of 75" in str(screen._status.render())
        assert "Page 1/2" in str(screen._status.render())
        assert "Prev/Next page" in str(screen._hint.render())
        if is_preview:
            assert "Showing 75 of 100 rows" in str(screen._status.render())
        await pilot.press("]")
        assert f"{row_label} 51–75 of 75" in str(screen._status.render())
        assert "Page 2/2" in str(screen._status.render())


@pytest.mark.parametrize("total", [None, 0])
async def test_empty_preview_has_one_clear_empty_state(total: int | None) -> None:
    screen = DataBrowserScreen(title="Empty", df=pd.DataFrame(columns=["value"]), is_preview=True, total_rows=total)
    app: App[None] = App()
    async with app.run_test():
        await app.push_screen(screen)
        status = str(screen._status.render())
        assert "No rows returned · 1 column" in status
        assert "0 rows" not in status
        assert "0–0" not in status
        assert "Page" not in status
