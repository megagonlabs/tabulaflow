"""Textual widgets for the mintq TUI."""

from __future__ import annotations

import re
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
from textual.widgets import DataTable, Input, Static, TextArea

from mintq.cli.display import (
    DATA_PREVIEW_MAX_COLUMNS,
    DATA_PREVIEW_MAX_ROWS,
    QUERY_PREVIEW_MAX_LINES,
)
from mintq.cli.theme import ACCENT, ACCENT_BOLD, DRACULA_TRANSPARENT

if TYPE_CHECKING:
    import pandas as pd
    from rich.console import RenderableType

    from mintq.cli.agent import ChatResult


# ---------------------------------------------------------------------------
# Autocomplete suggester
# ---------------------------------------------------------------------------

_SLASH_COMMANDS = sorted(
    ["/help", "/exit", "/clear", "/connect", "/disconnect", "/databases", "/db", "/schema", "/browse", "/model"]
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
        self._label = label
        self._spinner = Spinner("dots", text=Text(label, style="dim"), style="dim")

    def update_label(self, label: str) -> None:
        self._label = label
        self._spinner.text = Text(label, style="dim")

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
        self._steps: list[tuple[str, str, str, str]] = []  # (status, tool_call_id, name, label)
        self._streaming_text = ""
        self._raw_text = ""
        self._separator_seen = False
        self._status_text: str | None = "Thinking..."
        # Persistent spinner instances so animation state survives across renders.
        self._status_spinner = Spinner("dots", text=Text("Thinking...", style="dim"), style="dim")
        self._tool_spinner = Spinner("dots", style="dim")
        self._tool_progress_pct: int | None = None
        self._frozen = False
        self._timer: Timer | None = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / 12, self.refresh)

    def render(self) -> RenderableType:
        parts: list[RenderableType] = []

        has_running = False
        for status, _tool_call_id, _name, label in self._steps:
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
            if self._steps:
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

    def tool_start(self, tool_call_id: str, name: str, args_summary: str) -> None:
        if self._status_text and self._status_text != "Thinking...":
            self._steps.append(("done", "", "__status__", self._status_text))
        label = f"{name}({args_summary})" if args_summary else name
        self._steps.append(("running", tool_call_id, name, label))
        self._streaming_text = ""
        self._status_text = None
        self._refresh(layout=True, scroll=True)

    def tool_progress(self, completed: int, total: int) -> None:
        """Update the running tool step with a progress percentage."""
        pct = round(100 * completed / total) if total > 0 else 0
        self._tool_progress_pct = pct
        for i in range(len(self._steps) - 1, -1, -1):
            if self._steps[i][0] == "running":
                base_label = self._steps[i][3].split(" → ")[0]
                self._steps[i] = ("running", self._steps[i][1], self._steps[i][2], f"{base_label} → {pct}%")
                break
        self._refresh(layout=True, scroll=True)

    def tool_end(self, tool_call_id: str, name: str, result_summary: str) -> None:
        for i in range(len(self._steps) - 1, -1, -1):
            step = self._steps[i]
            if step[0] == "running" and step[1] == tool_call_id:
                label = step[3]
                if self._tool_progress_pct is not None:
                    base_label = label.split(" → ")[0]
                    self._steps[i] = ("done", step[1], step[2], f"{base_label} → 100%")
                else:
                    self._steps[i] = ("done", step[1], step[2], f"{label} → {result_summary}")
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
        border: solid #3EB489;
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

    DataBrowserScreen .data-browser-grid > .datatable--fixed {
        background: transparent;
        color: #888888;
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
        Binding("enter", "open_cell", "View cell", priority=True),
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
        self._table: DataTable[Text] = DataTable(
            zebra_stripes=True,
            classes="data-browser-grid",
            header_height=2,
            show_cursor=True,
            cursor_type="cell",
            cursor_background_priority="css",
            cursor_foreground_priority="css",
            fixed_columns=1,
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

    def action_open_cell(self) -> None:
        """Open cell value browser for the currently highlighted cell."""
        row_idx = self._table.cursor_coordinate.row
        col_idx = self._table.cursor_coordinate.column
        # Column 0 is the row-number column; skip it.
        if col_idx <= 0:
            return
        df_col = col_idx - 1
        if df_col >= len(self._df.columns):
            return
        start = self._page_index * self._page_size
        df_row = start + row_idx
        if df_row >= len(self._df):
            return
        col_name = str(self._df.columns[df_col])
        raw_value = self._df.iloc[df_row, df_col]
        row_number = df_row + 1
        dtype_str = self._describe_dtype(self._df[col_name])
        self.app.push_screen(
            CellBrowserScreen(
                column_name=col_name,
                row_number=row_number,
                value=raw_value,
                dtype_str=dtype_str,
            )
        )

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
        self._table.clear(columns=True)
        self._table.add_columns(*header_labels)

        for local_idx, row in enumerate(page_df.itertuples(index=False, name=None), start=1):
            row_number = start + local_idx
            row_label = Text(f"{row_number:,}", justify="right")
            cells = [row_label] + [self._format_cell(v) for v in row]
            self._table.add_row(*cells)

        self._update_status()
        self._update_hint()

    def _update_status(self) -> None:
        total_pages = self._max_page_index + 1
        start = self._page_index * self._page_size
        end = min(start + self._page_size, self._num_rows)
        shown_range = "0-0" if self._num_rows == 0 else f"{start + 1}-{end}"

        parts = [
            self._title,
            f"{self._num_rows:,} rows x {len(self._df.columns)} cols",
            f"Rows {shown_range} of {self._num_rows:,}",
            f"Page {self._page_index + 1}/{total_pages}",
        ]

        col_index = self._table.cursor_coordinate.column - 1
        if 0 <= col_index < len(self._df.columns):
            col_name = str(self._df.columns[col_index])
            col_dtype = self._describe_dtype(self._df[col_name])
            parts.append(f"{col_name} ({col_dtype})")

        self._status.update(Text("  |  ".join(parts), style="dim"))

    def _update_hint(self) -> None:
        hint_fg = "dim"
        hint_segments: list[tuple[str, str]] = [
            ("Esc", ACCENT_BOLD),
            (" Back    ", hint_fg),
            ("Enter", ACCENT_BOLD),
            (" View Cell    ", hint_fg),
            ("[", ACCENT_BOLD),
            (" Prev Page    ", hint_fg),
            ("]", ACCENT_BOLD),
            (" Next Page    ", hint_fg),
        ]
        hint = Text()
        for text, style in hint_segments:
            hint.append(text, style=style)
        self._hint.update(hint)

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        """Update status bar with selected column dtype."""
        if event.data_table is self._table:
            self._update_status()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Suppress default Enter behavior on cells."""
        event.stop()

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

    _MAX_CELL_LEN = 80

    @staticmethod
    def _describe_dtype(series: "pd.Series") -> str:
        """Return a human-readable dtype label, resolving 'object' to the actual Python type."""
        dtype_str = str(series.dtype)
        if dtype_str != "object":
            return dtype_str
        sample = series.dropna().head(20)
        if sample.empty:
            return "object"
        types = {type(v).__name__ for v in sample}
        if len(types) == 1:
            return types.pop()
        return "mixed"

    @staticmethod
    def _format_cell(value: object) -> Text:
        import numbers

        import pandas as pd_

        try:
            if value is None or pd_.isna(value):
                return Text("NULL", style="dim italic")
        except (TypeError, ValueError):
            pass

        if isinstance(value, bool):
            return Text("✔" if value else "✘", style=ACCENT if value else "dim")

        if isinstance(value, numbers.Integral):
            return Text(f"{value:,}", justify="right")

        if isinstance(value, numbers.Real):
            return Text(f"{value:,}", justify="right")

        s = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "⏎")
        if s == "<binary: skipped>":
            return Text(s, style="dim italic")
        if len(s) > DataBrowserScreen._MAX_CELL_LEN:
            t = Text(s[: DataBrowserScreen._MAX_CELL_LEN - 3])
            t.append("...", style="dim")
            return t
        return Text(s)


# ---------------------------------------------------------------------------
# Cell value browser screen
# ---------------------------------------------------------------------------


class CellBrowserScreen(Screen[None]):
    """Full-screen viewer for inspecting a single cell value."""

    DEFAULT_CSS = """
    CellBrowserScreen {
        background: $surface;
    }

    CellBrowserScreen TextArea {
        height: 1fr;
        margin: 0 1;
        border: solid white;
        background: $surface;
        scrollbar-color: #666666;
        scrollbar-color-hover: #3EB489;
        scrollbar-color-active: #3EB489;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    CellBrowserScreen TextArea:focus {
        border: solid white;
        outline: none;
    }

    CellBrowserScreen .cell-browser-status {
        padding: 0 1;
        color: #f5f5f5;
    }

    CellBrowserScreen .cell-browser-gap {
        height: 1;
    }

    CellBrowserScreen .cell-browser-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
    ]

    def __init__(
        self,
        *,
        column_name: str,
        row_number: int,
        value: object,
        dtype_str: str,
    ) -> None:
        super().__init__()
        self._column_name = column_name
        self._row_number = row_number
        self._raw_value = value
        self._dtype_str = dtype_str
        self._display_text, self._language = self._format_value(value)

    _SQL_RE = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|EXPLAIN)\b", re.IGNORECASE)
    _PY_RE = re.compile(r"^\s*(def |class |import |from |if __name__)")

    _MAX_JSON_LEAF = 1000

    @staticmethod
    def _truncate_json_leaves(obj: object, max_len: int) -> object:
        """Recursively truncate long string/bytes leaves in a JSON-like structure."""
        if isinstance(obj, dict):
            return {k: CellBrowserScreen._truncate_json_leaves(v, max_len) for k, v in obj.items()}
        if isinstance(obj, list):
            return [CellBrowserScreen._truncate_json_leaves(v, max_len) for v in obj]
        if isinstance(obj, (bytes, bytearray)):
            if len(obj) > max_len:
                return f"<binary: {len(obj):,} bytes>"
            return obj.hex(" ")
        if isinstance(obj, str) and len(obj) > max_len:
            return obj[:max_len] + f"... ({len(obj):,} chars)"
        return obj

    @staticmethod
    def _try_as_json(value: object) -> str | None:
        """Try to pretty-print value as JSON. Returns formatted string or None."""
        import ast
        import json

        if isinstance(value, (dict, list)):
            obj = value
        elif isinstance(value, str):
            # Try JSON first, then Python repr
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(value)
                    if isinstance(parsed, (dict, list)):
                        obj = parsed
                        break
                except Exception:
                    continue
            else:
                return None
        else:
            return None
        obj = CellBrowserScreen._truncate_json_leaves(obj, CellBrowserScreen._MAX_JSON_LEAF)
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)

    _MAX_CELL_DISPLAY = 10000

    @staticmethod
    def _format_value(value: object) -> tuple[str, str | None]:
        """Return (display_text, language) for the cell value."""
        import pandas as pd_

        try:
            if value is None or pd_.isna(value):
                return "NULL", None
        except (TypeError, ValueError):
            pass

        if isinstance(value, (bytes, bytearray, memoryview)):
            raw = bytes(value)
            preview = raw[:32].hex(" ")
            return f"<binary: {len(raw):,} bytes>\n{preview} ...", None

        json_str = CellBrowserScreen._try_as_json(value)
        if json_str is not None:
            if len(json_str) > CellBrowserScreen._MAX_CELL_DISPLAY:
                json_str = json_str[:CellBrowserScreen._MAX_CELL_DISPLAY] + f"\n\n... ({len(json_str):,} chars total, truncated)"
            return json_str, "json"

        s = str(value)
        if CellBrowserScreen._SQL_RE.match(s):
            if len(s) > CellBrowserScreen._MAX_CELL_DISPLAY:
                s = s[:CellBrowserScreen._MAX_CELL_DISPLAY] + f"\n\n... ({len(s):,} chars total, truncated)"
            return s, "sql"
        if CellBrowserScreen._PY_RE.match(s):
            if len(s) > CellBrowserScreen._MAX_CELL_DISPLAY:
                s = s[:CellBrowserScreen._MAX_CELL_DISPLAY] + f"\n\n... ({len(s):,} chars total, truncated)"
            return s, "python"
        if len(s) > CellBrowserScreen._MAX_CELL_DISPLAY:
            s = s[:CellBrowserScreen._MAX_CELL_DISPLAY] + f"\n\n... ({len(s):,} chars total, truncated)"
        return s, None

    def compose(self) -> ComposeResult:
        lang = self._language if self._language in QueryBrowserScreen._SUPPORTED_LANGUAGES else None
        yield TextArea(
            self._display_text,
            language=lang,
            read_only=True,
            show_line_numbers=True,
            soft_wrap=True,
        )
        yield Static(classes="cell-browser-status")
        yield Static(classes="cell-browser-gap")
        yield Static(classes="cell-browser-hint")

    def on_mount(self) -> None:
        text_area = self.query_one(TextArea)
        text_area.register_theme(DRACULA_TRANSPARENT)
        text_area.theme = "dracula-transparent"

        status_text = f"{self._column_name} ({self._dtype_str})  |  Row {self._row_number:,}"
        self.query_one(".cell-browser-status", Static).update(
            Text(status_text, style="dim")
        )

        hint = Text()
        hint.append("Esc", style=ACCENT_BOLD)
        hint.append(" Back    ", style="dim")
        self.query_one(".cell-browser-hint", Static).update(hint)

    def action_close_browser(self) -> None:
        self.dismiss()


