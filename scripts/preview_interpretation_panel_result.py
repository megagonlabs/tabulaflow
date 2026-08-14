"""Preview terminal answer-control interaction.

Run from the repo root:

    uv run scripts/preview_interpretation_panel_result.py

This is a focused preview for the terminal control-panel UX before wiring it
into ``AgentResultWidget``.  It exercises the intended key model:

- Up/Down moves the cursor.
- ``+`` / ``=`` increments the highlighted number parameter.
- ``-`` decrements the highlighted number parameter.
- Space applies the highlighted choice or pending number value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Static

from tabulaflow.app.theme import ACCENT, ACCENT_DIM, FOCUS_SURFACE, KEY_HINT, KEY_HINT_DIM
from tabulaflow.core.outputs import ChoiceOption, ChoiceParameter, NumberParameter, ParameterSpec, SelectionValue, parameter_default

_SLIDER_WIDTH = 16
_SLIDER_THUMB = "◆"


@dataclass(frozen=True)
class _CursorItem:
    parameter_index: int
    choice_index: int | None = None


class TerminalControlPanelPreview(Static, can_focus=True):
    """Standalone preview of the proposed terminal answer-control panel."""

    def __init__(self, parameters: list[ParameterSpec]) -> None:
        super().__init__(classes="control-preview")
        self._parameters = parameters
        self._cursor = 0
        self._pending_selection: dict[str, SelectionValue] = {
            parameter.id: parameter_default(parameter) for parameter in parameters
        }
        self._applied_selection: dict[str, SelectionValue] = dict(self._pending_selection)
        self._items = self._cursor_items()

    def on_mount(self) -> None:
        self.focus()
        self._refresh()

    def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            self._move(-1)
            event.stop()
        elif event.key == "down":
            self._move(1)
            event.stop()
        elif event.character in {"+", "="}:
            self._adjust_number(1)
            event.stop()
        elif event.character == "-":
            self._adjust_number(-1)
            event.stop()
        elif event.key == "space":
            self._apply_current()
            event.stop()

    def _cursor_items(self) -> list[_CursorItem]:
        items: list[_CursorItem] = []
        for parameter_index, parameter in enumerate(self._parameters):
            if isinstance(parameter, ChoiceParameter):
                items.extend(_CursorItem(parameter_index=parameter_index, choice_index=i) for i in range(len(parameter.choices)))
            elif isinstance(parameter, NumberParameter):
                items.append(_CursorItem(parameter_index=parameter_index))
        return items

    def _move(self, delta: int) -> None:
        if not self._items:
            return
        self._discard_current_number_draft()
        self._cursor = max(0, min(len(self._items) - 1, self._cursor + delta))
        self._refresh()

    def _current_item(self) -> _CursorItem | None:
        if not self._items:
            return None
        return self._items[self._cursor]

    def _adjust_number(self, direction: int) -> None:
        item = self._current_item()
        if item is None:
            return
        parameter = self._parameters[item.parameter_index]
        if not isinstance(parameter, NumberParameter):
            return
        current = float(self._pending_selection[parameter.id])
        self._pending_selection[parameter.id] = _next_number_value(parameter, current, direction)
        self._refresh()

    def _discard_current_number_draft(self) -> None:
        item = self._current_item()
        if item is None:
            return
        parameter = self._parameters[item.parameter_index]
        if isinstance(parameter, NumberParameter):
            self._pending_selection[parameter.id] = self._applied_selection[parameter.id]

    def _apply_current(self) -> None:
        item = self._current_item()
        if item is None:
            return
        parameter = self._parameters[item.parameter_index]
        if isinstance(parameter, ChoiceParameter):
            assert item.choice_index is not None
            self._applied_selection[parameter.id] = parameter.choices[item.choice_index].id
        elif isinstance(parameter, NumberParameter):
            self._applied_selection[parameter.id] = self._pending_selection[parameter.id]
        self._refresh()

    def _refresh(self) -> None:
        accent = ACCENT if self.has_focus else ACCENT_DIM
        key_hint = KEY_HINT if self.has_focus else KEY_HINT_DIM
        text = Text(no_wrap=False)
        text.append("Refine interpretation", style="bold dim")
        text.append("    ")
        text.append("↑↓", style=key_hint)
        text.append(" Move · ", style="dim")
        text.append("+/-", style=key_hint)
        text.append(" Adjust number · ", style="dim")
        text.append("Space", style=key_hint)
        text.append(" Apply", style="dim")
        text.append("\n\n")

        item_index = 0
        for parameter_index, parameter in enumerate(self._parameters):
            if parameter_index:
                text.append("\n")
            text.append(parameter.label, style=Style(bold=True))
            text.append("\n")
            if isinstance(parameter, ChoiceParameter):
                for choice_index, choice in enumerate(parameter.choices):
                    is_cursor = self._cursor == item_index
                    is_applied = self._applied_selection.get(parameter.id) == choice.id
                    self._append_option_line(text, choice.label, is_cursor=is_cursor, is_applied=is_applied, accent=accent, key_hint=key_hint)
                    item_index += 1
            elif isinstance(parameter, NumberParameter):
                is_cursor = self._cursor == item_index
                pending = self._pending_selection[parameter.id]
                applied = self._applied_selection.get(parameter.id)
                self._append_option_line(
                    text,
                    f"{_slider_text(parameter, float(pending))} {_format_number(pending, parameter.unit)}",
                    is_cursor=is_cursor,
                    is_applied=pending == applied,
                    accent=accent,
                    key_hint=key_hint,
                    show_applied_marker=False,
                )
                item_index += 1

        text.append("\n")
        text.append("Applied selection: ", style="dim")
        text.append(str(self._applied_selection), style="bold")
        self.update(text)

    @staticmethod
    def _append_option_line(
        text: Text,
        label: str,
        *,
        is_cursor: bool,
        is_applied: bool,
        accent: str,
        key_hint: str,
        show_applied_marker: bool = True,
    ) -> None:
        text.append("  ")
        text.append("❯ " if is_cursor else "  ", style=key_hint if is_cursor else "")
        if show_applied_marker:
            text.append("● " if is_applied else "  ", style=accent if is_applied else "")
        if is_applied:
            style = Style(bold=True, color=accent)
        elif is_cursor:
            style = Style(bold=True)
        else:
            style = Style()
        text.append(label, style=style)
        text.append("\n")


def _is_int_like(value: float) -> bool:
    return float(value).is_integer()


def _next_number_value(parameter: NumberParameter, current: float, direction: int) -> int | float:
    step = float(parameter.step)
    min_value = float(parameter.min)
    max_value = float(parameter.max)
    max_index = max(0, math.floor((max_value - min_value) / step + 1e-9))
    current_index = round((current - min_value) / step)
    next_index = max(0, min(max_index, current_index + direction))
    return _coerce_number_value(parameter, min_value + next_index * step)


def _coerce_number_value(parameter: NumberParameter, value: float) -> int | float:
    if _is_int_like(parameter.min) and _is_int_like(parameter.max) and _is_int_like(parameter.step):
        return int(round(value))
    return value


def _format_number(value: object, unit: str | None) -> str:
    number = float(value) if isinstance(value, int | float) else 0.0
    text = f"{number:g}"
    return f"{text} {unit}" if unit else text


def _slider_text(parameter: NumberParameter, value: float, width: int = _SLIDER_WIDTH) -> str:
    if parameter.max <= parameter.min:
        filled = 0
    else:
        filled = round((value - parameter.min) / (parameter.max - parameter.min) * width)
    filled = max(0, min(width, filled))
    return "[" + "━" * filled + _SLIDER_THUMB + "─" * (width - filled) + "]"


def _parameters() -> list[ParameterSpec]:
    return [
        ChoiceParameter(
            id="metric",
            label="Metric",
            choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="orders", label="Orders")],
        ),
        ChoiceParameter(
            id="period",
            label="Period",
            choices=[ChoiceOption(id="q2", label="Q2"), ChoiceOption(id="q3", label="Q3")],
        ),
        NumberParameter(id="min_value", label="Minimum value", min=0, max=140, step=0.1, default=60, unit="USD"),
    ]


class InterpretationPanelResultPreview(App[None]):
    CSS = """
    Screen {
        background: $surface;
    }

    #preview-root {
        padding: 1 2;
    }

    .control-preview {
        border: round #6a737d;
        padding: 1 2;
        margin: 1 0;
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
            Static("Terminal answer-control preview", classes="dim"),
            Static("Use ↑/↓ to move, +/- to edit the number, Space to apply, q to quit.", classes="dim"),
            TerminalControlPanelPreview(_parameters()),
            id="preview-root",
        )
        yield Input(id="input-bar")


if __name__ == "__main__":
    InterpretationPanelResultPreview().run()
