"""Full-screen modal explorers — the data / cell / query / chart / schema browser
screens (pushed on demand) and output-pane artifact helpers. Distinct from the
inline chat-flow widgets in ``widgets.py``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Static, TextArea

from tabulaflow.app.config import APP_CONFIG_PATH, ModelOption, load_app_config, update_app_config
from tabulaflow.app.theme import ACCENT, ACCENT_BOLD, DRACULA_TRANSPARENT, ERROR, FK_MARKER, KEY_HINT, PK_MARKER


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any

    import pandas as pd

    from tabulaflow.app.session import SessionState


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


# ---------------------------------------------------------------------------
# Output-pane helpers for manual table previews
# ---------------------------------------------------------------------------


def _show_path(
    record: object,
    app: object,
    *,
    status: "Callable[[Text], None]",
    title: str | None = None,
) -> None:
    """Show a dumped record-data payload in the live results pane.

    Manual "send to output pane" actions route here so one pane accumulates
    both agent results and explorer views.
    """
    try:
        shown = bool(app.view_card_in_pane(record, title=title))  # type: ignore[attr-defined]
    except Exception:
        shown = False
    if shown:
        status(Text("sent to output pane", style="dim"))
    else:
        status(Text("results pane unavailable; data preview was written", style="dim"))


def send_table_to_output_pane(
    df: "pd.DataFrame",
    title: str,
    app: object,
    *,
    status: "Callable[[Text], None]",
) -> "Path | None":
    """Render ``df`` as pane record data and send it to the output pane.

    Returns the written data path on success, or ``None`` on failure.
    """
    from types import SimpleNamespace

    from tabulaflow.app.pane import render_record_data

    try:
        pane_dir: Path = app._runtime_paths.pane_dir  # type: ignore[attr-defined]
    except AttributeError:
        status(Text("save failed: no pane dir", style=ERROR))
        return None
    try:
        card = render_record_data(
            SimpleNamespace(df=df, chart_spec=None, query=None, label=None, query_lexer="sql"),
            pane_dir,
        )
    except OSError as exc:
        status(Text(f"write failed: {exc}", style=ERROR))
        return None
    except Exception as exc:
        status(Text(f"render failed: {exc}", style=ERROR))
        return None
    if card is None:
        status(Text("render failed: no table data", style=ERROR))
        return None
    _show_path(card, app, status=status, title=title or "Table preview")
    return pane_dir / f"{card['id']}.data.json"


# ---------------------------------------------------------------------------
# Data browser screen
# ---------------------------------------------------------------------------


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
        send_table_to_output_pane(self._df, self._title, self.app, status=self._set_status_message)

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


# ---------------------------------------------------------------------------
# Cell value browser screen
# ---------------------------------------------------------------------------


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

        if isinstance(value, (bytes, bytearray, memoryview)):
            from tabulaflow.app.media import sniff_binary

            raw = bytes(value)
            sniffed = sniff_binary(raw)
            label = sniffed[1] if sniffed else "binary"
            preview = raw[:32].hex(" ")
            return f"<{label}: {len(raw):,} bytes>\n{preview} ...", None

        # HuggingFace Image/Audio struct: surface the blob preview rather
        # than the JSON tree of ``{"bytes": ..., "path": ...}``.
        if isinstance(value, dict):
            inner = value.get("bytes")
            if isinstance(inner, (bytes, bytearray, memoryview)):
                from tabulaflow.app.media import sniff_binary

                raw = bytes(inner)
                sniffed = sniff_binary(raw)
                label = sniffed[1] if sniffed else "binary"
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
        text_area.register_theme(DRACULA_TRANSPARENT)
        text_area.theme = "dracula-transparent"
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


# ---------------------------------------------------------------------------
# Query browser screen
# ---------------------------------------------------------------------------


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
        hint_text.append("Esc", style=KEY_HINT)
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
        from tabulaflow.app.display import build_chart

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


class _NodeData:
    """Metadata attached to each Tree node."""

    __slots__ = ("kind", "alias", "schema_name", "table_name", "column_name", "path", "status_text")

    def __init__(
        self,
        kind: str,
        alias: str,
        schema_name: str | None = None,
        table_name: str | None = None,
        column_name: str | None = None,
        path: tuple[str | None, ...] | None = None,
        status_text: str | None = None,
    ) -> None:
        self.kind = kind
        self.alias = alias
        self.schema_name = schema_name
        self.table_name = table_name
        self.column_name = column_name
        self.path = path
        self.status_text = status_text


_NodePath = tuple[str | None, ...]


class _ExplorerState:
    """Session-scoped UI state for ``SchemaBrowserScreen``.

    Held on ``TabulaflowApp`` and passed by reference into each freshly-created
    schema browser. The screen reads ``expansion`` while building nodes
    and updates state continuously via tree event handlers — no
    snapshot-on-close step needed.

    ``expansion`` is a *dict*, not a set: presence of a path means "the
    user has seen this node," and the value is its expansion state.
    Unknown paths fall through to the build-time default. This is what
    distinguishes "user explicitly collapsed" (path → False) from "user
    never saw this node" (path absent → use default), so newly-connected
    DBs honor their auto-expand default instead of being collapsed by
    a missing entry.
    """

    __slots__ = ("expansion", "cursor")

    def __init__(self) -> None:
        self.expansion: dict[_NodePath, bool] = {}
        self.cursor: _NodePath | None = None


class SchemaBrowserScreen(Screen[None]):
    """Full-screen tree browser for exploring connected database schemas."""

    DEFAULT_CSS = """
    SchemaBrowserScreen {
        background: $background;
    }

    SchemaBrowserScreen #browse-tree {
        height: 1fr;
        padding: 1 2;
        background: $background;
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

    SchemaBrowserScreen #browse-tree:focus {
        outline: none;
        background-tint: transparent 0%;
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

    SchemaBrowserScreen .schema-browser-status {
        padding: 0 2;
        color: #f5f5f5;
    }

    SchemaBrowserScreen .schema-browser-gap {
        height: 1;
    }

    SchemaBrowserScreen #browse-hint {
        dock: bottom;
        padding: 0 2;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close_browser", "Back", show=True),
        Binding("left", "collapse_node", "Collapse", show=False, priority=True),
        Binding("right", "expand_node", "Expand", show=False, priority=True),
        Binding("enter", "open_preview", "Preview table", show=False, priority=True),
        Binding("r", "refresh_schema", "Refresh", show=True),
    ]

    _PREVIEW_ROW_CAP = 50

    def __init__(
        self,
        *,
        registry: object,
        alias: str | None = None,
        state: _ExplorerState | None = None,
    ) -> None:
        super().__init__()
        from tabulaflow.core.db_connector.db_registry import DBRegistry

        assert isinstance(registry, DBRegistry)
        self._registry: DBRegistry = registry
        self._filter_alias = alias
        self._state = state if state is not None else _ExplorerState()
        self._refreshing = False
        self._status = Static(classes="schema-browser-status")
        self._gap = Static(classes="schema-browser-gap")
        self._hint = Static(id="browse-hint")

    def compose(self) -> ComposeResult:
        from textual.widgets import Tree

        tree: Tree[_NodeData] = Tree("Databases", id="browse-tree")
        tree.show_root = False
        tree.guide_depth = 3
        tree.auto_expand = False

        yield tree
        yield self._status
        yield self._gap
        yield self._hint

    def on_mount(self) -> None:
        # Snapshot the saved cursor before any side effects can clobber it.
        # ``on_tree_node_highlighted`` rewrites ``_state.cursor`` whenever
        # the cursor moves, including the implicit move that Textual does
        # to the first line on initial render — without this local, that
        # would overwrite the path we're about to restore to.
        saved_cursor = self._state.cursor
        self._build_tree()
        self._update_status()
        self._update_hint()
        tree = self.query_one("#browse-tree")
        tree.focus()
        # Cursor restore is deferred to after the next refresh: ancestor
        # expansion (built into the tree but applied lazily by Textual)
        # only populates ``_tree_lines`` on render. Running ``move_cursor``
        # before that leaves it as a silent no-op for collapsed-by-default
        # subtrees (the workspace alias case).
        if saved_cursor is not None:
            self.call_after_refresh(self._restore_cursor, saved_cursor)
        elif not self._state.expansion:
            # Genuine first open — nothing to restore, focus the first
            # table so Enter previews immediately.
            self.call_after_refresh(self._focus_first_table)

    @staticmethod
    def _node_path(data: "_NodeData | None") -> _NodePath | None:
        if data is None:
            return None
        if data.path is not None:
            return data.path
        return (data.alias, data.schema_name, data.table_name, data.column_name)

    def _expand_for(self, path: _NodePath, default: bool) -> bool:
        """Resolve expansion state for a node: the user's last-recorded
        value if known, otherwise the construction-time default.
        """
        return self._state.expansion.get(path, default)

    def _walk_nodes(self) -> "Iterator[Any]":
        """Pre-order traversal of every tree node below the (hidden) root."""
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        stack: list[Any] = list(reversed(tree.root.children))
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def _find_node_by_path(self, path: _NodePath) -> "Any | None":
        for node in self._walk_nodes():
            if self._node_path(node.data) == path:
                return node
        return None

    def _first_table_node(self) -> "Any | None":
        for node in self._walk_nodes():
            data: _NodeData | None = node.data
            if data is not None and data.kind == _NODE_KIND_TABLE:
                return node
        return None

    def _restore_cursor(self, saved: _NodePath | None) -> None:
        """Move the cursor to the saved node, if its path still resolves.

        Deliberately does not fall back to the first table or force
        ancestor expansion when the path is missing — the build phase
        already put the tree in the user's saved collapse state, and
        overriding that to make a fallback cursor visible would silently
        undo an explicit collapse (e.g., after a disconnect dropped the
        saved cursor's DB).
        """
        if saved is None:
            return
        target = self._find_node_by_path(saved)
        if target is None:
            return
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        tree.move_cursor(target)
        tree.scroll_to_node(target)

    def _focus_first_table(self) -> None:
        """First-open default: land the cursor on the first table so Enter
        previews immediately. Force-expands ancestors because on a true
        first open there is no user-intended collapse state to respect.
        """
        target = self._first_table_node()
        if target is None:
            return
        from textual.widgets import Tree

        tree = self.query_one("#browse-tree", Tree)
        parent = target.parent
        while parent is not None and parent is not tree.root:
            parent.expand()
            parent = parent.parent
        tree.move_cursor(target)
        tree.scroll_to_node(target)

    # -- event handlers: keep ``_state`` current as the user navigates ----

    def on_tree_node_expanded(self, event: "Any") -> None:
        path = self._node_path(event.node.data)
        if path is not None:
            self._state.expansion[path] = True

    def on_tree_node_collapsed(self, event: "Any") -> None:
        path = self._node_path(event.node.data)
        if path is not None:
            self._state.expansion[path] = False

    # -- tree construction ---------------------------------------------------

    def _visible_aliases(self) -> list[str]:
        """Sorted aliases the tree shows: all registered, or just the filter."""
        aliases = self._registry.list_aliases()
        if self._filter_alias is not None:
            aliases = [a for a in aliases if a == self._filter_alias]
        aliases.sort()
        return aliases

    @staticmethod
    def _visible_tables(alias: str, schema: object) -> list[Any]:
        """Tables the tree shows for ``alias``. The workspace hides internal/scratch
        schemas (conventionally ``_``-prefixed); every other DB shows all tables.

        Shared by ``_build_tree`` and ``_update_status`` so the status-bar count
        always matches what the tree actually renders.
        """
        from tabulaflow.core.types import SQLSchema

        assert isinstance(schema, SQLSchema)
        tables = list(schema.tables)
        if alias == "workspace":
            tables = [t for t in tables if not (t.schema_name and t.schema_name.startswith("_"))]
        return tables

    def _build_tree(self) -> None:
        from textual.widgets import Tree

        from tabulaflow.core.types import PropertyGraphSchema, SQLSchema, SQLTableSchema

        tree = self.query_one("#browse-tree", Tree)

        for alias in self._visible_aliases():
            connector = self._registry.get(alias)
            schema = connector.schema
            if isinstance(schema, PropertyGraphSchema):
                self._add_graph_db_node(tree.root, alias, connector, schema)
                continue
            if not isinstance(schema, SQLSchema):
                continue

            db_label = Text()
            db_label.append(alias, style="bold")
            dialect = schema.dialect or getattr(connector, "language", None)
            if dialect:
                db_label.append(f"  {dialect}", style="dim")

            db_node = tree.root.add(
                db_label,
                data=_NodeData(kind=_NODE_KIND_DB, alias=alias),
                expand=self._expand_for((alias, None, None, None), True),
            )

            tables: list[SQLTableSchema] = self._visible_tables(alias, schema)
            schema_names: set[str | None] = {t.schema_name for t in tables}
            has_schemas = schema_names != {None}

            if has_schemas:
                groups: dict[str | None, list[SQLTableSchema]] = {}
                for t in tables:
                    groups.setdefault(t.schema_name, []).append(t)
                for sn in sorted(groups, key=lambda s: (s is None, s or "")):
                    sn_label = Text()
                    sn_label.append(sn or "(default)", style="bold")
                    sn_label.append("  schema", style="dim")
                    schema_node = db_node.add(
                        sn_label,
                        data=_NodeData(kind=_NODE_KIND_SCHEMA, alias=alias, schema_name=sn),
                        expand=self._expand_for((alias, sn, None, None), True),
                    )
                    for t in sorted(groups[sn], key=lambda t: t.name):
                        self._add_table_node(schema_node, alias, t)
            else:
                for t in sorted(tables, key=lambda t: t.name):
                    self._add_table_node(db_node, alias, t)

    def _add_graph_db_node(self, parent: object, alias: str, connector: object, schema: object) -> None:
        from tabulaflow.core.types import PropertyGraphSchema

        assert isinstance(schema, PropertyGraphSchema)
        parent_node: Any = parent
        node_types_label = _GRAPH_GROUP_LABELS[_GRAPH_NODE_TYPES]
        rel_types_label = _GRAPH_GROUP_LABELS[_GRAPH_REL_TYPES]

        db_label = Text()
        db_label.append(alias, style="bold")
        backend = getattr(connector, "backend", None)
        if backend:
            db_label.append(f"  {backend}", style="dim")

        db_node = parent_node.add(
            db_label,
            data=_NodeData(
                kind=_NODE_KIND_DB,
                alias=alias,
                path=(alias, None, None, None),
                status_text=(
                    f"{alias}  |  {len(schema.nodes):,} {node_types_label}  |  "
                    f"{len(schema.relationships):,} {rel_types_label}"
                ),
            ),
            expand=self._expand_for((alias, None, None, None), False),
        )

        nodes = db_node.add(
            Text(node_types_label, style="bold"),
            data=_NodeData(
                kind=_NODE_KIND_GRAPH_GROUP,
                alias=alias,
                path=(alias, _GRAPH_NODE_TYPES, None, None),
                status_text=f"{alias} > {node_types_label}  |  {len(schema.nodes):,} labels",
            ),
            expand=self._expand_for((alias, _GRAPH_NODE_TYPES, None, None), True),
        )
        for node in sorted(schema.nodes, key=lambda n: n.label):
            label_node = nodes.add(
                Text(node.label),
                data=_NodeData(
                    kind=_NODE_KIND_GRAPH_NODE,
                    alias=alias,
                    path=(alias, _GRAPH_NODE_TYPES, node.label, None),
                    status_text=(
                        f"{alias} > {node_types_label} > {node.label}  |  {len(node.properties):,} properties"
                    ),
                ),
                expand=self._expand_for((alias, _GRAPH_NODE_TYPES, node.label, None), False),
            )
            self._add_graph_properties(
                label_node,
                alias,
                identity_path=(_GRAPH_NODE_TYPES, node.label),
                display_path=(node_types_label, node.label),
                properties=node.properties,
            )

        relationships = db_node.add(
            Text(rel_types_label, style="bold"),
            data=_NodeData(
                kind=_NODE_KIND_GRAPH_GROUP,
                alias=alias,
                path=(alias, _GRAPH_REL_TYPES, None, None),
                status_text=f"{alias} > {rel_types_label}  |  {len(schema.relationships):,} types",
            ),
            expand=self._expand_for((alias, _GRAPH_REL_TYPES, None, None), True),
        )
        for rel in sorted(schema.relationships, key=lambda rel: rel.label):
            rel_path = (_GRAPH_REL_TYPES, rel.label, None, None)
            rel_node = relationships.add(
                Text(rel.label),
                data=_NodeData(
                    kind=_NODE_KIND_GRAPH_RELATIONSHIP,
                    alias=alias,
                    path=(alias, *rel_path),
                    status_text=(f"{alias} > {rel_types_label} > {rel.label}  |  {len(rel.properties):,} properties"),
                ),
                expand=self._expand_for((alias, *rel_path), False),
            )
            self._add_graph_properties(
                rel_node,
                alias,
                identity_path=rel_path,
                display_path=(rel_types_label, rel.label),
                properties=rel.properties,
            )

    def _add_graph_properties(
        self,
        parent: object,
        alias: str,
        *,
        identity_path: tuple[str | None, ...],
        display_path: tuple[str, ...],
        properties: list[Any],
    ) -> None:
        from tabulaflow.core.types import GraphPropertySchema

        parent_node: Any = parent
        name_width = max((len(prop.name) for prop in properties if isinstance(prop, GraphPropertySchema)), default=0)
        for prop in properties:
            assert isinstance(prop, GraphPropertySchema)
            parent_label = " > ".join(display_path)
            parent_node.add_leaf(
                Text.assemble(prop.name.ljust(name_width), (f"  {prop.dtype}", "dim")),
                data=_NodeData(
                    kind=_NODE_KIND_GRAPH_PROPERTY,
                    alias=alias,
                    path=(alias, *identity_path, prop.name),
                    status_text=f"{alias} > {parent_label} > {prop.name}  |  {prop.dtype}",
                ),
            )

    def _add_table_node(self, parent: object, alias: str, table: object) -> None:
        from tabulaflow.core.types import SQLTableSchema

        assert isinstance(table, SQLTableSchema)
        parent_node: Any = parent

        t_label = Text()
        t_label.append(table.name)
        if table.is_view:
            t_label.append("  view", style="dim")

        table_node = parent_node.add(
            t_label,
            data=_NodeData(
                kind=_NODE_KIND_TABLE,
                alias=alias,
                schema_name=table.schema_name,
                table_name=table.name,
            ),
            expand=self._expand_for((alias, table.schema_name, table.name, None), False),
        )

        name_width = max((len(col.name) for col in table.columns), default=0)
        for col in table.columns:
            c_label = Text()
            c_label.append(col.name.ljust(name_width))
            c_label.append(f"  {col.dtype}", style="dim")
            if col.primary_key_type:
                c_label.append(" PK", style=PK_MARKER)
            if col.foreign_keys:
                c_label.append(" FK", style=FK_MARKER)
            table_node.add_leaf(
                c_label,
                data=_NodeData(
                    kind=_NODE_KIND_COLUMN,
                    alias=alias,
                    schema_name=table.schema_name,
                    table_name=table.name,
                    column_name=col.name,
                ),
            )

    # -- actions --------------------------------------------------------------

    async def action_open_preview(self) -> None:
        """Open DataBrowserScreen for the table under the cursor.

        For writable SQL connectors (``read_only=False``), runs a live
        ``SELECT * ... LIMIT 10`` so the preview reflects the current
        database state.  For read-only or non-SQL connectors, falls back
        to the cached ``sampled_df``.
        """
        from textual.widgets import Tree

        from tabulaflow.core.types import SQLSchema

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
        # SQLSchema implies a SQL connector; the live preview path uses
        # SQLAlchemy ``Executable`` which only ``BaseSQLDBConnector``
        # accepts.
        assert connector.connector_type == "sql"
        assert node_data.table_name is not None
        table = next(
            (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
            None,
        )
        if table is None:
            return

        import pandas as pd
        import sqlalchemy

        tbl = sqlalchemy.table(
            node_data.table_name,
            schema=node_data.schema_name,
        )
        stmt = sqlalchemy.select("*").select_from(tbl).limit(self._PREVIEW_ROW_CAP)
        self._status.update(Text("Loading preview...", style="dim"))
        result = await connector.run_query_async(stmt, timeout=30)
        if result.error is not None:
            msg = result.error.message.replace("\n", " ").strip()
            self._status.update(Text.from_markup(f"[{ERROR}]Preview error:[/] {msg}"))
            return
        self._update_status()
        df = result.df if result.df is not None else pd.DataFrame()

        suffix = f"(first {self._PREVIEW_ROW_CAP} rows)"
        title = (
            f"{node_data.alias}: {node_data.schema_name}.{node_data.table_name} {suffix}"
            if node_data.schema_name
            else f"{node_data.alias}: {node_data.table_name} {suffix}"
        )
        self.app.push_screen(DataBrowserScreen(title=title, df=df))

    # -- actions & hints -----------------------------------------------------

    def action_close_browser(self) -> None:
        self.dismiss()

    async def action_refresh_schema(self) -> None:
        """Re-introspect the visible database(s) and rebuild the tree in place.

        Re-reads each shown connector's schema directly from the live
        database, so DDL run outside the agent (or by it) shows up here on
        demand. Cursor and expansion state are preserved across the
        rebuild. Re-introspection can be slow on cloud warehouses, so the
        key is a no-op while a refresh is already in flight.
        """
        from textual.widgets import Tree

        if self._refreshing:
            return
        self._refreshing = True
        # Snapshot before clearing: ``tree.clear()`` moves the cursor and
        # fires ``on_tree_node_highlighted``, which would overwrite
        # ``_state.cursor`` (same hazard guarded against in ``on_mount``).
        saved_cursor = self._state.cursor
        self._status.update(Text("Refreshing schema...", style="dim"))
        try:
            failures: list[str] = []
            for alias in self._visible_aliases():
                connector = self._registry.get(alias)
                try:
                    await connector.refresh_schema_async()
                except Exception as e:  # noqa: BLE001 - surface, don't crash the screen
                    failures.append(f"{alias} ({type(e).__name__})")

            tree = self.query_one("#browse-tree", Tree)
            tree.clear()
            self._build_tree()
            self._update_status()
            self._update_hint()
            self.call_after_refresh(self._restore_cursor, saved_cursor)

            # On success the rebuilt tree is the feedback; only surface
            # failures. Deferred so it lands after ``_restore_cursor``'s
            # highlight re-runs ``_update_status`` (which would clobber it).
            if failures:
                msg = "Schema refresh failed: " + ", ".join(failures)
                self.call_after_refresh(
                    self._status.update,
                    Text.from_markup(f"[{ERROR}]{msg}[/]"),
                )
        finally:
            self._refreshing = False

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

    def on_tree_node_highlighted(self, event: "Any") -> None:
        """Update hint/status bars and record cursor position in state."""
        self._state.cursor = self._node_path(event.node.data)
        self._update_status()
        self._update_hint()

    def _cursor_has_preview(self) -> bool:
        """Return True if the cursor is on a table node with sampled_df."""
        from textual.widgets import Tree

        from tabulaflow.core.types import SQLSchema

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

    def _update_status(self) -> None:
        """Update the status bar with table/column/row counts for the highlighted scope."""
        from textual.widgets import Tree

        from tabulaflow.core.types import SQLSchema

        tree = self.query_one("#browse-tree", Tree)
        try:
            node = tree._tree_lines[tree.cursor_line].path[-1]
        except (IndexError, AttributeError):
            self._status.update(Text(""))
            return

        node_data: _NodeData | None = node.data
        if node_data is None:
            self._status.update(Text(""))
            return
        if node_data.status_text is not None:
            self._status.update(Text(node_data.status_text, style="dim"))
            return

        parts: list[str] = []
        connector = self._registry.get(node_data.alias)
        schema = connector.schema
        if not isinstance(schema, SQLSchema):
            self._status.update(Text(""))
            return

        if node_data.kind == _NODE_KIND_DB:
            tables = self._visible_tables(node_data.alias, schema)
            parts.append(node_data.alias)
            parts.append(f"{len(tables):,} tables")

        elif node_data.kind == _NODE_KIND_SCHEMA:
            tables = [
                t for t in self._visible_tables(node_data.alias, schema) if t.schema_name == node_data.schema_name
            ]
            path = f"{node_data.alias} > {node_data.schema_name or '(default)'}"
            parts.append(path)
            parts.append(f"{len(tables):,} tables")

        elif node_data.kind in (_NODE_KIND_TABLE, _NODE_KIND_COLUMN):
            table = next(
                (t for t in schema.tables if t.name == node_data.table_name and t.schema_name == node_data.schema_name),
                None,
            )
            if table:
                if node_data.schema_name:
                    path = f"{node_data.alias} > {node_data.schema_name}.{node_data.table_name}"
                else:
                    path = f"{node_data.alias} > {node_data.table_name}"
                parts.append(path)
                parts.append(f"{len(table.columns):,} columns")
                if table.num_rows is not None:
                    parts.append(f"{table.num_rows:,} rows")

        if parts:
            self._status.update(Text("  |  ".join(parts), style="dim"))
        else:
            self._status.update(Text(""))

    def _update_hint(self) -> None:
        hint_fg = "dim"
        hint = Text()
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back", style=hint_fg)
        if self._cursor_has_preview():
            hint.append("    ", style=hint_fg)
            hint.append("↵", style=KEY_HINT)
            hint.append(" Preview table", style=hint_fg)
        hint.append("    ", style=hint_fg)
        hint.append("R", style=KEY_HINT)
        hint.append(" Refresh", style=hint_fg)
        self._hint.update(hint)


# ---------------------------------------------------------------------------
# Config screen
# ---------------------------------------------------------------------------


class _SetProfile(Protocol):
    def __call__(self, *, model: str, reasoning_effort: str) -> None: ...


@dataclass(frozen=True)
class _ConfigModelSection:
    kind: str
    effort_kind: str
    title: str
    options: list[ModelOption]
    rows: list[Static]
    current_model: Callable[[], str]
    api_key: Callable[[], str | None]
    supported_efforts: Callable[[], tuple[str, ...]]
    current_effort: Callable[[], str]
    set_profile: _SetProfile


class ConfigScreen(Screen[None]):
    """Full-screen editor for session preferences (main/subagent models, reasoning effort).

    Renders the whole model catalog with the reasoning-effort chips nested
    under the active main model, then a separate subagent model section:
    up/down moves the cursor, enter applies the model under it, left/right
    cycles the main-agent effort. Changes apply to the live session immediately
    and persist to ``~/.tabulaflow/app_config.json`` as the default for new
    sessions.
    """

    DEFAULT_CSS = """
    ConfigScreen {
        background: $background;
    }

    ConfigScreen #config-body {
        padding: 1 2;
    }

    ConfigScreen .config-row {
        height: auto;
    }

    ConfigScreen #config-hint {
        dock: bottom;
        padding: 0 1;
        color: #f5f5f5;
        background: #2a2a2a;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Back", show=True),
        Binding("up", "cursor_move(-1)", "Move", show=False),
        Binding("down", "cursor_move(1)", "Move", show=False),
        Binding("left", "cycle(-1)", "Change", show=False),
        Binding("right", "cycle(1)", "Change", show=False),
        Binding("enter", "select", "Select", show=False),
    ]

    def __init__(self, session: SessionState, on_change: Callable[[], None]) -> None:
        super().__init__()
        self._session = session
        self._on_change = on_change
        app_config = load_app_config()
        options = list(app_config.model_options)
        if all(o.model != session.model for o in options):
            options.insert(0, ModelOption(model=session.model, label=session.model))
        self._options = options
        subagent_options = list(app_config.subagent_model_options)
        if all(o.model != session.subagent_model for o in subagent_options):
            subagent_options.insert(0, ModelOption(model=session.subagent_model, label=session.subagent_model))
        self._subagent_options = subagent_options
        active = next(i for i, o in enumerate(options) if o.model == session.model)
        # Cursor is a slot, not an index, so it survives the effort row moving
        # to a newly selected model.
        self._cursor: tuple[str, int] = ("model", active)
        # Set when applying a model fails (e.g. missing provider credentials):
        # (slot kind, option index, provider error). Rendered inline under the
        # attempted row.
        self._select_error: tuple[str, int, str] | None = None
        self._rows = [Static(classes="config-row") for _ in options]
        self._subagent_rows = [Static(classes="config-row") for _ in subagent_options]
        self._sections = (
            _ConfigModelSection(
                kind="model",
                effort_kind="effort",
                title="Model",
                options=self._options,
                rows=self._rows,
                current_model=lambda: self._session.model,
                api_key=lambda: self._session.api_key,
                supported_efforts=lambda: self._session.supported_efforts,
                current_effort=lambda: self._session.reasoning_effort,
                set_profile=self._session.set_main_profile,
            ),
            _ConfigModelSection(
                kind="subagent_model",
                effort_kind="subagent_effort",
                title="Subagent Model",
                options=self._subagent_options,
                rows=self._subagent_rows,
                current_model=lambda: self._session.subagent_model,
                api_key=lambda: self._session.subagent_api_key,
                supported_efforts=lambda: self._session.subagent_supported_efforts,
                current_effort=lambda: self._session.subagent_reasoning_effort,
                set_profile=self._session.set_subagent_profile,
            ),
        )

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical

        config_path = APP_CONFIG_PATH.replace(str(Path.home()), "~", 1)
        title = Text()
        title.append("Config", style=ACCENT_BOLD)
        title.append(f" · auto-saved to {config_path}", style="dim")
        with Vertical(id="config-body"):
            yield Static(title)
            yield Static("")
            for n, section in enumerate(self._sections):
                if n:
                    yield Static("")
                yield Static(Text(section.title, style="bold"))
                yield from section.rows
        yield Static(self._hint_text(), id="config-hint")

    def on_mount(self) -> None:
        self._refresh()

    def _slots(self) -> list[tuple[str, int]]:
        """Cursor-reachable rows: every model, plus the effort row nested under
        the active model when it supports reasoning efforts."""
        slots: list[tuple[str, int]] = []
        for section in self._sections:
            for i, option in enumerate(section.options):
                slots.append((section.kind, i))
                if option.model == section.current_model() and section.supported_efforts():
                    slots.append((section.effort_kind, i))
        return slots

    def _render_row(self, i: int) -> Text:
        return self._render_model_row(self._sections[0], i)

    def _render_subagent_row(self, i: int) -> Text:
        return self._render_model_row(self._sections[1], i)

    def _render_model_row(self, section: _ConfigModelSection, i: int) -> Text:
        option = section.options[i]
        active = option.model == section.current_model()
        selected = self._cursor == (section.kind, i)
        t = Text()
        t.append("❯ " if selected else "  ", style=ACCENT_BOLD)
        t.append("● " if active else "  ", style=ACCENT)
        # Mint iff active, bold iff under the cursor — two independent channels.
        if active:
            label_style = ACCENT_BOLD if selected else ACCENT
        else:
            label_style = "bold" if selected else ""
        t.append(option.label, style=label_style)
        provider = option.model.partition(":")[0] if ":" in option.model else ""
        if provider and option.model != option.label:
            t.append(f" · {provider}", style="dim")
        if active:
            key = section.api_key()
            if key is not None and len(key) >= 12:
                t.append(f" · API key {key[:3]}***{key[-4:]}", style="dim")
        if active and section.supported_efforts():
            t.append("\n")
            t.append_text(self._render_effort_line(section, i))
        if self._select_error is not None and self._select_error[0] == section.kind and self._select_error[1] == i:
            t.append("\n")
            t.append(f"      {self._select_error[2]}", style=ERROR)
        return t

    def _render_effort_line(self, section: _ConfigModelSection, i: int) -> Text:
        option = section.options[i]
        selected = self._cursor == (section.effort_kind, i)
        t = Text()
        t.append("❯ " if selected else "  ", style=ACCENT_BOLD)
        t.append("    ")
        t.append("effort: ", style="dim")
        for effort in section.supported_efforts():
            current = effort == section.current_effort()
            label = f" {effort} (recommended) " if effort == option.recommended_effort else f" {effort} "
            t.append(label, style=(ACCENT_BOLD if selected else ACCENT) if current else "dim")
            t.append(" ")
        return t

    def _hint_text(self) -> Text:
        hint = Text()
        hint.append("↑↓", style=KEY_HINT)
        hint.append(" Move    ", style="dim")
        hint.append("↵", style=KEY_HINT)
        hint.append(" Select model    ", style="dim")
        hint.append("←→", style=KEY_HINT)
        hint.append(" Change effort    ", style="dim")
        hint.append("Esc", style=KEY_HINT)
        hint.append(" Back", style="dim")
        return hint

    def _refresh(self) -> None:
        for section in self._sections:
            for i, row in enumerate(section.rows):
                row.update(self._render_model_row(section, i))

    def _persist(self) -> None:
        update_app_config(
            model=self._session.model,
            reasoning_effort=self._session.reasoning_effort,
            subagent_model=self._session.subagent_model,
            subagent_reasoning_effort=self._session.subagent_reasoning_effort,
        )
        self._on_change()
        self._refresh()

    def action_cursor_move(self, delta: int) -> None:
        slots = self._slots()
        i = slots.index(self._cursor)
        self._cursor = slots[max(0, min(len(slots) - 1, i + delta))]
        self._refresh()

    def action_select(self) -> None:
        kind, i = self._cursor
        section = self._section_for_kind(kind)
        if section is None or kind != section.kind:
            return
        option = section.options[i]
        changed = option.model != section.current_model()
        reasoning_effort = (
            option.recommended_effort if changed and option.recommended_effort is not None else section.current_effort()
        )
        self._select_error = None
        try:
            section.set_profile(model=option.model, reasoning_effort=reasoning_effort)
        except Exception as e:
            # ``set_profile`` is transactional — the previous profile is still
            # active. Report why this one couldn't be applied; nothing persists.
            self._select_error = (kind, i, str(e))
            self._refresh()
            return
        # Land on the chips that just appeared under the selection, so ←→
        # tunes the effort without an intervening ↓.
        if section.supported_efforts():
            self._cursor = (section.effort_kind, i)
        self._persist()

    def action_cycle(self, delta: int) -> None:
        kind, _ = self._cursor
        section = self._section_for_kind(kind)
        if section is None or kind != section.effort_kind:
            return
        efforts = section.supported_efforts()
        current = section.current_effort()
        j = (efforts.index(current) + delta) % len(efforts) if current in efforts else 0
        section.set_profile(model=section.current_model(), reasoning_effort=efforts[j])
        self._persist()

    def _section_for_kind(self, kind: str) -> _ConfigModelSection | None:
        for section in self._sections:
            if kind in {section.kind, section.effort_kind}:
                return section
        return None

    def action_close(self) -> None:
        self.app.pop_screen()
