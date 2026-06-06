"""The agent result widget — the interactive table / chart / query result card
shown inline in the chat stream (pushes the browser screens on demand).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text

from textual.binding import Binding
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from tabulaflow.app.display import DATA_PREVIEW_MAX_ROWS
from tabulaflow.app.theme import ACCENT, ACCENT_DIM, KEY_HINT, KEY_HINT_DIM
from tabulaflow.app.screens import ChartBrowserScreen, DataBrowserScreen, QueryBrowserScreen


if TYPE_CHECKING:
    import pandas as pd

    from tabulaflow.chat import ChatResult
    from tabulaflow.app.display import RecordGroup, ViewItem


# ---------------------------------------------------------------------------
# Agent result widget with interactive tabs
# ---------------------------------------------------------------------------


class AgentResultWidget(Widget):
    """Displays an agent result with two-level tab switching.

    Top bar: records (shown when there is more than one record).
    Bottom bar: view kinds (Chart / Data / Query) for the selected record.
    """

    DEFAULT_CSS = """
    AgentResultWidget {
        padding: 1 1;
        margin: 1 4 0 1;
        height: auto;
        background: $surface;
    }

    AgentResultWidget.-focused {
        background: $focus-surface;
    }

    AgentResultWidget .top-bar-row {
        layout: horizontal;
        height: auto;
        margin: 0 0 1 0;
    }

    AgentResultWidget .record-bar {
        width: 1fr;
        height: auto;
        overflow-x: hidden;
        margin: 0 4 0 0;
    }

    AgentResultWidget .view-stepper {
        width: auto;
        height: auto;
    }

    AgentResultWidget .bottom-hint {
        height: auto;
    }

    """

    current_record: reactive[int] = reactive(0, init=False)
    current_view: reactive[int] = reactive(0, init=False)

    def __init__(
        self,
        result: ChatResult,
        width: int = 80,
        query_history: object | None = None,
    ) -> None:
        super().__init__()
        from tabulaflow.app.display import build_result_views
        from tabulaflow.toolhub.query_history import QueryHistory

        self._records = build_result_views(result, width)
        self._query_history: QueryHistory | None = query_history if isinstance(query_history, QueryHistory) else None
        self._content = Static(id="result-content")
        self._mounted = False
        self._record_bar_widget: Static | None = None
        self._view_stepper_widget: Static | None = None
        self._bottom_hint_widget: Static | None = None
        # Record hit areas: (record_index, col_start, col_end, row) relative
        # to the record bar widget. Pills wrap across multiple rows when they
        # don't all fit on a single line.
        self._record_hit_areas: list[tuple[int, int, int, int]] = []
        # View hit areas: (target, col_start, col_end) relative to the view
        # stepper widget. Target is "prev" or "next".
        self._view_hit_areas: list[tuple[str, int, int]] = []

    @property
    def _has_top_bar(self) -> bool:
        """Top bar exists whenever the result has any displayable records."""
        return bool(self._records)

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal

        if self._has_top_bar:
            self._record_bar_widget = Static(classes="record-bar")
            self._view_stepper_widget = Static(classes="view-stepper")
            yield Horizontal(
                self._record_bar_widget,
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

    def on_resize(self) -> None:
        if self._record_bar_widget is not None:
            self._update_record_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()

    def watch_current_record(self) -> None:
        if not self._mounted:
            return
        # Clamp current_view to the new record's view count; setting it will
        # trigger watch_current_view which calls _refresh_all.
        rec = self._current_record_or_none()
        if rec is not None and self.current_view >= len(rec.views):
            self.current_view = max(0, len(rec.views) - 1)
            return
        self._refresh_all()

    def watch_current_view(self) -> None:
        if not self._mounted:
            return
        self._refresh_all()

    def watch_has_focus(self, has_focus: bool) -> None:
        """Re-render styled elements when focus changes.

        The record pill, view stepper chevrons / kind label, and the
        ``KEY_HINT`` glyphs use mint accents when this widget is focused
        and a muted gray when it isn't — the focus indication emerges
        from element saturation rather than added chrome (no border,
        stripe, or glyph). Modern app pattern (Linear, VS Code panels).
        """
        self.set_class(has_focus, "-focused")
        if not self._mounted:
            return
        if self._record_bar_widget is not None:
            self._update_record_bar()
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
        self._update_content()
        if self._record_bar_widget is not None:
            self._update_record_bar()
        if self._view_stepper_widget is not None:
            self._update_view_stepper()
        if self._bottom_hint_widget is not None:
            self._update_bottom_hint()
        if self._is_last_chat_item():
            chat_log = self.app.query_one("#chat-log")
            chat_log.scroll_end(animate=False)

    def _is_last_chat_item(self) -> bool:
        """Return True when this widget is the last chat log child."""
        try:
            chat_log = self.app.query_one("#chat-log")
        except Exception:
            return False
        children = list(chat_log.children)
        return bool(children) and children[-1] is self

    def _current_record_or_none(self) -> "RecordGroup | None":
        if not self._records:
            return None
        idx = min(self.current_record, len(self._records) - 1)
        return self._records[idx]

    def _current_view_or_none(self) -> "ViewItem | None":
        rec = self._current_record_or_none()
        if rec is None or not rec.views:
            return None
        idx = min(self.current_view, len(rec.views) - 1)
        return rec.views[idx]

    def _update_record_bar(self) -> None:
        """Render record pills left-anchored, wrapping across multiple lines.

        All pills are shown; when the row fills, subsequent pills wrap to a
        new line. When more than one record exists, a ``·  ←/→ Switch record``
        hint is appended inline after the final pill if it fits on the last
        line, otherwise on a new line below.

        Hit areas are stored as ``(record_index, col_start, col_end, row)``
        relative to ``self._record_bar_widget`` so the click handler can test
        ``event.x``/``event.y`` directly without worrying about the enclosing
        layout.
        """
        from rich.style import Style

        if self._record_bar_widget is None:
            return

        available_width = self._record_bar_widget.size.width or 80
        record_interactive = len(self._records) > 1

        HINT_SEP = " · "
        HINT_KEY = "←/→"
        HINT_TEXT = " Switch record"
        hint_width = len(HINT_SEP) + len(HINT_KEY) + len(HINT_TEXT) if record_interactive else 0

        SEP = 1  # space between pills on the same row
        dim_style = Style(dim=True)

        line = Text(no_wrap=True, overflow="crop")
        self._record_hit_areas = []
        row = 0
        col = 0

        for rec_idx, r in enumerate(self._records):
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
                if rec_idx == self.current_record
                else Style(dim=True)
            )
            line.append_text(Text(pill, style=pill_style))
            col += pill_width
            self._record_hit_areas.append((rec_idx, col_start, col, row))

        if record_interactive:
            if col + hint_width > available_width:
                line.append("\n")
            line.append_text(Text(HINT_SEP, style=dim_style))
            line.append_text(Text("←", style=self._focus_key_hint))
            line.append_text(Text("/", style="dim"))
            line.append_text(Text("→", style=self._focus_key_hint))
            line.append_text(Text(HINT_TEXT, style="dim"))

        self._record_bar_widget.update(line)

    def _update_view_stepper(self) -> None:
        """Render the view stepper with an optional switch-view hint on its left.

        Hit areas are stored relative to ``self._view_stepper_widget``.
        """
        from rich.style import Style

        from tabulaflow.app.display import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

        if self._view_stepper_widget is None:
            return

        rec = self._current_record_or_none()
        has_views = rec is not None and bool(rec.views)
        view_interactive = rec is not None and len(rec.views) > 1

        self._view_hit_areas = []
        if not has_views:
            self._view_stepper_widget.update(Text(""))
            return
        assert rec is not None

        chevron_style = Style(bold=True, color=self._focus_accent)
        label_style = Style(bold=True, color=self._focus_accent)
        dim_sep_style = Style(dim=True)

        cur_kind = rec.views[min(self.current_view, len(rec.views) - 1)].kind
        max_kind_width = max(len(k) for k in (VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY))
        pad = max_kind_width - len(cur_kind)

        line = Text(no_wrap=True)
        col = 0

        # Always reserve the Switch view hint width so the stepper's total
        # width stays constant across records. If we rendered this block only
        # when the record has multiple views, clicking a single-view record
        # would shrink the stepper and — since it shares a row with the
        # ``width: 1fr`` record bar — cause the record pills to re-wrap.
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
        navigate to a record (↑↓), then inspect it (Enter).
        """
        if self._bottom_hint_widget is None:
            return
        view = self._current_view_or_none()
        if view is None:
            self._bottom_hint_widget.update(Text(""))
            return

        hint = Text(no_wrap=True)
        # ↑↓ and Enter only do anything when this widget is focused, so
        # both follow focus-state dimming (bright when focused, dim when
        # not) — the "way in" comes from the docked bottom-bar hint, not
        # from the widget itself.
        hint.append("↑↓", style=self._focus_key_hint)
        hint.append(" Prev/Next result    ", style="dim")
        hint.append("↵", style=self._focus_key_hint)
        hint.append(" Inspect", style="dim")

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
        from tabulaflow.app.display import VIEW_KIND_DATA

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

        if self._record_bar_widget is not None and event.widget is self._record_bar_widget:
            for rec_idx, col_start, col_end, row in self._record_hit_areas:
                if row == event.y and col_start <= event.x < col_end:
                    if rec_idx != self.current_record:
                        self._switch_record(rec_idx)
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
            from tabulaflow.app.display import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

            if view.kind == VIEW_KIND_CHART and self._is_chart_region_click(view, event.x, event.y):
                self.run_worker(self.action_open_full_screen(), exclusive=True)
                return
            if view.kind == VIEW_KIND_DATA and self._is_table_region_click(view, event.x, event.y):
                self.run_worker(self.action_open_full_screen(), exclusive=True)
                return
            if view.kind == VIEW_KIND_QUERY:
                self.run_worker(self.action_open_full_screen(), exclusive=True)
                return

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

    def _switch_record(self, new_idx: int) -> None:
        """Change the active record, preserving the current view kind if possible."""
        if not self._records or new_idx == self.current_record:
            return
        current_view = self._current_view_or_none()
        target_kind = current_view.kind if current_view is not None else None
        new_rec = self._records[new_idx]
        new_view_idx = 0
        if target_kind is not None:
            for i, v in enumerate(new_rec.views):
                if v.kind == target_kind:
                    new_view_idx = i
                    break
        self.current_record = new_idx
        self.current_view = new_view_idx

    def action_next_view(self) -> None:
        rec = self._current_record_or_none()
        if rec is not None and len(rec.views) > 1:
            self.current_view = (self.current_view + 1) % len(rec.views)

    def action_prev_view(self) -> None:
        rec = self._current_record_or_none()
        if rec is not None and len(rec.views) > 1:
            self.current_view = (self.current_view - 1) % len(rec.views)

    def action_next_record(self) -> None:
        if len(self._records) > 1:
            self._switch_record((self.current_record + 1) % len(self._records))

    def action_prev_record(self) -> None:
        if len(self._records) > 1:
            self._switch_record((self.current_record - 1) % len(self._records))

    can_focus = True

    BINDINGS = [
        ("right_square_bracket", "next_view", "Next view"),
        ("left_square_bracket", "prev_view", "Previous view"),
        ("right", "next_record", "Next record"),
        ("left", "prev_record", "Previous record"),
        ("enter", "open_full_screen", "Full screen"),
        # ``priority=True`` so these beat ``VerticalScroll``'s own priority
        # up/down bindings (which would otherwise scroll the chat log
        # instead of moving between focused result widgets).
        Binding("up", "focus_prev_result", "Previous result", priority=True),
        Binding("down", "focus_next_result", "Next result", priority=True),
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
        from tabulaflow.app.display import VIEW_KIND_CHART, VIEW_KIND_DATA, VIEW_KIND_QUERY

        rec = self._current_record_or_none()
        view = self._current_view_or_none()
        if rec is None or view is None:
            return
        title = f"{view.kind} ({rec.label})"

        if view.kind == VIEW_KIND_CHART and view.chart_spec is not None:
            df = await self._fetch_df(rec.record_id)
            if df is not None:
                self.app.push_screen(ChartBrowserScreen(title=title, df=df, vegalite_spec=view.chart_spec))
            return
        if view.kind == VIEW_KIND_DATA:
            df = await self._fetch_df(rec.record_id)
            if df is not None:
                self.app.push_screen(DataBrowserScreen(title=title, df=df))
            return
        if view.kind == VIEW_KIND_QUERY and view.query is not None:
            query, lexer = view.query
            self.app.push_screen(QueryBrowserScreen(title=title, query=query, lexer=lexer))

    async def _fetch_df(self, record_id: str) -> pd.DataFrame | None:
        """Fetch a DataFrame from QueryHistory, hydrating from DuckDB if needed."""
        if self._query_history is None:
            return None
        try:
            record = await self._query_history.get(record_id)
        except (KeyError, ValueError):
            return None
        if record.pred_query.exec_result is None:
            return None
        return record.pred_query.exec_result.df
