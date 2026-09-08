"""Interactive artifact cards and output-parameter controls."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.text import Text

from textual import events
from textual.binding import Binding
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from tabulaflow.app.tui.rendering import DATA_PREVIEW_MAX_ROWS, build_resolved_output_card_views
from tabulaflow.output.specs import ChoiceParameter, NumberParameter, SelectionValue
from tabulaflow.output.store import ArtifactSourceResolutionError
from tabulaflow.app.theme import ACCENT
from tabulaflow.app.tui.widgets.chat_log import ChatLog
from tabulaflow.app.tui.theme import (
    ACCENT_DIM,
    KEY_HINT,
    KEY_HINT_DIM,
)
from tabulaflow.app.tui.screens.results import ChartBrowserScreen, DataBrowserScreen, QueryBrowserScreen
from tabulaflow.app.turn import TurnOutput

if TYPE_CHECKING:
    import pandas as pd

    from tabulaflow.agents.chat import ChatResult
    from tabulaflow.app.tui.rendering import CardGroup, ViewItem


@dataclass(frozen=True)
class _ControlCursorItem:
    parameter_index: int
    choice_index: int | None = None


_SLIDER_WIDTH = 16
_SLIDER_THUMB = "◆"


def _is_int_like(value: float) -> bool:
    return float(value).is_integer()


def _next_number_parameter_value(parameter: NumberParameter, current: float, direction: int) -> int | float:
    step = float(parameter.step)
    min_value = float(parameter.min)
    max_value = float(parameter.max)
    max_index = max(0, math.floor((max_value - min_value) / step + 1e-9))
    current_index = round((current - min_value) / step)
    next_index = max(0, min(max_index, current_index + direction))
    return _coerce_number_parameter_value(parameter, min_value + next_index * step)


def _coerce_number_parameter_value(parameter: NumberParameter, value: float) -> int | float:
    if _is_int_like(parameter.min) and _is_int_like(parameter.max) and _is_int_like(parameter.step):
        return int(round(value))
    return value


def _format_number_parameter_value(value: object, unit: str | None) -> str:
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


class AgentResultWidget(Widget):
    """Displays an agent result with two-level tab switching.

    Top bar: cards (shown when there is more than one card).
    Bottom bar: view kinds (Chart / Data / Query) for the selected card.
    Each card keeps its own selected view; stepping the view on one
    card never affects what another card shows.
    """

    DEFAULT_CSS = """
    AgentResultWidget {
        padding: 1 1;
        margin: 1 2 0 1;
        height: auto;
        background: $surface;
    }

    AgentResultWidget.-focused {
        background: $focus-surface;
    }

    AgentResultWidget.-has-panel {
        padding: 0 1 1 1;
    }

    AgentResultWidget .top-bar-row {
        layout: horizontal;
        height: auto;
        margin: 0 0 1 0;
    }

    AgentResultWidget .card-bar {
        width: 1fr;
        height: auto;
        overflow-x: hidden;
        margin: 0 4 0 0;
    }

    AgentResultWidget .view-stepper {
        width: auto;
        height: auto;
    }

    AgentResultWidget .interpretation-panel {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 2;
        border: round #6a737d;
    }

    AgentResultWidget .interpretation-title {
        height: auto;
        margin: 0 0 1 0;
    }

    AgentResultWidget .interpretation-content {
        height: auto;
    }

    AgentResultWidget .bottom-hint {
        height: auto;
    }

    """

    current_card: reactive[int] = reactive(0, init=False)

    def __init__(
        self,
        result: ChatResult,
        cards: Sequence["CardGroup"],
        width: int = 80,
        turn_output: TurnOutput | None = None,
    ) -> None:
        super().__init__()
        self._result = result
        self._width = width
        self._control_parameters = list(result.output.parameters)
        self._control_cursor_items = self._build_control_cursor_items()
        self._control_cursor_index_by_item = {item: index for index, item in enumerate(self._control_cursor_items)}
        self._has_answer_controls = bool(self._control_cursor_items)
        self.set_class(self._has_answer_controls, "-has-panel")
        self._applied_selection: dict[str, SelectionValue] = dict(result.output.default_selection)
        self._pending_selection: dict[str, SelectionValue] = dict(self._applied_selection)
        self._interpretation_cursor = 0
        self._cards = list(cards)
        # Selected view index per card; every card has at least one view.
        self._view_indices: list[int] = [0] * len(self._cards)
        self._turn_output = turn_output
        self._interpretation_title: Static | None = None
        self._interpretation_content: Static | None = None
        self._content = Static(id="result-content")
        self._mounted = False
        self._card_bar_widget: Static | None = None
        self._view_stepper_widget: Static | None = None
        self._bottom_hint_widget: Static | None = None
        # Card hit areas: (card_index, col_start, col_end, row) relative
        # to the card bar widget. Pills wrap across multiple rows when they
        # don't all fit on a single line.
        self._card_hit_areas: list[tuple[int, int, int, int]] = []
        # View hit areas: (target, col_start, col_end) relative to the view
        # stepper widget. Target is "prev" or "next".
        self._view_hit_areas: list[tuple[str, int, int]] = []
        # Interpretation control hit areas: (cursor_item_index, row) relative to
        # the interpretation-content widget.
        self._control_hit_areas: list[tuple[int, int]] = []

    @property
    def _has_top_bar(self) -> bool:
        """Top bar exists whenever the result has any displayable cards."""
        return bool(self._cards)

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, Vertical

        if self._has_answer_controls:
            self._interpretation_title = Static(classes="interpretation-title")
            self._interpretation_content = Static(classes="interpretation-content")
            yield Vertical(
                self._interpretation_title,
                self._interpretation_content,
                classes="interpretation-panel",
            )
        if self._has_top_bar:
            self._card_bar_widget = Static(classes="card-bar")
            self._view_stepper_widget = Static(classes="view-stepper")
            yield Horizontal(
                self._card_bar_widget,
                self._view_stepper_widget,
                classes="top-bar-row",
            )
        yield self._content
        if self._has_top_bar:
            self._bottom_hint_widget = Static(classes="bottom-hint")
            yield self._bottom_hint_widget

    def on_mount(self) -> None:
        self._mounted = True
        self._refresh_all()
        # The first refresh can run before the child widgets have final widths;
        # refresh once more after layout so the interpretation header/separator
        # don't render with width 0 until the first keypress.
        self.call_after_refresh(self._refresh_all)

    def on_resize(self) -> None:
        if self._card_bar_widget is not None:
            self._update_card_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()

    def watch_current_card(self) -> None:
        if not self._mounted:
            return
        self._refresh_all()

    def watch_has_focus(self, has_focus: bool) -> None:
        """Re-render styled elements when focus changes.

        The card pill, view stepper chevrons / kind label, and the
        ``KEY_HINT`` glyphs use mint accents when this widget is focused
        and a muted gray when it isn't — the focus indication emerges
        from element saturation rather than added chrome (no border,
        stripe, or glyph). Modern app pattern (Linear, VS Code panels).
        """
        self.set_class(has_focus, "-focused")
        if not self._mounted:
            return
        if self._card_bar_widget is not None:
            self._update_card_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()

    @property
    def _focus_accent(self) -> str:
        return ACCENT if self.has_focus else ACCENT_DIM

    @property
    def _focus_key_hint(self) -> str:
        return KEY_HINT if self.has_focus else KEY_HINT_DIM

    def _refresh_all(self) -> None:
        if self._has_answer_controls:
            self._update_interpretation_panel()
        self._update_content()
        if self._card_bar_widget is not None:
            self._update_card_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()
        self.app.query_one("#chat-log", ChatLog).follow_new_content()

    def _rebuild_cards_for_selection(self, cards: list["CardGroup"]) -> None:
        old_indices = self._view_indices
        old_card = self.current_card
        self._cards = cards
        self.current_card = min(old_card, max(len(self._cards) - 1, 0))
        self._view_indices = [0] * len(self._cards)
        for i, old in enumerate(old_indices[: len(self._cards)]):
            if self._cards[i].views:
                self._view_indices[i] = min(old, len(self._cards[i].views) - 1)

    async def _resolve_cards_for_selection(self, selection: dict[str, "SelectionValue"]) -> None:
        if self._turn_output is None:
            return
        resolved_output = await self._turn_output.resolve(selection)
        cards = build_resolved_output_card_views(resolved_output, self._width)
        self._rebuild_cards_for_selection(cards)
        self._refresh_all()

    def _current_card_or_none(self) -> "CardGroup | None":
        if not self._cards:
            return None
        idx = min(self.current_card, len(self._cards) - 1)
        return self._cards[idx]

    def _current_view_or_none(self) -> "ViewItem | None":
        card = self._current_card_or_none()
        if card is None or not card.views:
            return None
        return card.views[self._view_indices[min(self.current_card, len(self._cards) - 1)]]

    def _build_control_cursor_items(self) -> list[_ControlCursorItem]:
        items: list[_ControlCursorItem] = []
        for parameter_index, parameter in enumerate(self._control_parameters):
            if isinstance(parameter, ChoiceParameter):
                items.extend(
                    _ControlCursorItem(parameter_index=parameter_index, choice_index=choice_index)
                    for choice_index in range(len(parameter.choices))
                )
            elif isinstance(parameter, NumberParameter):
                items.append(_ControlCursorItem(parameter_index=parameter_index))
        return items

    def _choice_count(self) -> int:
        return sum(
            len(parameter.choices) for parameter in self._control_parameters if isinstance(parameter, ChoiceParameter)
        )

    def _current_control_item(self) -> _ControlCursorItem | None:
        if not self._control_cursor_items:
            return None
        return self._control_cursor_items[self._interpretation_cursor]

    def _control_item_index(self, item: _ControlCursorItem) -> int:
        return self._control_cursor_index_by_item[item]

    def _move_interpretation_cursor(self, delta: int) -> None:
        max_cursor = len(self._control_cursor_items) - 1
        if max_cursor < 0:
            return
        self._discard_current_number_draft()
        self._interpretation_cursor = max(0, min(max_cursor, self._interpretation_cursor + delta))
        self._refresh_all()

    def _adjust_number_control(self, direction: int) -> None:
        item = self._current_control_item()
        if item is None:
            return
        parameter = self._control_parameters[item.parameter_index]
        if not isinstance(parameter, NumberParameter):
            return
        current = float(self._pending_selection[parameter.id])
        self._pending_selection[parameter.id] = _next_number_parameter_value(parameter, current, direction)
        self._refresh_all()

    def _discard_current_number_draft(self) -> None:
        item = self._current_control_item()
        if item is None:
            return
        parameter = self._control_parameters[item.parameter_index]
        if isinstance(parameter, NumberParameter):
            self._pending_selection[parameter.id] = self._applied_selection[parameter.id]

    def _apply_interpretation_cursor(self) -> None:
        item = self._current_control_item()
        if item is None:
            return
        parameter = self._control_parameters[item.parameter_index]
        value: SelectionValue
        if isinstance(parameter, ChoiceParameter):
            assert item.choice_index is not None
            value = parameter.choices[item.choice_index].id
        elif isinstance(parameter, NumberParameter):
            value = self._pending_selection[parameter.id]
        else:
            return
        if self._applied_selection.get(parameter.id) == value:
            return
        self._applied_selection = {**self._applied_selection, parameter.id: value}
        self._pending_selection = {**self._pending_selection, parameter.id: value}
        if self._turn_output is not None:
            self.run_worker(self._resolve_cards_for_selection(dict(self._applied_selection)), exclusive=True)
        else:
            self._refresh_all()

    def _update_interpretation_panel(self) -> None:
        from rich.style import Style

        if not self._has_answer_controls:
            return
        if self._interpretation_title is None or self._interpretation_content is None:
            return

        available = self._interpretation_title.size.width or 80
        hint = Text(no_wrap=True)
        hint.append("↑↓", style=self._focus_key_hint)
        hint.append(" Move · ", style="dim")
        hint.append("+/-", style=self._focus_key_hint)
        hint.append(" Adjust · ", style="dim")
        hint.append("Space", style=self._focus_key_hint)
        hint.append(" Apply", style="dim")
        title = Text("Refine interpretation", style="bold dim")
        title_line = Text(no_wrap=True, overflow="crop")
        title_line.append_text(title)
        title_line.append(" " * max(1, available - title.cell_len - hint.cell_len))
        title_line.append_text(hint)
        self._interpretation_title.update(title_line)

        parameters = self._control_parameters
        rows: list[Text] = []
        self._control_hit_areas = []
        if not parameters:
            self._interpretation_content.update(Text("No supported answer controls yet.", style="dim"))
            return
        cursor_item = self._current_control_item()
        row = 0
        for parameter_index, parameter in enumerate(parameters):
            if rows:
                rows.append(Text(""))
                row += 1
            rows.append(Text(parameter.label, style=Style(bold=True)))
            row += 1
            if isinstance(parameter, ChoiceParameter):
                for choice_idx, choice in enumerate(parameter.choices):
                    item = _ControlCursorItem(parameter_index=parameter_index, choice_index=choice_idx)
                    is_applied = self._applied_selection.get(parameter.id) == choice.id
                    rows.append(
                        self._control_line(
                            choice.label,
                            is_cursor=cursor_item == item,
                            is_applied=is_applied,
                            show_applied_marker=True,
                        )
                    )
                    self._control_hit_areas.append((self._control_item_index(item), row))
                    row += 1
            elif isinstance(parameter, NumberParameter):
                item = _ControlCursorItem(parameter_index=parameter_index)
                pending = self._pending_selection[parameter.id]
                applied = self._applied_selection.get(parameter.id)
                rows.append(
                    self._control_line(
                        f"{_slider_text(parameter, float(pending))} {_format_number_parameter_value(pending, parameter.unit)}",
                        is_cursor=cursor_item == item,
                        is_applied=pending == applied,
                        show_applied_marker=False,
                    )
                )
                self._control_hit_areas.append((self._control_item_index(item), row))
                row += 1
        self._interpretation_content.update(Text("\n").join(rows))

    def _control_line(self, label: str, *, is_cursor: bool, is_applied: bool, show_applied_marker: bool) -> Text:
        from rich.style import Style

        line = Text()
        line.append("  ")
        line.append(
            "❯ " if is_cursor else "  ",
            style=KEY_HINT if is_cursor and self.has_focus else KEY_HINT_DIM if is_cursor else "",
        )
        if show_applied_marker:
            line.append("● " if is_applied else "  ", style=self._focus_accent if is_applied else "")
        if is_applied:
            label_style = Style(bold=True, color=self._focus_accent)
        elif is_cursor:
            label_style = Style(bold=True)
        else:
            label_style = Style()
        line.append(label, style=label_style)
        return line

    def _update_card_bar(self) -> None:
        """Render card pills left-anchored, wrapping across multiple lines.

        All pills are shown; when the row fills, subsequent pills wrap to a
        new line. When more than one card exists, a ``·  ←/→ Switch card``
        hint is appended inline after the final pill if it fits on the last
        line, otherwise on a new line below.

        Hit areas are stored as ``(card_index, col_start, col_end, row)``
        relative to ``self._card_bar_widget`` so the click handler can test
        ``event.x``/``event.y`` directly without worrying about the enclosing
        layout.
        """
        from rich.style import Style

        if self._card_bar_widget is None:
            return

        available_width = self._card_bar_widget.size.width or 80
        card_interactive = len(self._cards) > 1

        HINT_SEP = " · "
        HINT_KEY = "←/→"
        HINT_TEXT = " Switch card"
        hint_width = len(HINT_SEP) + len(HINT_KEY) + len(HINT_TEXT) if card_interactive else 0

        SEP = 1  # space between pills on the same row
        dim_style = Style(dim=True)

        line = Text(no_wrap=True, overflow="crop")
        self._card_hit_areas = []
        row = 0
        col = 0

        for card_idx, r in enumerate(self._cards):
            pill = f" {r.label} "
            pill_width = len(pill)
            needed = pill_width + (SEP if col > 0 else 0)
            if col > 0 and col + needed > available_width:
                line.append("\n")
                row += 1
                col = 0
                needed = pill_width
            if col > 0:
                line.append(" ")
                col += 1
            col_start = col
            pill_style = (
                Style(bold=True, color="black", bgcolor=self._focus_accent)
                if card_idx == self.current_card
                else Style(dim=True)
            )
            line.append_text(Text(pill, style=pill_style))
            col += pill_width
            self._card_hit_areas.append((card_idx, col_start, col, row))

        if card_interactive:
            if col + hint_width > available_width:
                line.append("\n")
            line.append_text(Text(HINT_SEP, style=dim_style))
            line.append_text(Text("←", style=self._focus_key_hint))
            line.append_text(Text("/", style="dim"))
            line.append_text(Text("→", style=self._focus_key_hint))
            line.append_text(Text(HINT_TEXT, style="dim"))

        self._card_bar_widget.update(line)

    def _update_view_stepper(self) -> None:
        """Render the view stepper with an optional switch-view hint on its left.

        Hit areas are stored relative to ``self._view_stepper_widget``.
        """
        from rich.style import Style

        from tabulaflow.app.tui.rendering import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

        if self._view_stepper_widget is None:
            return

        card = self._current_card_or_none()
        has_views = card is not None and bool(card.views)
        view_interactive = card is not None and len(card.views) > 1

        self._view_hit_areas = []
        if not has_views:
            self._view_stepper_widget.update(Text(""))
            return
        assert card is not None

        chevron_style = Style(bold=True, color=self._focus_accent)
        label_style = Style(bold=True, color=self._focus_accent)
        dim_sep_style = Style(dim=True)

        cur_view = self._current_view_or_none()
        assert cur_view is not None
        cur_kind = cur_view.kind
        max_kind_width = max(len(k) for k in (VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY))
        pad = max_kind_width - len(cur_kind)

        line = Text(no_wrap=True)
        col = 0

        # Always reserve the Switch view hint width so the stepper's total
        # width stays constant across cards. If we rendered this block only
        # when the card has multiple views, clicking a single-view card
        # would shrink the stepper and — since it shares a row with the
        # ``width: 1fr`` card bar — cause the card pills to re-wrap.
        if view_interactive:
            line.append_text(Text("[", style=self._focus_key_hint))
            line.append_text(Text("/", style="dim"))
            line.append_text(Text("]", style=self._focus_key_hint))
            col += 3
            line.append_text(Text(" Switch view", style="dim"))
            col += len(" Switch view")
            line.append_text(Text(" · ", style=dim_sep_style))
            col += 3
        else:
            reserved = 3 + len(" Switch view") + 3
            line.append_text(Text(" " * reserved))
            col += reserved

        # Left-pad short kinds outside the stepper so the stepper itself stays
        # visually tight and its right edge stays pinned.
        if pad > 0:
            line.append_text(Text(" " * pad))
            col += pad

        prev_x = col
        if view_interactive:
            line.append_text(Text("◂", style=chevron_style))
        else:
            line.append_text(Text(" "))
        col += 1
        line.append_text(Text(" "))
        col += 1
        line.append_text(Text(cur_kind, style=label_style))
        col += len(cur_kind)
        line.append_text(Text(" "))
        col += 1
        next_x = col
        if view_interactive:
            line.append_text(Text("▸", style=chevron_style))
        else:
            line.append_text(Text(" "))
        col += 1

        if view_interactive:
            self._view_hit_areas.append(("prev", prev_x, prev_x + 1))
            self._view_hit_areas.append(("next", next_x, next_x + 1))

        self._view_stepper_widget.update(line)

    def _update_bottom_hint(self) -> None:
        """Render hint affordances below the preview.

        The hint cluster is right-aligned. For data views, the truncation
        caption ('showing N of M rows/cols') is left-aligned on the same
        line. Hints read left-to-right as the user's natural progression:
        navigate to a card (↑↓), then inspect it (Enter).
        """
        if self._bottom_hint_widget is None:
            return
        view = self._current_view_or_none()
        if view is None:
            self._bottom_hint_widget.update(Text(""))
            return

        hint = Text(no_wrap=True)
        if not self._has_answer_controls:
            # ↑↓ and Enter only do anything when this widget is focused, so
            # both follow focus-state dimming (bright when focused, dim when
            # not) — the "way in" comes from the docked bottom-bar hint, not
            # from the widget itself.
            hint.append("↑↓", style=self._focus_key_hint)
            hint.append(" Prev/Next result    ", style="dim")
            hint.append("↵", style=self._focus_key_hint)
            hint.append(" Inspect", style="dim")
        else:
            hint.append("↵", style=self._focus_key_hint)
            hint.append(" Inspect    ", style="dim")
            hint.append("Esc", style=self._focus_key_hint)
            hint.append(" Back to input", style="dim")

        caption = self._data_preview_caption(view)
        available = self._bottom_hint_widget.size.width or 0
        line = Text(no_wrap=True)
        if caption:
            line.append(caption, style="dim")
            pad = available - hint.cell_len - len(caption)
        else:
            pad = available - hint.cell_len
        line.append(" " * max(1, pad))
        line.append_text(hint)
        self._bottom_hint_widget.update(line)

    def _data_preview_caption(self, view: "ViewItem") -> str:
        """Return the truncation caption for a data view, or empty string."""
        from tabulaflow.app.tui.rendering import VIEW_KIND_DATA

        if view.kind != VIEW_KIND_DATA or view.data_shape is None:
            return ""
        num_rows, num_cols = view.data_shape
        shown_cols = view.shown_cols if view.shown_cols is not None else num_cols
        parts: list[str] = []
        if num_rows > DATA_PREVIEW_MAX_ROWS:
            parts.append(f"showing {DATA_PREVIEW_MAX_ROWS} of {num_rows} rows")
        if num_cols > shown_cols:
            parts.append(f"showing {shown_cols} of {num_cols} columns")
        return " | ".join(parts)

    def _update_content(self) -> None:
        view = self._current_view_or_none()
        if view is None:
            self._content.update(Text("No results to display.", style="dim"))
            return
        self._content.update(view.renderable)

    def on_click(self, event: object) -> None:
        """Handle clicks on tab labels and content regions."""
        from textual.events import Click

        assert isinstance(event, Click)

        if self._interpretation_content is not None and event.widget is self._interpretation_content:
            for item_idx, row in self._control_hit_areas:
                if row == event.y:
                    self._discard_current_number_draft()
                    self._interpretation_cursor = item_idx
                    item = self._current_control_item()
                    if item is not None and isinstance(self._control_parameters[item.parameter_index], ChoiceParameter):
                        self._apply_interpretation_cursor()
                    else:
                        self._refresh_all()
                    return
            return

        if self._card_bar_widget is not None and event.widget is self._card_bar_widget:
            for card_idx, col_start, col_end, row in self._card_hit_areas:
                if row == event.y and col_start <= event.x < col_end:
                    self.current_card = card_idx
                    return
            return

        if self._view_stepper_widget is not None and event.widget is self._view_stepper_widget:
            if event.y != 0:
                return
            for target, col_start, col_end in self._view_hit_areas:
                if col_start <= event.x < col_end:
                    if target == "prev":
                        self.action_prev_view()
                    elif target == "next":
                        self.action_next_view()
                    return
            return

        if event.widget is self._content:
            view = self._current_view_or_none()
            if view is None:
                return
            from tabulaflow.app.tui.rendering import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

            if view.kind == VIEW_KIND_CHART and self._is_chart_region_click(view, event.x, event.y):
                self.run_worker(self.action_open_full_screen(), exclusive=True)
                return
            if view.kind == VIEW_KIND_DATA and self._is_table_region_click(view, event.x, event.y):
                self.run_worker(self.action_open_full_screen(), exclusive=True)
                return
            if view.kind == VIEW_KIND_QUERY:
                self.run_worker(self.action_open_full_screen(), exclusive=True)
                return

    def on_key(self, event: events.Key) -> None:
        if not self._has_answer_controls:
            return
        if event.character in {"+", "="}:
            self._adjust_number_control(1)
            event.stop()
        elif event.character == "-":
            self._adjust_number_control(-1)
            event.stop()

    def _is_chart_region_click(self, view: "ViewItem", x: int, y: int) -> bool:
        """Return True when click lands within the rendered chart area."""
        if x < 0 or y < 0:
            return False
        options = self.app.console.options.update(width=max(1, self._content.size.width))
        measurement = self.app.console.measure(view.renderable, options=options)
        return bool(x < measurement.maximum)

    def _is_table_region_click(self, view: "ViewItem", x: int, y: int) -> bool:
        """Return True when click lands within the visible data-table preview area."""
        if x < 0 or y < 0:
            return False
        content_height = self._content.size.height
        if content_height <= 0:
            return False
        table_width = self._data_preview_table_width(view)
        if table_width <= 0 or x >= table_width:
            return False
        return y < content_height

    def _data_preview_table_width(self, view: "ViewItem") -> int:
        """Measure rendered width of the data preview table area."""
        options = self.app.console.options.update(width=max(1, self._content.size.width))
        measurement = self.app.console.measure(view.renderable, options=options)
        return int(measurement.maximum)

    def _step_view(self, delta: int) -> None:
        card = self._current_card_or_none()
        if card is not None and len(card.views) > 1:
            self._view_indices[self.current_card] = (self._view_indices[self.current_card] + delta) % len(card.views)
            self._refresh_all()

    def action_next_view(self) -> None:
        self._step_view(1)

    def action_prev_view(self) -> None:
        self._step_view(-1)

    def action_next_card(self) -> None:
        if len(self._cards) > 1:
            self.current_card = (self.current_card + 1) % len(self._cards)

    def action_prev_card(self) -> None:
        if len(self._cards) > 1:
            self.current_card = (self.current_card - 1) % len(self._cards)

    def action_result_enter(self) -> None:
        self.run_worker(self.action_open_full_screen(), exclusive=True)

    def action_apply_interpretation(self) -> None:
        if self._has_answer_controls:
            self._apply_interpretation_cursor()

    def action_result_up(self) -> None:
        if self._has_answer_controls:
            self._move_interpretation_cursor(-1)
        else:
            self.action_focus_prev_result()

    def action_result_down(self) -> None:
        if self._has_answer_controls:
            self._move_interpretation_cursor(1)
        else:
            self.action_focus_next_result()

    can_focus = True

    BINDINGS = [
        ("right_square_bracket", "next_view", "Next view"),
        ("left_square_bracket", "prev_view", "Previous view"),
        ("right", "next_card", "Next card"),
        ("left", "prev_card", "Previous card"),
        ("space", "apply_interpretation", "Apply interpretation"),
        ("enter", "result_enter", "Full screen"),
        # ``priority=True`` so these beat ``VerticalScroll``'s own priority
        # up/down bindings (which would otherwise scroll the chat log
        # instead of moving between focused result widgets).
        Binding("up", "result_up", "Move up", priority=True),
        Binding("down", "result_down", "Move down", priority=True),
        ("escape", "focus_input", "Back to input"),
    ]

    def action_focus_prev_result(self) -> None:
        """Focus the previous AgentResultWidget."""
        results = list(self.app.query(AgentResultWidget))
        try:
            idx = results.index(self)
        except ValueError:
            return
        if idx > 0:
            results[idx - 1].focus()
            results[idx - 1].scroll_visible()

    def action_focus_next_result(self) -> None:
        """Focus the next AgentResultWidget, or return to the input.

        When the user is on the newest result and presses ``down``, focus
        jumps back to the input bar — completing the "step back through
        history, step forward back to input" chain.
        """
        results = list(self.app.query(AgentResultWidget))
        try:
            idx = results.index(self)
        except ValueError:
            return
        if idx < len(results) - 1:
            results[idx + 1].focus()
            results[idx + 1].scroll_visible()
        else:
            self.app.query_one("#input-bar").focus()

    def action_focus_input(self) -> None:
        """Return focus to the input bar."""
        self.app.query_one("#input-bar").focus()

    async def action_open_full_screen(self) -> None:
        """Open full-screen viewer for the active Chart, Data, or Query tab."""
        from tabulaflow.app.tui.rendering import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

        card = self._current_card_or_none()
        view = self._current_view_or_none()
        if card is None or view is None:
            return
        title = f"{view.kind} ({card.label})"

        if view.kind == VIEW_KIND_CHART and view.chart_spec is not None:
            df = await self._fetch_df(card.result_id)
            if df is not None:
                self.app.push_screen(ChartBrowserScreen(title=title, df=df, vegalite_spec=view.chart_spec))
            return
        if view.kind == VIEW_KIND_DATA:
            df = await self._fetch_df(card.result_id)
            if df is not None:
                self.app.push_screen(DataBrowserScreen(title=title, df=df))
            return
        if view.kind == VIEW_KIND_QUERY and view.query is not None:
            query, lexer = view.query
            self.app.push_screen(QueryBrowserScreen(title=title, query=query, lexer=lexer))

    async def _fetch_df(self, result_id: str | None) -> pd.DataFrame | None:
        """Fetch a DataFrame from OutputStore, loading from DuckDB if needed."""
        if self._turn_output is None or result_id is None:
            return None
        try:
            result = await self._turn_output.output_store.get_result(result_id)
            return result.df
        except (ArtifactSourceResolutionError, ValueError):
            return None
