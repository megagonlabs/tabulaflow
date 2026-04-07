"""Textual widgets for the mintq TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Group
from rich.spinner import Spinner
from rich.text import Text
from pathlib import Path

from textual.binding import Binding
from textual.reactive import reactive
from textual.suggester import Suggester
from textual.timer import Timer
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import DataTable, Input, Static

from mintq.cli.display import (
    DATA_PREVIEW_MAX_COLUMNS,
    DATA_PREVIEW_MAX_ROWS,
    QUERY_PREVIEW_MAX_LINES,
)
from mintq.cli.theme import ACCENT, ACCENT_BOLD

if TYPE_CHECKING:
    import pandas as pd
    from rich.console import RenderableType

    from mintq.cli.agent import ChatResult


# ---------------------------------------------------------------------------
# Autocomplete suggester
# ---------------------------------------------------------------------------

_SLASH_COMMANDS = sorted(
    ["/help", "/exit", "/clear", "/connect", "/disconnect", "/databases", "/db", "/schema", "/model"]
)

_CONNECTABLE_EXTENSIONS = frozenset(
    {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".ndjson", ".sqlite", ".sqlite3", ".db", ".duckdb"}
)


class MintqSuggester(Suggester):
    """Autocomplete for slash commands and file paths after /connect."""

    def __init__(self) -> None:
        super().__init__(use_cache=False, case_sensitive=True)

    async def get_suggestion(self, value: str) -> str | None:
        if not value:
            return None

        # File path completion after "/connect "
        if value.startswith("/connect "):
            return self._suggest_connect_path(value)

        # Slash command completion
        if value.startswith("/"):
            return self._suggest_slash_command(value)

        return None

    def _suggest_slash_command(self, value: str) -> str | None:
        # Only complete the command portion (first word)
        parts = value.split(" ", 1)
        prefix = parts[0]
        for cmd in _SLASH_COMMANDS:
            if cmd.startswith(prefix) and cmd != prefix:
                # Return just the command if user hasn't typed args yet
                if len(parts) == 1:
                    return cmd
                return None
        return None

    def _suggest_connect_path(self, value: str) -> str | None:
        raw = value[len("/connect "):]
        if not raw:
            return None

        # Split to find the last token (supports multiple file args)
        tokens = raw.split()
        partial = tokens[-1] if tokens else raw
        prefix_part = value[: len(value) - len(partial)]

        p = Path(partial)
        if partial.endswith("/"):
            parent = p
            name_prefix = ""
        else:
            parent = p.parent
            name_prefix = p.name

        try:
            candidates = sorted(parent.iterdir())
        except (OSError, PermissionError):
            return None

        files: list[Path] = []
        dirs: list[Path] = []
        for entry in candidates:
            if not entry.name.startswith(name_prefix) or entry.name.startswith("."):
                continue
            if entry.name == name_prefix:
                continue
            if entry.is_dir():
                dirs.append(entry)
            elif entry.suffix.lower() in _CONNECTABLE_EXTENSIONS:
                files.append(entry)

        # Prioritize files over directories
        for entry in files:
            return f"{prefix_part}{entry}"
        for entry in dirs:
            return f"{prefix_part}{entry}/"
        return None


# ---------------------------------------------------------------------------
# Input with persistent history
# ---------------------------------------------------------------------------

_MAX_HISTORY_ENTRIES = 500


class HistoryInput(Input):
    """Input widget with file-backed command history (Up/Down arrows)."""

    BINDINGS = [
        Binding("up", "history_prev", "Previous command", priority=True),
        Binding("down", "history_next", "Next command", priority=True),
        Binding("tab", "accept_suggestion", "Accept suggestion", show=False),
    ]

    def __init__(self, history_path: Path, **kwargs: object) -> None:
        super().__init__(suggester=MintqSuggester(), **kwargs)  # type: ignore[arg-type]
        self._history_path = history_path
        self._history: list[str] = []
        self._history_index: int = -1
        self._saved_input: str = ""
        self._load_history()

    def _load_history(self) -> None:
        if self._history_path.is_file():
            lines = self._history_path.read_text(encoding="utf-8").splitlines()
            self._history = lines[-_MAX_HISTORY_ENTRIES:]

    def _save_history(self) -> None:
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._history_path.write_text(
            "\n".join(self._history[-_MAX_HISTORY_ENTRIES:]) + "\n",
            encoding="utf-8",
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Automatically add submitted text to history."""
        self._add_to_history(event.value)

    def _add_to_history(self, text: str) -> None:
        """Append a command to history and persist."""
        stripped = text.strip()
        if not stripped:
            return
        if self._history and self._history[-1] == stripped:
            return
        self._history.append(stripped)
        self._history_index = -1
        self._saved_input = ""
        self._save_history()

    def action_history_prev(self) -> None:
        if not self._history:
            return
        if self._history_index == -1:
            self._saved_input = self.value
            self._history_index = len(self._history) - 1
        elif self._history_index > 0:
            self._history_index -= 1
        else:
            return
        self.value = self._history[self._history_index]
        self.cursor_position = len(self.value)

    def action_history_next(self) -> None:
        if self._history_index == -1:
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.value = self._history[self._history_index]
        else:
            self._history_index = -1
            self.value = self._saved_input
        self.cursor_position = len(self.value)

    def action_accept_suggestion(self) -> None:
        """Accept the current autocomplete suggestion, if any."""
        if self._suggestion:
            self.value = self._suggestion
            self.cursor_position = len(self.value)


