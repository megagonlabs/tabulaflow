from __future__ import annotations

import pandas as pd
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll

from tabulaflow.app.display import VIEW_KIND_DATA, VIEW_KIND_QUERY, build_resolved_output_card_views
from tabulaflow.app.widgets import AgentResultWidget
from tabulaflow.chat import ChatResult
from tabulaflow.core.outputs import ResultMetadata
from tabulaflow.toolhub.output_resolver import ResolvedArtifact, ResolvedOutput, ResolvedTableArtifact
from tabulaflow.toolhub.output_store import ResultPayload


def _result(result_id: str, label: str) -> ResolvedTableArtifact:
    return ResolvedTableArtifact(
        artifact_id=result_id,
        source_id=result_id,
        label=label,
        payload=ResultPayload(
            metadata=ResultMetadata(id=result_id, db_alias="debug", query=f"SELECT '{label}' AS label"),
            df=pd.DataFrame({"label": [label], "value": [1]}),
        ),
    )


class _ResultWidgetApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        artifacts: list[ResolvedArtifact] = [
            _result("Q1", "one"),
            _result("Q2", "two"),
        ]
        self.result_widget = AgentResultWidget(
            ChatResult(
                text="x",
            ),
            build_resolved_output_card_views(ResolvedOutput(selection={}, artifacts=artifacts)),
        )

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["focus-surface"] = "#1a212c"
        return variables

    def compose(self) -> ComposeResult:
        yield VerticalScroll(self.result_widget, id="chat-log")

    def on_mount(self) -> None:
        self.result_widget.focus()


async def test_card_switch_refreshes_displayed_content() -> None:
    app = _ResultWidgetApp()

    async with app.run_test(size=(100, 30)) as pilot:
        widget = app.result_widget
        await pilot.pause()
        first_content = widget._content.content

        await pilot.press("right")
        await pilot.pause()

        assert widget.current_card == 1
        assert widget._content.content is not first_content

        second_content = widget._content.content
        await pilot.press("left")
        await pilot.pause()

        assert widget.current_card == 0
        assert widget._content.content is not second_content


def _current_kind(widget: AgentResultWidget) -> str:
    view = widget._current_view_or_none()
    assert view is not None
    return view.kind


async def test_view_selection_is_per_result() -> None:
    app = _ResultWidgetApp()

    async with app.run_test(size=(100, 30)) as pilot:
        widget = app.result_widget
        await pilot.pause()

        await pilot.press("right_square_bracket")
        await pilot.pause()
        assert _current_kind(widget) == VIEW_KIND_QUERY

        await pilot.press("right")
        await pilot.pause()
        assert widget.current_card == 1
        assert _current_kind(widget) == VIEW_KIND_DATA

        await pilot.press("left")
        await pilot.pause()
        assert widget.current_card == 0
        assert _current_kind(widget) == VIEW_KIND_QUERY
