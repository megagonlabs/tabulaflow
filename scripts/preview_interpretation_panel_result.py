"""Preview ``AgentResultWidget`` rendering a real ``ChatResult.panel``.

Run from the repo root:

    uv run scripts/preview_interpretation_panel_result.py

This is the integration preview for the implemented panel result model. It uses
the same ``AgentResultWidget`` the chat TUI uses, not the older standalone
prototype in ``preview_disambiguation_panel.py``.
"""

from __future__ import annotations

import pandas as pd
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Static

from tabulaflow.app.theme import FOCUS_SURFACE
from tabulaflow.app.widgets import AgentResultWidget
from tabulaflow.chat import (
    ChatResult,
    ChatResultCombination,
    ChatResultPanel,
    ChatResultPlaceholder,
    ChatResultRecord,
)
from tabulaflow.toolhub import Choice, Dimension


def _record(record_id: str, label: str, rows: list[dict[str, object]]) -> ChatResultRecord:
    return ChatResultRecord(
        record_id=record_id,
        label=label,
        query=f"SELECT * FROM {record_id}",
        df=pd.DataFrame(rows),
        query_lexer="sql",
    )


def _result() -> ChatResult:
    dimensions = [
        Dimension(
            id="ranking",
            label="Ranking",
            choices=[
                Choice(id="net", label="Highest net revenue"),
                Choice(id="count", label="Most orders"),
            ],
        ),
        Dimension(
            id="period",
            label="Time period",
            choices=[
                Choice(id="q2", label="Q2"),
                Choice(id="q3", label="Q3"),
            ],
        ),
    ]

    combinations = [
        ChatResultCombination(
            selection={"ranking": "net", "period": "q2"},
            artifacts=[
                _record(
                    "Q1",
                    "Top customers",
                    [{"customer": "Acme", "value": 10}, {"customer": "Globex", "value": 7}],
                ),
                _record("Q5", "Data coverage", [{"rows": 3, "source": "orders"}]),
            ],
        ),
        ChatResultCombination(
            selection={"ranking": "net", "period": "q3"},
            artifacts=[
                _record("Q2", "Top customers", [{"customer": "Acme", "value": 20}]),
                _record("Q5", "Data coverage", [{"rows": 3, "source": "orders"}]),
            ],
        ),
        ChatResultCombination(
            selection={"ranking": "count", "period": "q2"},
            artifacts=[
                _record(
                    "Q3",
                    "Top customers",
                    [{"customer": "Acme", "value": 1}, {"customer": "Globex", "value": 1}],
                ),
                _record("Q5", "Data coverage", [{"rows": 3, "source": "orders"}]),
            ],
        ),
        ChatResultCombination(
            selection={"ranking": "count", "period": "q3"},
            artifacts=[
                ChatResultPlaceholder(label="Top customers", message="only applies when Time period = Q2"),
                _record("Q5", "Data coverage", [{"rows": 3, "source": "orders"}]),
            ],
        ),
    ]

    return ChatResult(
        text="Preview panel",
        artifacts=combinations[0].artifacts,
        panel=ChatResultPanel(dimensions=dimensions, combinations=combinations),
    )


class InterpretationPanelResultPreview(App[None]):
    CSS = """
    Screen {
        background: $surface;
    }

    #preview-root {
        padding: 1 2;
    }

    #input-bar {
        display: none;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["focus-surface"] = FOCUS_SURFACE
        return variables

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("AgentResultWidget panel preview", classes="dim"),
            AgentResultWidget(_result(), width=100),
            id="preview-root",
        )
        yield Input(id="input-bar")

    def on_mount(self) -> None:
        self.query_one(AgentResultWidget).focus()


if __name__ == "__main__":
    InterpretationPanelResultPreview().run()