# ---------------------------------------------------------------------------
# Simple message widgets
# ---------------------------------------------------------------------------


class BannerWidget(Static):
    """Displays the welcome banner."""

    DEFAULT_CSS = """
    BannerWidget {
        margin: 1 0;
    }
    """

    def __init__(self, *, model: str) -> None:
        from mintq.cli.display import build_banner

        super().__init__(build_banner(model=model))


class UserMessage(Static):
    """Displays a user input message."""

    DEFAULT_CSS = """
    UserMessage {
        margin: 1 0 1 0;
        padding: 0 1;
    }
    """

    def __init__(self, text: str) -> None:
        line = Text()
        line.append("┃ ", style=ACCENT_BOLD)
        line.append(text)
        super().__init__(line)


class SystemMessage(Static):
    """Displays system/command output."""

    DEFAULT_CSS = """
    SystemMessage {
        padding: 0 1;
    }
    """


class SpinnerWidget(Widget):
    """Simple animated spinner with a label."""

    DEFAULT_CSS = """
    SpinnerWidget {
        padding: 0 1;
        height: auto;
    }
    """

    def __init__(self, label: str = "Loading...") -> None:
        super().__init__()
        self._spinner = Spinner("dots", text=Text(label, style="dim"), style=ACCENT)

    def on_mount(self) -> None:
        self.set_interval(1 / 12, self.refresh)

    def render(self) -> RenderableType:
        return self._spinner


# ---------------------------------------------------------------------------
# Agent progress widget (implements ProgressSink)
# ---------------------------------------------------------------------------


