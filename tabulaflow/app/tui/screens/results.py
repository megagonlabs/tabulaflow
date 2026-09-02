"""Full-screen result inspection."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Static, TextArea

from tabulaflow.app.theme import (
    ACCENT,
    normalize_query_lexer,
)
from tabulaflow.app.tui.theme import (
    ERROR,
    KEY_HINT,
    configure_code_text_area,
)
from tabulaflow.core.media import detect_media, extract_media_bytes


if TYPE_CHECKING:
    import pandas as pd


def _normalize_json_like(value: object) -> object:
    """Coerce ``ndarray``/``dict``/``list`` cells into a JSON-ready structure.

    Converts numpy ndarrays to lists and recursively json.loads any string leaf
    that parses as a dict or list — so HF-style JSON-array columns
    (``ndarray([str, str, ...])``) render as structured JSON instead of
    backslash-escaped Python list reprs.
    """
    import numpy as np

    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, dict):
        return {k: _normalize_json_like(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_json_like(v) for v in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
        if isinstance(parsed, (dict, list)):
            return _normalize_json_like(parsed)
        return value
    return value


class DataBrowserScreen(Screen[None]):
    """Full-screen browser for inspecting query result rows."""

    DEFAULT_CSS = """
    DataBrowserScreen {
        background: $background;
    }

    DataBrowserScreen .data-browser-grid {
        height: 1fr;
        margin: 0 1;
        border: solid #3EB489;
        background: $background;
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

    DataBrowserScreen .data-browser-grid:focus {
        border: solid #3EB489;
        outline: none;
        background-tint: transparent 0%;
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
        Binding("enter", "open_cell", "Inspect cell", priority=True),
        Binding("[", "prev_page", "Prev page", show=True),
        Binding("]", "next_page", "Next page", show=True),
        Binding("b", "send_table_to_output_pane", "Send table to output pane", show=True, priority=True),
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

    async def action_open_cell(self) -> None:
        """Open cell value browser for the currently highlighted cell.

        Yields one event-loop tick after updating the status so Textual
        gets to paint ``Loading cell...`` before we run the (CPU-bound,
        GIL-holding) ``_format_value`` synchronously.
        """
        import asyncio

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

        self._status.update(Text("Loading cell...", style="dim"))
        # Wait until Textual has actually painted the new status before we
        # block the main thread with _format_value (CPU-bound, holds GIL).
        painted: asyncio.Future[None] = asyncio.get_running_loop().create_future()

        def mark_painted() -> None:
            if not painted.done():
                painted.set_result(None)

        self.call_after_refresh(mark_painted)
        await painted
        try:
            display_text, language = CellBrowserScreen._format_value(raw_value)
        finally:
            self._update_status()
        self.app.push_screen(
            CellBrowserScreen(
                column_name=col_name,
                row_number=row_number,
                value=raw_value,
                dtype_str=dtype_str,
                display_text=display_text,
                language=language,
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

    async def action_send_table_to_output_pane(self) -> None:
        """Render the current DataFrame payload and send it to the output pane."""
        import asyncio

        self._set_status_message(Text("Sending...", style="dim"))
        painted: asyncio.Future[None] = asyncio.get_running_loop().create_future()

        def mark_painted() -> None:
            if not painted.done():
                painted.set_result(None)

        self.call_after_refresh(mark_painted)
        await painted
        from tabulaflow.app.tui.app import TabulaflowApp

        app = cast(TabulaflowApp, self.app)
        if app.show_table_in_pane(self._df, title=self._title):
            self._set_status_message(Text("sent to output pane", style="dim"))
        else:
            self._set_status_message(Text("results pane unavailable", style=ERROR))

    def _set_status_message(self, message: "Text") -> None:
        """Display a transient status message from an output-pane helper."""
        self._status.update(message)

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
        # Textual's DataTable.clear() always resets scroll_x; save and restore.
        scroll_x = self._table.scroll_x
        self._table.clear(columns=True)
        self._table.add_columns(*header_labels)

        for local_idx, row in enumerate(page_df.itertuples(index=False, name=None), start=1):
            row_number = start + local_idx
            row_label = Text(f"{row_number:,}", justify="right")
            cells = [row_label] + [self._format_cell(v) for v in row]
            self._table.add_row(*cells)

        self._table.scroll_to(x=scroll_x, y=0, animate=False)
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
            ("Esc", KEY_HINT),
            (" Back    ", hint_fg),
            ("↵", KEY_HINT),
            (" Inspect cell    ", hint_fg),
            ("[", KEY_HINT),
            ("/", hint_fg),
            ("]", KEY_HINT),
            (" Prev/Next page    ", hint_fg),
            ("B", KEY_HINT),
            (" Send table to output pane", hint_fg),
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

        import numpy as np
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

        # Short-circuit binary cells before ``str(value)`` allocates the
        # full escaped-hex repr. For a single 1 MB BLOB ``str()`` produces
        # ~5 MB of escaped chars, which then gets truncated to 80 chars —
        # the work is wasted and stalls page renders on tables with
        # image / audio / video columns.
        if isinstance(value, (bytes, bytearray, memoryview)):
            return Text(f"<binary: {len(value):,} bytes>", style="dim italic")
        # HuggingFace Image/Audio struct: ``{"bytes": <blob>, "path": ...}``
        if isinstance(value, dict):
            inner = value.get("bytes")
            if isinstance(inner, (bytes, bytearray, memoryview)):
                return Text(f"<binary: {len(inner):,} bytes>", style="dim italic")

        if isinstance(value, (np.ndarray, list, dict)):
            try:
                s = json.dumps(_normalize_json_like(value), ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                s = str(value)
        else:
            s = str(value)
        # Truncate before the replace chain so the per-cell cost stays
        # O(_MAX_CELL_LEN) instead of O(full-string-length). For huge text
        # cells (megabytes of content) the replace passes and downstream
        # Rich rendering were dominating page-render time.
        truncated = len(s) > DataBrowserScreen._MAX_CELL_LEN
        if truncated:
            s = s[: DataBrowserScreen._MAX_CELL_LEN]
        # Normalize whitespace to single spaces — collapses newlines
        # (which DataTable otherwise renders as hard line breaks,
        # expanding the row), tabs, and runs of spaces. Full multi-line
        # content stays available via Enter to inspect.
        s = " ".join(s.split())
        # Match the dim-italic styling of the ``NULL`` and ``<binary: N
        # bytes>`` placeholders — ``<binary: skipped>`` plays the same
        # role (a placeholder for stripped BLOB data, produced by the HF
        # loader's ``blob_strip=True``).
        if s == "<binary: skipped>":
            return Text(s, style="dim italic")
        if truncated:
            t = Text(s[: DataBrowserScreen._MAX_CELL_LEN - 3])
            t.append("...", style="dim")
            return t
        return Text(s)


class CellBrowserScreen(Screen[None]):
    """Full-screen viewer for inspecting a single cell value."""

    DEFAULT_CSS = """
    CellBrowserScreen {
        background: $background;
    }

    CellBrowserScreen TextArea {
        height: 1fr;
        margin: 0 1;
        border: solid white;
        background: $background;
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

    # Skip syntax highlighting above this many rendered chars — Pygments'
    # upfront pass blocks the UI for several seconds on multi-MB JSON.
    _MAX_HIGHLIGHT_CHARS = 200_000
    # Disable soft_wrap when any line exceeds this length — wrap recompute
    # on a single very long line dominates scroll/cursor cost in TextArea.
    _MAX_SOFT_WRAP_LINE = 500
    # Soft cap on the rendered display text. Beyond this, append a footer
    # so the TUI stays responsive for unusually large cells.
    _MAX_DISPLAY_CHARS = 1_000_000

    def __init__(
        self,
        *,
        column_name: str,
        row_number: int,
        value: object,
        dtype_str: str,
        display_text: str | None = None,
        language: str | None = None,
    ) -> None:
        super().__init__()
        self._column_name = column_name
        self._row_number = row_number
        self._dtype_str = dtype_str
        if display_text is None:
            self._display_text, self._language = self._format_value(value)
        else:
            self._display_text, self._language = display_text, language

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

        import numpy as np

        obj: object
        if isinstance(value, np.ndarray):
            obj = _normalize_json_like(value)
        elif isinstance(value, (dict, list)):
            obj = _normalize_json_like(value)
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

    @staticmethod
    def _format_value(value: object) -> tuple[str, str | None]:
        """Return (display_text, language) for the cell value.

        Output is soft-capped at ``_MAX_DISPLAY_CHARS``. Per-leaf truncation
        (``_MAX_JSON_LEAF``) keeps individual JSON strings bounded so
        pretty-printed JSON has short lines.
        """
        import pandas as pd_

        try:
            if value is None or pd_.isna(value):
                return "NULL", None
        except (TypeError, ValueError):
            pass

        if (raw := extract_media_bytes(value)) is not None:
            detected = detect_media(raw)
            label = detected.media_type if detected else "binary"
            preview = raw[:32].hex(" ")
            return f"<{label}: {len(raw):,} bytes>\n{preview} ...", None

        json_str = CellBrowserScreen._try_as_json(value)
        if json_str is not None:
            return CellBrowserScreen._cap_display(json_str), "json"

        s = str(value)
        if CellBrowserScreen._SQL_RE.match(s):
            return CellBrowserScreen._cap_display(s), "sql"
        if CellBrowserScreen._PY_RE.match(s):
            return CellBrowserScreen._cap_display(s), "python"
        return CellBrowserScreen._cap_display(s), None

    @classmethod
    def _cap_display(cls, text: str) -> str:
        """Truncate ``text`` to ``_MAX_DISPLAY_CHARS`` and append a footer."""
        if len(text) <= cls._MAX_DISPLAY_CHARS:
            return text
        return (
            text[: cls._MAX_DISPLAY_CHARS] + f"\n\n... (truncated to {cls._MAX_DISPLAY_CHARS:,} of {len(text):,} chars)"
        )

    def _resolved_language(self) -> str | None:
        if self._language not in QueryBrowserScreen._SUPPORTED_LANGUAGES:
            return None
        if len(self._display_text) > self._MAX_HIGHLIGHT_CHARS:
            return None
        return self._language

    def _resolved_soft_wrap(self) -> bool:
        max_line = max((len(line) for line in self._display_text.split("\n")), default=0)
        return max_line < self._MAX_SOFT_WRAP_LINE

    def compose(self) -> ComposeResult:
        yield TextArea(
            self._display_text,
            language=self._resolved_language(),
            read_only=True,
            show_line_numbers=True,
            soft_wrap=self._resolved_soft_wrap(),
        )
        yield Static(classes="cell-browser-status")
        yield Static(classes="cell-browser-gap")
        yield Static(classes="cell-browser-hint")

    def on_mount(self) -> None:
        text_area = self.query_one(TextArea)
        configure_code_text_area(text_area)
        self._refresh_status()

        hint = Text()
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back    ", style="dim")
        self.query_one(".cell-browser-hint", Static).update(hint)

    def _refresh_status(self) -> None:
        status = Text()
        status.append(
            f"{self._column_name} ({self._dtype_str})  |  Row {self._row_number:,}",
            style="dim",
        )
        self.query_one(".cell-browser-status", Static).update(status)

    def action_close_browser(self) -> None:
        self.dismiss()


class QueryBrowserScreen(Screen[None]):
    """Full-screen viewer for inspecting a query with scrolling."""

    DEFAULT_CSS = """
    QueryBrowserScreen {
        background: $background;
    }

    QueryBrowserScreen TextArea {
        height: 1fr;
        margin: 0 1;
        border: solid white;
        background: $background;
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
    _SUPPORTED_LANGUAGES = frozenset(
        {
            "bash",
            "css",
            "go",
            "html",
            "java",
            "javascript",
            "json",
            "markdown",
            "python",
            "regex",
            "rust",
            "sql",
            "toml",
            "xml",
            "yaml",
        }
    )

    def __init__(self, *, title: str, query: str, lexer: str = "sql") -> None:
        super().__init__()
        self._title = title
        self._query = query
        self._lexer = normalize_query_lexer(lexer)

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
        configure_code_text_area(text_area)

        hint_text = Text()
        hint_text.append("Esc", style=KEY_HINT)
        hint_text.append(" Back    ", style="dim")
        self.query_one(".query-browser-hint", Static).update(hint_text)

    def action_close_browser(self) -> None:
        self.dismiss()


class ChartBrowserScreen(Screen[None]):
    """Full-screen viewer for inspecting a chart at terminal size."""

    DEFAULT_CSS = """
    ChartBrowserScreen {
        background: $background;
    }

    ChartBrowserScreen .chart-browser-content {
        height: 1fr;
        margin: 0 1;
        padding: 1 2;
        background: $background;
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

    def __init__(self, *, title: str, df: "pd.DataFrame", vegalite_spec: dict[str, object]) -> None:
        super().__init__()
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
        from tabulaflow.app.tui.rendering import build_chart

        content_width = max(20, self._content.size.width - 4)
        content_height = max(10, self._content.size.height)
        renderable = build_chart(self._df, self._vegalite_spec, content_width, content_height)
        self._content.update(renderable)

        hint = Text()
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back    ", style="dim")
        self._hint.update(hint)


# Node data stored in Tree nodes to identify what each node represents.
_NODE_KIND_DB = "db"
_NODE_KIND_SCHEMA = "schema"
_NODE_KIND_TABLE = "table"
_NODE_KIND_COLUMN = "column"
_NODE_KIND_GRAPH_GROUP = "graph_group"
_NODE_KIND_GRAPH_NODE = "graph_node"
_NODE_KIND_GRAPH_RELATIONSHIP = "graph_relationship"
_NODE_KIND_GRAPH_PROPERTY = "graph_property"

_GRAPH_NODE_TYPES = "node_types"
_GRAPH_REL_TYPES = "relationship_types"
_GRAPH_GROUP_LABELS = {
    _GRAPH_NODE_TYPES: "Node Types",
    _GRAPH_REL_TYPES: "Relationship Types",
}