# ---------------------------------------------------------------------------
# Query browser screen
# ---------------------------------------------------------------------------


class QueryBrowserScreen(Screen[None]):
    """Full-screen viewer for inspecting a query with scrolling."""

    DEFAULT_CSS = """
    QueryBrowserScreen {
        background: $surface;
    }

    QueryBrowserScreen TextArea {
        height: 1fr;
        margin: 0 1;
        border: solid white;
        background: $surface;
        scrollbar-color: #666666;
        scrollbar-color-hover: #3EB489;
        scrollbar-color-active: #3EB489;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    QueryBrowserScreen TextArea:focus {
        border: solid white;
        outline: none;
    }

    QueryBrowserScreen .query-browser-gap {
        height: 1;
    }

    QueryBrowserScreen .query-browser-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
    ]

    # Languages supported by Textual's TextArea.
    _SUPPORTED_LANGUAGES = frozenset({
        "bash", "css", "go", "html", "java", "javascript", "json",
        "markdown", "python", "regex", "rust", "sql", "toml", "xml", "yaml",
    })

    def __init__(self, *, title: str, query: str, lexer: str = "sql") -> None:
        super().__init__()
        self._title = title
        self._query = query
        self._lexer = lexer

    def compose(self) -> ComposeResult:
        lang = self._lexer if self._lexer in self._SUPPORTED_LANGUAGES else None
        yield TextArea(
            self._query,
            language=lang,
            read_only=True,
            show_line_numbers=True,
            soft_wrap=False,
        )
        yield Static(classes="query-browser-gap")
        yield Static(classes="query-browser-hint")

    def on_mount(self) -> None:
        text_area = self.query_one(TextArea)
        text_area.register_theme(DRACULA_TRANSPARENT)
        text_area.theme = "dracula-transparent"

        hint_text = Text()
        hint_text.append("Esc", style=ACCENT_BOLD)
        hint_text.append(" Back    ", style="dim")
        self.query_one(".query-browser-hint", Static).update(hint_text)

    def action_close_browser(self) -> None:
        self.dismiss()


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

    def on_click(self, event: object) -> None:
        self.dismiss()

    def _render_chart(self) -> None:
        from mintq.cli.display import build_chart

        content_width = max(20, self._content.size.width - 4)
        content_height = max(10, self._content.size.height)
        renderable = build_chart(self._df, self._vegalite_spec, content_width, content_height)
        self._content.update(renderable)

        hint = Text()
        hint.append("Esc", style=ACCENT_BOLD)
        hint.append(" Back    ", style="dim")
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
        if current_key in self._chart_views or current_key in self._data_views or current_key in self._query_views:
            if hint:
                hint.append("    ")
            hint.append("Enter", style=ACCENT_BOLD)
            hint.append(" Full Screen", style="dim")
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
            renderable = build_query(query, max_lines=QUERY_PREVIEW_MAX_LINES, lexer=lexer)
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
            if key in self._chart_views and self._is_chart_region_click(key=key, x=event.x, y=event.y):
                self.action_open_full_screen()
                return
            if key in self._data_views and self._is_table_region_click(key=key, x=event.x, y=event.y):
                self.action_open_full_screen()
                return
            if key in self._query_views:
                self.action_open_full_screen()
                return

    def _is_chart_region_click(self, *, key: str, x: int, y: int) -> bool:
        """Return True when click lands within the rendered chart area."""
        if x < 0 or y < 0:
            return False
        renderable = self._views.get(key)
        if renderable is None:
            return False
        options = self.app.console.options.update(width=max(1, self._content.size.width))
        measurement = self.app.console.measure(renderable, options=options)
        return x < measurement.maximum

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


    def action_next_tab(self) -> None:
        if self._ordered_keys:
            self.current_tab = (self.current_tab + 1) % len(self._ordered_keys)

    def action_prev_tab(self) -> None:
        if self._ordered_keys:
            self.current_tab = (self.current_tab - 1) % len(self._ordered_keys)

    can_focus = True

    BINDINGS = [
        ("right", "next_tab", "Next tab"),
        ("left", "prev_tab", "Previous tab"),
        ("tab", "next_tab", "Next tab"),
        ("shift+tab", "prev_tab", "Previous tab"),
        ("enter", "open_full_screen", "Full screen"),
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

    def action_open_full_screen(self) -> None:
        """Open full-screen viewer for the active Chart, Data, or Query tab."""
        key = self._current_key()
        if key is None:
            return
        chart_data = self._chart_views.get(key)
        if chart_data is not None:
            df, spec = chart_data
            self.app.push_screen(ChartBrowserScreen(title=key, df=df, vegalite_spec=spec))
            return
        df = self._data_views.get(key)
        if df is not None:
            self.app.push_screen(DataBrowserScreen(title=key, df=df))
            return
        query_data = self._query_views.get(key)
        if query_data is not None:
            query, lexer = query_data
            self.app.push_screen(QueryBrowserScreen(title=key, query=query, lexer=lexer))


# ---------------------------------------------------------------------------
# Schema browser screen
# ---------------------------------------------------------------------------

# Node data stored in Tree nodes to identify what each node represents.
_NODE_KIND_DB = "db"
_NODE_KIND_SCHEMA = "schema"
_NODE_KIND_TABLE = "table"
_NODE_KIND_COLUMN = "column"


class _NodeData:
    """Metadata attached to each Tree node."""

    __slots__ = ("kind", "alias", "schema_name", "table_name")

    def __init__(
        self,
        kind: str,
        alias: str,
        schema_name: str | None = None,
        table_name: str | None = None,
    ) -> None:
        self.kind = kind
        self.alias = alias
        self.schema_name = schema_name
        self.table_name = table_name


class SchemaBrowserScreen(Screen[None]):
    """Full-screen tree browser for exploring connected database schemas."""

    DEFAULT_CSS = """
    SchemaBrowserScreen {
        background: $surface;
    }

    SchemaBrowserScreen #browse-tree {
        height: 1fr;
        margin: 0 1;
        scrollbar-color: #666666;
        scrollbar-color-hover: #3EB489;
        scrollbar-color-active: #3EB489;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
    }

    SchemaBrowserScreen #browse-tree > .tree--cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    SchemaBrowserScreen #browse-tree:focus > .tree--cursor {
        background: #3EB489;
        color: black;
        text-style: bold;
    }

    SchemaBrowserScreen #browse-tree > .tree--highlight {
        background: transparent;
    }

    SchemaBrowserScreen #browse-tree > .tree--highlight-line {
        background: transparent;
    }

    SchemaBrowserScreen #browse-tree > .tree--guides {
        color: #555555;
    }

    SchemaBrowserScreen #browse-tree > .tree--guides-hover {
        color: #555555;
    }

    SchemaBrowserScreen #browse-tree > .tree--guides-selected {
        color: #555555;
    }

    SchemaBrowserScreen #browse-tree:focus > .tree--guides-selected {
        color: #555555;
    }

    SchemaBrowserScreen #browse-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
        Binding("left", "collapse_node", "Collapse", show=False, priority=True),
        Binding("right", "expand_node", "Expand", show=False, priority=True),
        Binding("enter", "open_preview", "Preview table", show=False, priority=True),
    ]

    def __init__(self, *, registry: object, alias: str | None = None) -> None:
        super().__init__()
        from mintq.db_connector.db_registry import DBRegistry

        assert isinstance(registry, DBRegistry)
        self._registry: DBRegistry = registry
        self._filter_alias = alias
        self._hint = Static(id="browse-hint")

    def compose(self) -> ComposeResult:
        from textual.widgets import Tree

        tree: Tree[_NodeData] = Tree("Databases", id="browse-tree")
        tree.show_root = False
        tree.guide_depth = 3
        tree.auto_expand = False

        yield tree
        yield self._hint

    def on_mount(self) -> None:
        self._build_tree()
        self._update_hint()
        self.query_one("#browse-tree").focus()

    # -- tree construction ---------------------------------------------------

    def _build_tree(self) -> None:
        from textual.widgets import Tree

        from mintq.schema import SQLSchema, SQLTableSchema

        tree = self.query_one("#browse-tree", Tree)

        aliases = self._registry.list_aliases()
        if self._filter_alias is not None:
            aliases = [a for a in aliases if a == self._filter_alias]
        aliases.sort()

        for alias in aliases:
            connector = self._registry.get(alias)
            schema = connector.schema
            if not isinstance(schema, SQLSchema):
                continue

            db_label = Text()
            db_label.append(alias, style="bold")
            dialect = schema.dialect or getattr(connector, "language", None)
            if dialect:
                db_label.append(f"  {dialect}", style="dim")

            auto_expand = alias != "workspace"
            db_node = tree.root.add(
                db_label,
                data=_NodeData(kind=_NODE_KIND_DB, alias=alias),
                expand=auto_expand,
            )

            tables: list[SQLTableSchema] = list(schema.tables)
            schema_names: set[str | None] = {t.schema_name for t in tables}
            has_schemas = schema_names != {None}

            if has_schemas:
                groups: dict[str | None, list[SQLTableSchema]] = {}
                for t in tables:
                    groups.setdefault(t.schema_name, []).append(t)
                for sn in sorted(groups, key=lambda s: (s is None, s or "")):
                    sn_label = Text()
                    sn_label.append(sn or "(default)", style="bold")
                    sn_label.append(f"  {len(groups[sn])} tables", style="dim")
                    schema_node = db_node.add(
                        sn_label,
                        data=_NodeData(kind=_NODE_KIND_SCHEMA, alias=alias, schema_name=sn),
                        expand=auto_expand,
                    )
                    for t in sorted(groups[sn], key=lambda t: t.name):
                        self._add_table_node(schema_node, alias, t)
            else:
                for t in sorted(tables, key=lambda t: t.name):
                    self._add_table_node(db_node, alias, t)

    @staticmethod
    def _add_table_node(parent: object, alias: str, table: object) -> None:
        from typing import Any

        from mintq.schema import SQLTableSchema

        assert isinstance(table, SQLTableSchema)
        parent_node: Any = parent

        t_label = Text()
        t_label.append(table.name)
        parts: list[str] = []
        if table.num_rows is not None:
            parts.append(f"{table.num_rows:,} rows")
        parts.append(f"{len(table.columns)} cols")
        if table.is_view:
            parts.append("view")
        t_label.append(f"  {', '.join(parts)}", style="dim")

        table_node = parent_node.add(
            t_label,
            data=_NodeData(
                kind=_NODE_KIND_TABLE,
                alias=alias,
                schema_name=table.schema_name,
                table_name=table.name,
            ),
        )

        for col in table.columns:
            c_label = Text()
            c_label.append(col.name)
            c_label.append(f"  {col.dtype}", style="dim")
            if col.primary_key_type:
                c_label.append(" PK", style="bold #e6c07b")
            if col.foreign_keys:
                c_label.append(" FK", style="#61afef")
            table_node.add_leaf(c_label, data=None)

    # -- actions --------------------------------------------------------------

    def action_open_preview(self) -> None:
        """Open DataBrowserScreen for the table under the cursor using sampled_df."""
        from textual.widgets import Tree

        from mintq.schema import SQLSchema

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return
        node_data: _NodeData | None = node.data
        if node_data is None or node_data.kind != _NODE_KIND_TABLE:
            return

        connector = self._registry.get(node_data.alias)
        schema = connector.schema
        assert isinstance(schema, SQLSchema)
        table = next(
            (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
            None,
        )
        if table is None or table.sampled_df is None or table.sampled_df.empty:
            return

        title = (
            f"{node_data.alias}: {node_data.schema_name}.{node_data.table_name} (preview)"
            if node_data.schema_name
            else f"{node_data.alias}: {node_data.table_name} (preview)"
        )
        self.app.push_screen(DataBrowserScreen(title=title, df=table.sampled_df))

    # -- actions & hints -----------------------------------------------------

    def action_close_browser(self) -> None:
        self.dismiss()

    def action_collapse_node(self) -> None:
        """Collapse the cursor node."""
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return
        node.collapse()

    def action_expand_node(self) -> None:
        """Expand the cursor node."""
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return
        node.expand()

    def on_tree_node_highlighted(self, event: object) -> None:
        """Update hint bar when cursor moves."""
        self._update_hint()

    def _cursor_has_preview(self) -> bool:
        """Return True if the cursor is on a table node with sampled_df."""
        from textual.widgets import Tree

        from mintq.schema import SQLSchema

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            return False
        node_data: _NodeData | None = node.data
        if node_data is None or node_data.kind != _NODE_KIND_TABLE:
            return False
        connector = self._registry.get(node_data.alias)
        schema = connector.schema
        if not isinstance(schema, SQLSchema):
            return False
        table = next(
            (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
            None,
        )
        return table is not None and table.sampled_df is not None and not table.sampled_df.empty

    def _update_hint(self) -> None:
        hint_fg = "dim"
        hint = Text()
        hint.append("Esc", style=ACCENT_BOLD)
        hint.append(" Back", style=hint_fg)
        if self._cursor_has_preview():
            hint.append("    ", style=hint_fg)
            hint.append("Enter", style=ACCENT_BOLD)
            hint.append(" Preview table", style=hint_fg)
        self._hint.update(hint)