class AgentProgressWidget(Widget):
    """Shows agent execution progress with tool steps and streaming text."""

    DEFAULT_CSS = """
    AgentProgressWidget {
        padding: 0 1;
        height: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._steps: list[tuple[str, str, str]] = []
        self._streaming_text = ""
        self._raw_text = ""
        self._separator_seen = False
        self._status_text: str | None = "Thinking..."
        # Persistent spinner instances so animation state survives across renders.
        self._status_spinner = Spinner("dots", text=Text("Thinking...", style="dim"), style=ACCENT)
        self._tool_spinner = Spinner("dots", style="dim")
        self._tool_progress_pct: int | None = None
        self._frozen = False
        self._timer: Timer | None = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / 12, self.refresh)

    def render(self) -> RenderableType:
        parts: list[RenderableType] = []

        has_running = False
        for status, _name, label in self._steps:
            if status == "running":
                has_running = True
                self._tool_spinner.text = Text(label, style="dim")
                parts.append(self._tool_spinner)
            else:
                line = Text()
                line.append("→ ", style="dim")
                line.append(label, style="dim")
                parts.append(line)

        if self._status_text and not has_running:
            self._status_spinner.text = Text(self._status_text, style="dim")
            parts.append(self._status_spinner)

        if self._streaming_text:
            parts.append(Text())
            parts.append(Text(self._streaming_text))

        return Group(*parts) if parts else Text()

    # ProgressSink interface

    def start(self) -> None:
        pass

    def finish(self) -> None:
        self._status_text = None
        self._frozen = True
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._refresh(layout=True)

    def tool_start(self, name: str, args_summary: str) -> None:
        if self._status_text and self._status_text != "Thinking...":
            self._steps.append(("done", "__status__", self._status_text))
        label = f"{name}({args_summary})" if args_summary else name
        self._steps.append(("running", name, label))
        self._streaming_text = ""
        self._status_text = None
        self._refresh(layout=True, scroll=True)

    def tool_progress(self, completed: int, total: int) -> None:
        """Update the running tool step with a progress percentage."""
        pct = round(100 * completed / total) if total > 0 else 0
        self._tool_progress_pct = pct
        for i in range(len(self._steps) - 1, -1, -1):
            if self._steps[i][0] == "running":
                base_label = self._steps[i][2].split(" → ")[0]
                self._steps[i] = ("running", self._steps[i][1], f"{base_label} → {pct}%")
                break
        self._refresh(layout=True, scroll=True)

    def tool_end(self, name: str, result_summary: str) -> None:
        for i in range(len(self._steps) - 1, -1, -1):
            if self._steps[i][0] == "running":
                label = self._steps[i][2]
                if self._tool_progress_pct is not None:
                    # Already has "→ pct%"; update to final 100%
                    base_label = label.split(" → ")[0]
                    self._steps[i] = ("done", self._steps[i][1], f"{base_label} → 100%")
                else:
                    self._steps[i] = ("done", self._steps[i][1], f"{label} → {result_summary}")
                break
        self._tool_progress_pct = None
        self._status_text = "Thinking..."
        self._refresh(layout=True, scroll=True)

    def text_delta(self, delta: str) -> None:
        self._raw_text += delta
        # Only display text after the --- separator
        if self._separator_seen:
            self._streaming_text += delta
        elif "---" in self._raw_text:
            self._separator_seen = True
            self._streaming_text = self._raw_text.split("---", 1)[1].lstrip("\n")
        else:
            return
        self._status_text = None
        self._refresh(layout=True, scroll=True)

    def set_status(self, text: str) -> None:
        self._status_text = text
        self._refresh()

    def _refresh(self, *, layout: bool = False, scroll: bool = False) -> None:
        try:
            self.refresh(layout=layout)
            if scroll:
                self.app.query_one("#chat-log").scroll_end(animate=False)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Data browser screen
# ---------------------------------------------------------------------------


class DataBrowserScreen(Screen[None]):
    """Full-screen browser for inspecting query result rows."""

    DEFAULT_CSS = """
    DataBrowserScreen {
        background: $surface;
    }

    DataBrowserScreen .data-browser-grid {
        height: 1fr;
        margin: 0 1;
        border: solid white;
        background: $surface;
        color: $text;
        scrollbar-color: #666666;
        scrollbar-color-hover: #3EB489;
        scrollbar-color-active: #3EB489;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    DataBrowserScreen .data-browser-grid > .datatable--cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid > .datatable--fixed-cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid:focus > .datatable--cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid:focus > .datatable--fixed-cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid > .datatable--header {
        background: transparent;
        color: #3EB489;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid > .datatable--header-hover {
        background: transparent;
        color: #3EB489;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-grid > .datatable--header-cursor {
        background: transparent;
        color: #3EB489;
        text-style: bold;
    }

    DataBrowserScreen .data-browser-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }

    DataBrowserScreen .data-browser-status {
        padding: 0 1;
        color: #f5f5f5;
    }

    DataBrowserScreen .data-browser-gap {
        height: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
        Binding("q", "close_browser", "Back", show=False),
        Binding("b", "close_browser", "Back", show=False),
        Binding("[", "prev_page", "Prev page", show=True),
        Binding("]", "next_page", "Next page", show=True),
    ]

    def __init__(self, *, title: str, df: "pd.DataFrame", page_size: int = 50) -> None:
        super().__init__()
        self._title = title
        self._df = df
        self._page_size = max(1, page_size)
        self._page_index = 0
        self._sorted_column: str | None = None
        self._sort_reverse = False
        self._header_labels: tuple[str, ...] = tuple()
        self._table = DataTable(
            zebra_stripes=True,
            classes="data-browser-grid",
            header_height=2,
            show_cursor=True,
            cursor_type="cell",
            cursor_background_priority="css",
            cursor_foreground_priority="css",
        )
        self._status = Static(classes="data-browser-status")
        self._gap = Static(classes="data-browser-gap")
        self._hint = Static(classes="data-browser-hint")

    def compose(self) -> ComposeResult:
        yield self._table
        yield self._status
        yield self._gap
        yield self._hint

    def on_mount(self) -> None:
        self._table.focus()
        self._render_page()

    def action_close_browser(self) -> None:
        self.dismiss()

    def action_next_page(self) -> None:
        if self._page_index < self._max_page_index:
            self._page_index += 1
        else:
            self._page_index = 0
        self._render_page()

    def action_prev_page(self) -> None:
        if self._page_index > 0:
            self._page_index -= 1
        else:
            self._page_index = self._max_page_index
        self._render_page()

    @property
    def _num_rows(self) -> int:
        return len(self._df)

    @property
    def _max_page_index(self) -> int:
        if self._num_rows == 0:
            return 0
        return (self._num_rows - 1) // self._page_size

    def _render_page(self) -> None:
        start = self._page_index * self._page_size
        end = min(start + self._page_size, self._num_rows)
        page_df = self._df.iloc[start:end]

        header_labels = ["#"]
        for col in page_df.columns:
            label = str(col)
            if self._sorted_column == label:
                marker = "▼" if self._sort_reverse else "▲"
                label = f"{label} {marker}"
            header_labels.append(label)
        current_headers = tuple(header_labels)
        if current_headers != self._header_labels:
            self._table.clear(columns=True)
            self._table.add_columns(*header_labels)
            self._header_labels = current_headers
        else:
            self._table.clear(columns=False)

        for local_idx, row in enumerate(page_df.itertuples(index=False, name=None), start=1):
            row_number = start + local_idx
            cells = [str(row_number)] + [self._format_cell(v) for v in row]
            self._table.add_row(*cells)

        total_pages = self._max_page_index + 1
        shown_range = "0-0" if self._num_rows == 0 else f"{start + 1}-{end}"
        summary_and_status_line = (
            f"{self._title}  |  {self._num_rows:,} rows x {len(self._df.columns)} columns"
            f"  |  Rows {shown_range} of {self._num_rows:,}  |  Page {self._page_index + 1}/{total_pages}"
        )
        hint_fg = "dim"
        hint_segments: list[tuple[str, str]] = [
            ("[", ACCENT_BOLD),
            (" Prev Page    ", hint_fg),
            ("]", ACCENT_BOLD),
            (" Next Page    ", hint_fg),
            ("b", ACCENT_BOLD),
            (" Go Back    ", hint_fg),
        ]
        hint = Text()
        for text, style in hint_segments:
            hint.append(text, style=style)
        self._status.update(Text(summary_and_status_line, style=hint_fg))
        self._hint.update(hint)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Sort when user clicks a header cell."""
        if event.data_table is not self._table:
            return
        self._sort_by_column_index(event.column_index)
        event.stop()

    def _sort_by_column_index(self, column_index: int) -> None:
        """Sort by a displayed column index; index 0 is row number and ignored."""
        if column_index <= 0:
            return
        col_pos = column_index - 1
        if col_pos < 0 or col_pos >= len(self._df.columns):
            return
        column = str(self._df.columns[col_pos])
        if self._sorted_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sorted_column = column
            self._sort_reverse = False
        self._df = self._df.sort_values(
            by=column,
            ascending=not self._sort_reverse,
            kind="mergesort",
            na_position="last",
        )
        self._page_index = 0
        self._render_page()

    @staticmethod
    def _format_cell(value: object) -> str:
        s = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "⏎")
        if len(s) > 200:
            return s[:197] + "..."
        return s


# ---------------------------------------------------------------------------
# Chart browser screen
# ---------------------------------------------------------------------------


class ChartBrowserScreen(Screen[None]):
    """Full-screen viewer for inspecting a chart at terminal size."""

    DEFAULT_CSS = """
    ChartBrowserScreen {
        background: $surface;
    }

    ChartBrowserScreen .chart-browser-content {
        height: 1fr;
        margin: 0 1;
        padding: 1 2;
        background: $surface;
        color: $text;
    }

    ChartBrowserScreen .chart-browser-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
        Binding("q", "close_browser", "Back", show=False),
        Binding("b", "close_browser", "Back", show=False),
        Binding("f", "close_browser", "Back", show=False),
    ]

    def __init__(
        self, *, title: str, df: "pd.DataFrame", vegalite_spec: dict[str, object]
    ) -> None:
        super().__init__()
        self._title = title
        self._df = df
        self._vegalite_spec = vegalite_spec
        self._content = Static(classes="chart-browser-content")
        self._hint = Static(classes="chart-browser-hint")

    def compose(self) -> ComposeResult:
        yield self._content
        yield self._hint

    def on_mount(self) -> None:
        self._render_chart()

    def on_resize(self) -> None:
        self._render_chart()

    def action_close_browser(self) -> None:
        self.dismiss()

    def _render_chart(self) -> None:
        from mintq.cli.display import build_chart

        content_width = max(20, self._content.size.width - 4)
        content_height = max(10, self._content.size.height)
        renderable = build_chart(self._df, self._vegalite_spec, content_width, content_height)
        self._content.update(renderable)

        hint = Text()
        hint.append("f", style=ACCENT_BOLD)
        hint.append(" Go Back    ", style="dim")
        self._hint.update(hint)


