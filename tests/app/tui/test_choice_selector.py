from __future__ import annotations

from typing import cast

import pytest
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Static

from tabulaflow.app.tui.theme import FOCUS_SURFACE
from tabulaflow.app.tui.widgets.choice import InlineChoiceSelector


class _ChoiceApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.selected: str | None = None
        self.cancelled = False

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["focus-surface"] = FOCUS_SURFACE
        return variables

    def compose(self) -> ComposeResult:
        yield InlineChoiceSelector(
            "Choose subset",
            ("cola", "mnli", "mrpc", "qnli"),
            confirm_label="Connect",
        )

    def on_inline_choice_selector_selected(self, event: InlineChoiceSelector.Selected) -> None:
        self.selected = event.value

    def on_inline_choice_selector_cancelled(self, event: InlineChoiceSelector.Cancelled) -> None:
        self.cancelled = True


async def test_inline_choice_selector_filters_and_selects() -> None:
    app = _ChoiceApp()

    async with app.run_test(size=(100, 24)) as pilot:
        await pilot.pause()
        selector = app.query_one(InlineChoiceSelector)
        assert selector.has_focus
        assert "Type Filter" in cast(Text, app.query_one("#choice-title", Static).render()).plain

        await pilot.press("m", "r")
        await pilot.pause()

        assert "· “mr”" in cast(Text, app.query_one("#choice-title", Static).render()).plain
        options = cast(Text, app.query_one("#choice-options", Static).render()).plain
        assert "mrpc" in options
        assert "mnli" not in options

        await pilot.press("enter")
        await pilot.pause()

        assert app.selected == "mrpc"


async def test_inline_choice_selector_backspace_and_cancel() -> None:
    app = _ChoiceApp()

    async with app.run_test(size=(100, 24)) as pilot:
        await pilot.press("m", "r", "backspace")
        await pilot.pause()

        assert "· “m”" in cast(Text, app.query_one("#choice-title", Static).render()).plain

        await pilot.press("escape")
        await pilot.pause()

        assert app.cancelled is True


@pytest.mark.parametrize("terminal_width", [60, 80])
async def test_inline_choice_selector_keeps_hints_anchored_while_filtering(
    terminal_width: int,
) -> None:
    app = _ChoiceApp()

    async with app.run_test(size=(terminal_width, 24)) as pilot:
        await pilot.pause()
        title_widget = app.query_one("#choice-title", Static)
        initial = cast(Text, title_widget.render()).plain
        hint_column = initial.index("↑↓")

        await pilot.press("m", "r", "p", "c")
        await pilot.pause()

        filtered = cast(Text, title_widget.render()).plain
        assert filtered.index("↑↓") == hint_column
        assert len(filtered) == len(initial)
