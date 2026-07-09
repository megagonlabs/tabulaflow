from __future__ import annotations

import pandas as pd
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll

from tabulaflow.app.widgets import AgentResultWidget
from tabulaflow.chat.result import ChatResult, ChatResultRecord


def _record(record_id: str, label: str) -> ChatResultRecord:
    return ChatResultRecord(
        record_id=record_id,
        label=label,
        query=f"SELECT '{label}' AS label",
        df=pd.DataFrame({"label": [label], "value": [1]}),
        chart_spec=None,
        query_lexer="sql",
    )


class _ResultWidgetApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.result_widget = AgentResultWidget(
            ChatResult(
                text="x",
                artifacts=[
                    _record("Q1", "one"),
                    _record("Q2", "two"),
                ],
            )
        )

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["focus-surface"] = "#1a212c"
        return variables

    def compose(self) -> ComposeResult:
        yield VerticalScroll(self.result_widget, id="chat-log")

    def on_mount(self) -> None:
        self.result_widget.focus()


async def test_record_switch_refreshes_displayed_content() -> None:
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