# ---------------------------------------------------------------------------
# Agent result widget with interactive tabs
# ---------------------------------------------------------------------------


class AgentResultWidget(Widget):
    """Displays an agent result with interactive tab switching."""

    DEFAULT_CSS = """
    AgentResultWidget {
        padding: 1 1;
        margin: 1 4 0 1;
        height: auto;
        background: $surface;
    }

    AgentResultWidget .tab-bar {
        height: auto;
        margin: 0 0 1 0;
    }

    """

    current_tab: reactive[int] = reactive(0, init=False)

    def __init__(self, result: ChatResult, width: int = 80) -> None:
        super().__init__()
        from mintq.cli.display import build_result_views

        self._ordered_keys, self._views, self._data_views, self._query_views, self._chart_views = build_result_views(
            result, width
        )
        self._content = Static(id="result-content")
        self._mounted = False
        self._tab_hit_areas: list[tuple[int, int, int]] = []  # (row, col_start, col_end)
        self._expanded_query_keys: set[str] = set()

    @property
    def has_tabs(self) -> bool:
        return len(self._ordered_keys) > 1

    def compose(self) -> ComposeResult:
        if self.has_tabs:
            self._tab_bar_widget = Static(classes="tab-bar")
        if self.has_tabs:
            yield self._tab_bar_widget
        yield self._content

    def on_mount(self) -> None:
        self._mounted = True
        self._update_content()

    def on_resize(self) -> None:
        if self.has_tabs:
            self._update_tab_bar()

    def watch_current_tab(self) -> None:
        if not self._mounted:
            return
        self._update_content()
        if self.has_tabs:
            self._update_tab_bar()
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

    def _update_tab_bar(self) -> None:
        from rich.align import Align
        from rich.columns import Columns
        from rich.style import Style

        wrap_width = self._tab_bar_widget.size.width or 80
        current_key = self._current_key()

        hint = Text()
        if current_key in self._chart_views:
            if hint:
                hint.append("    ")
            hint.append("f", style=ACCENT_BOLD)
            hint.append(" Full Screen Chart", style="dim")
        if current_key in self._data_views:
            if hint:
                hint.append("    ")
            hint.append("b", style=ACCENT_BOLD)
            hint.append(" Open Data Browser", style="dim")
        if current_key in self._query_views:
            if current_key is not None and self._is_query_truncated(current_key):
                expanded = current_key in self._expanded_query_keys
                if hint:
                    hint.append("    ")
                hint.append("e", style=ACCENT_BOLD)
                hint.append(" Collapse Query" if expanded else " Show Full Query", style="dim")
        if hint:
            hint.append("    ")
        hint.append("←/→", style=ACCENT_BOLD)
        hint.append(" Switch Tab", style="dim")

        # Keep tab wrapping stable; if there isn't enough room for a side-by-side layout,
        # render hints on a right-aligned second line.
        hint_width = len(hint.plain)
        side_by_side = (wrap_width - hint_width - 1) >= 20
        tab_wrap_width = max(1, (wrap_width - hint_width - 1) if side_by_side else wrap_width)

        # Build styled text and compute hit areas by simulating layout.
        # Visual width uses raw key; Rich Text uses escaped key for markup safety.
        line = Text()
        self._tab_hit_areas = []
        row, col = 0, 0
        for i, key in enumerate(self._ordered_keys):
            label = f" {key} "
            sep = " " if i > 0 else ""
            needed = len(sep) + len(label)
            if col > 0 and col + needed > tab_wrap_width:
                line.append_text(Text("\n"))
                row += 1
                col = 0
                sep = ""
            if sep:
                line.append_text(Text(" "))
                col += 1
            col_start = col
            style = Style(bold=True, color="black", bgcolor="#3EB489") if i == self.current_tab else Style(dim=True)
            line.append_text(Text(label, style=style))
            col += len(label)
            self._tab_hit_areas.append((row, col_start, col))
        if side_by_side:
            self._tab_bar_widget.update(
                Columns(
                    [line, Align.right(hint)],
                    expand=True,
                    equal=False,
                    padding=(0, 1),
                )
            )
        else:
            self._tab_bar_widget.update(Group(line, Align.right(hint)))

    def _update_content(self) -> None:
        from mintq.cli.display import build_query

        if not self._ordered_keys:
            self._content.update(Text("No results to display.", style="dim"))
            return
        idx = min(self.current_tab, len(self._ordered_keys) - 1)
        key = self._ordered_keys[idx]
        query_view = self._query_views.get(key)
        if query_view is not None:
            query, lexer = query_view
            expanded = key in self._expanded_query_keys
            renderable = build_query(
                query,
                max_lines=None if expanded else QUERY_PREVIEW_MAX_LINES,
                lexer=lexer,
            )
        else:
            renderable = self._views.get(key, Text(""))
        self._content.update(renderable)

    def _current_key(self) -> str | None:
        if not self._ordered_keys:
            return None
        idx = min(self.current_tab, len(self._ordered_keys) - 1)
        return self._ordered_keys[idx]

    def on_click(self, event: object) -> None:
        """Handle clicks on tab labels."""
        from textual.events import Click

        assert isinstance(event, Click)

        if self.has_tabs and event.widget is self._tab_bar_widget:
            for i, (row, col_start, col_end) in enumerate(self._tab_hit_areas):
                if event.y == row and col_start <= event.x < col_end:
                    self.current_tab = i
                    break
            return

        if event.widget is self._content:
            key = self._current_key()
            if key in self._data_views and self._is_table_region_click(key=key, x=event.x, y=event.y):
                self.action_open_data_browser()
                return
            if key in self._query_views and key is not None and self._is_query_truncated(key):
                self.action_toggle_query_preview()

    def _is_table_region_click(self, *, key: str, x: int, y: int) -> bool:
        """Return True when click lands within the visible data-table preview area."""
        if x < 0 or y < 0:
            return False
        content_height = self._content.size.height
        if content_height <= 0:
            return False
        table_width = self._data_preview_table_width(key)
        if table_width <= 0 or x >= table_width:
            return False
        footer_lines = 1 if self._data_preview_has_footer(key) else 0
        return y < (content_height - footer_lines)

    def _data_preview_has_footer(self, key: str) -> bool:
        """Data preview shows a one-line footer only when rows/cols are truncated."""
        df = self._data_views.get(key)
        if df is None:
            return False
        return len(df) > DATA_PREVIEW_MAX_ROWS or len(df.columns) > DATA_PREVIEW_MAX_COLUMNS

    def _data_preview_table_width(self, key: str) -> int:
        """Measure rendered width of the data preview table area."""
        renderable = self._views.get(key)
        if renderable is None:
            return 0
        table_renderable = renderable
        if isinstance(renderable, Group):
            renderables = tuple(getattr(renderable, "renderables", ()))
            if not renderables:
                return 0
            table_renderable = renderables[0]
        options = self.app.console.options.update(width=max(1, self._content.size.width))
        measurement = self.app.console.measure(table_renderable, options=options)
        return measurement.maximum

    def _is_query_truncated(self, key: str) -> bool:
        """Return True when query preview uses truncation for this key."""
        query_view = self._query_views.get(key)
        if query_view is None:
            return False
        query, _lexer = query_view
        return len(query.strip().splitlines()) > QUERY_PREVIEW_MAX_LINES

    def action_next_tab(self) -> None:
        if self._ordered_keys:
            self.current_tab = (self.current_tab + 1) % len(self._ordered_keys)

    def action_prev_tab(self) -> None:
        if self._ordered_keys:
            self.current_tab = (self.current_tab - 1) % len(self._ordered_keys)

    def action_toggle_query_preview(self) -> None:
        """Toggle expanded/collapsed rendering for the active Query tab."""
        key = self._current_key()
        if key is None or key not in self._query_views or not self._is_query_truncated(key):
            return
        if key in self._expanded_query_keys:
            self._expanded_query_keys.remove(key)
        else:
            self._expanded_query_keys.add(key)
        self._update_content()
        if self._is_last_chat_item():
            chat_log = self.app.query_one("#chat-log")
            chat_log.scroll_end(animate=False)

    can_focus = True

    BINDINGS = [
        ("right", "next_tab", "Next tab"),
        ("left", "prev_tab", "Previous tab"),
        ("tab", "next_tab", "Next tab"),
        ("shift+tab", "prev_tab", "Previous tab"),
        ("e", "toggle_query_preview", "Expand/collapse query"),
        ("f", "open_chart_browser", "Full screen chart"),
        ("b", "open_data_browser", "Open data browser"),
        ("up", "focus_prev_result", "Previous result"),
        ("down", "focus_next_result", "Next result"),
        ("k", "focus_prev_result", "Previous result"),
        ("j", "focus_next_result", "Next result"),
        ("escape", "focus_input", "Back to input"),
        ("i", "focus_input", "Back to input"),
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
        """Focus the next AgentResultWidget."""
        results = list(self.app.query(AgentResultWidget))
        try:
            idx = results.index(self)
        except ValueError:
            return
        if idx < len(results) - 1:
            results[idx + 1].focus()
            results[idx + 1].scroll_visible()

    def action_focus_input(self) -> None:
        """Return focus to the input bar."""
        self.app.query_one("#input-bar").focus()

    def action_open_data_browser(self) -> None:
        """Open full data browser for the active Data tab."""
        key = self._current_key()
        if key is None:
            return
        df = self._data_views.get(key)
        if df is None:
            return
        self.app.push_screen(DataBrowserScreen(title=key, df=df))

    def action_open_chart_browser(self) -> None:
        """Open full-screen chart viewer for the active Chart tab."""
        key = self._current_key()
        if key is None:
            return
        chart_data = self._chart_views.get(key)
        if chart_data is None:
            return
        df, spec = chart_data
        self.app.push_screen(ChartBrowserScreen(title=key, df=df, vegalite_spec=spec))
