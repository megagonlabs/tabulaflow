"""Full-screen modal explorers — the data / cell / query / chart / schema browser
screens (pushed on demand) and the browser-open helpers. Distinct from the inline
chat-flow widgets in ``widgets.py``.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from rich.text import Text
from pathlib import Path

from textual.binding import Binding
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static, TextArea

from tabulaflow.app.theme import ACCENT, DRACULA_TRANSPARENT, ERROR, FK_MARKER, KEY_HINT, PK_MARKER


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any

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


# ---------------------------------------------------------------------------
# Browser-open helpers (used by Data and Cell browsers)
# ---------------------------------------------------------------------------


def _open_path_in_browser(path: Path, *, status: "Callable[[Text], None]") -> bool:
    """Open ``path`` in the system browser, reporting via ``status``.

    ``webbrowser_open.open`` returns None and raises on failure; we use
    absence of exception (combined with a default-browser probe for the
    headless case) as the success signal.
    """
    import webbrowser_open

    try:
        webbrowser_open.open(path.absolute().as_uri())
        opened = webbrowser_open.get_default_browser() is not None
    except Exception:
        opened = False
    if opened:
        status(Text(f"opened in browser: {path}", style="dim"))
    else:
        status(Text(f"no browser, saved to {path}", style="dim"))
    return opened


def open_cell_in_browser(value: object, app: object, *, status: "Callable[[Text], None]") -> "Path | None":
    """Serialize ``value`` to the dumps dir and open it in the browser.

    Returns the written path on success, or ``None`` if no dumps dir is
    configured or the write failed.
    """
    from tabulaflow.app.dump import write_cell_dump

    try:
        dumps_dir: Path = app._runtime_paths.dumps_dir  # type: ignore[attr-defined]
    except AttributeError:
        status(Text("save failed: no cell dumps dir", style=ERROR))
        return None
    try:
        path = write_cell_dump(value, dumps_dir)
    except OSError as exc:
        status(Text(f"write failed: {exc}", style=ERROR))
        return None
    except Exception as exc:
        status(Text(f"serialize failed: {exc}", style=ERROR))
        return None
    _open_path_in_browser(path, status=status)
    return path


def open_table_in_browser(
    df: "pd.DataFrame",
    title: str,
    app: object,
    *,
    status: "Callable[[Text], None]",
) -> "Path | None":
    """Render ``df`` as inline-media HTML in the dumps dir and open it.

    Returns the written HTML path on success, or ``None`` on failure.
    """
    import secrets

    from tabulaflow.app.dump import render_table_html

    try:
        dumps_dir: Path = app._runtime_paths.dumps_dir  # type: ignore[attr-defined]
    except AttributeError:
        status(Text("save failed: no cell dumps dir", style=ERROR))
        return None
    html_path = dumps_dir / f"T_{secrets.token_hex(3)}.html"
    try:
        render_table_html(df, html_path, title=title)
    except OSError as exc:
        status(Text(f"write failed: {exc}", style=ERROR))
        return None
    except Exception as exc:
        status(Text(f"render failed: {exc}", style=ERROR))
        return None
    _open_path_in_browser(html_path, status=status)
    return html_path


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
        Binding("b", "open_table_in_browser", "Open table in browser", show=True, priority=True),
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
        self.call_after_refresh(lambda: painted.done() or painted.set_result(None))
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

    async def action_open_table_in_browser(self) -> None:
        """Open the current DataFrame as HTML in the system browser.

        Shows ``Opening...`` while the (blocking) render runs, paints
        before the block, then the helper overwrites the status with the
        final result (``opened in browser: <path>`` or ``no browser, saved
        to: <path>``).
        """
        import asyncio

        self._set_status_message(Text("Opening...", style="dim"))
        painted: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self.call_after_refresh(lambda: painted.done() or painted.set_result(None))
        await painted
        open_table_in_browser(self._df, self._title, self.app, status=self._set_status_message)

    def _set_status_message(self, message: "Text") -> None:
        """Display a transient status message from a browser-open helper."""
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
            (" Open table in browser", hint_fg),
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
        Binding("b", "open_in_browser", "Open cell in browser", show=True, priority=True),
    ]

    # Skip syntax highlighting above this many rendered chars — Pygments'
    # upfront pass blocks the UI for several seconds on multi-MB JSON.
    _MAX_HIGHLIGHT_CHARS = 200_000
    # Disable soft_wrap when any line exceeds this length — wrap recompute
    # on a single very long line dominates scroll/cursor cost in TextArea.
    _MAX_SOFT_WRAP_LINE = 500
    # Soft cap on the rendered display text. Beyond this, append a footer
    # pointing the user at `b` for full-fidelity content via the browser
    # (which goes through ``dump.serialize_cell``, bypassing this cap).
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
        self._raw_value = value
        self._dtype_str = dtype_str
        # Cache the path written by ``action_open_in_browser`` so repeated
        # presses of `b` reuse the same file (and may reuse the same
        # browser tab) instead of writing a new dump every time.
        self._dumped_path: Path | None = None
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

        Output is soft-capped at ``_MAX_DISPLAY_CHARS``; truncated text gets
        a footer pointing the user at `b` for full content (which goes
        through ``dump.serialize_cell``, bypassing this cap). Per-leaf
        truncation (``_MAX_JSON_LEAF``) keeps individual JSON strings
        bounded so pretty-printed JSON has short lines.
        """
        import pandas as pd_

        try:
            if value is None or pd_.isna(value):
                return "NULL", None
        except (TypeError, ValueError):
            pass

        if isinstance(value, (bytes, bytearray, memoryview)):
            from tabulaflow.app.dump import sniff_binary

            raw = bytes(value)
            sniffed = sniff_binary(raw)
            label = sniffed[1] if sniffed else "binary"
            preview = raw[:32].hex(" ")
            return f"<{label}: {len(raw):,} bytes>\n{preview} ...", None

        # HuggingFace Image/Audio struct: surface the blob preview rather
        # than the JSON tree of ``{"bytes": ..., "path": ...}``. Matches the
        # serialize_cell path so the in-TUI cell view and the file written
        # by ``b`` are consistent (both treat the cell as media, not JSON).
        if isinstance(value, dict):
            inner = value.get("bytes")
            if isinstance(inner, (bytes, bytearray, memoryview)):
                from tabulaflow.app.dump import sniff_binary

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
            text[: cls._MAX_DISPLAY_CHARS]
            + f"\n\n... (truncated to {cls._MAX_DISPLAY_CHARS:,} of {len(text):,} chars; "
            "press `b` for full content in browser)"
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
        hint.append("B", style=KEY_HINT)
        hint.append(" Open cell in browser    ", style="dim")
        self.query_one(".cell-browser-hint", Static).update(hint)

    def _refresh_status(self, extra: Text | None = None) -> None:
        status = Text()
        status.append(
            f"{self._column_name} ({self._dtype_str})  |  Row {self._row_number:,}",
            style="dim",
        )
        if extra is not None:
            status.append("  |  ", style="dim")
            status.append_text(extra)
        self.query_one(".cell-browser-status", Static).update(status)

    def action_close_browser(self) -> None:
        self.dismiss()

    async def action_open_in_browser(self) -> None:
        """Save the raw value with its native extension and open it in a browser.

        Uses ``webbrowser_open`` (which queries the system's default browser
        directly rather than going through file-extension associations) so
        ``.json`` reaches Chrome's native tree viewer regardless of how
        ``.json`` is otherwise associated. Falls back to reporting the
        saved path if no browser is available (headless / SSH).

        Shows ``Opening...`` while the serialize/write runs so the user
        sees an immediate response on click. Only paints the wait status
        when a dump is actually being produced — if the cached path
        already exists, the reuse-path is fast and skips the flicker.
        """
        if self._dumped_path is None or not self._dumped_path.exists():
            import asyncio

            self._refresh_status(Text("Opening...", style="dim"))
            painted: asyncio.Future[None] = asyncio.get_running_loop().create_future()
            self.call_after_refresh(lambda: painted.done() or painted.set_result(None))
            await painted
            path = open_cell_in_browser(self._raw_value, self.app, status=self._refresh_status)
            if path is None:
                return
            self._dumped_path = path
        else:
            _open_path_in_browser(self._dumped_path, status=self._refresh_status)


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


class _NodeData:
    """Metadata attached to each Tree node."""

    __slots__ = ("kind", "alias", "schema_name", "table_name", "column_name")

    def __init__(
        self,
        kind: str,
        alias: str,
        schema_name: str | None = None,
        table_name: str | None = None,
        column_name: str | None = None,
    ) -> None:
        self.kind = kind
        self.alias = alias
        self.schema_name = schema_name
        self.table_name = table_name
        self.column_name = column_name


# 4-tuple identifier for any tree node: (alias, schema, table, column).
# DB → (a, None, None, None); schema → (a, s, None, None); table → (a, s, t,
# None); column → (a, s, t, c). All four levels are unique by tuple identity.
_NodePath = tuple[str, str | None, str | None, str | None]


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

    def _build_tree(self) -> None:
        from textual.widgets import Tree

        from tabulaflow.core.types import SQLSchema, SQLTableSchema

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
                expand=self._expand_for((alias, None, None, None), auto_expand),
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
                    schema_node = db_node.add(
                        sn_label,
                        data=_NodeData(kind=_NODE_KIND_SCHEMA, alias=alias, schema_name=sn),
                        expand=self._expand_for((alias, sn, None, None), auto_expand),
                    )
                    for t in sorted(groups[sn], key=lambda t: t.name):
                        self._add_table_node(schema_node, alias, t)
            else:
                for t in sorted(tables, key=lambda t: t.name):
                    self._add_table_node(db_node, alias, t)

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

        for col in table.columns:
            c_label = Text()
            c_label.append(col.name)
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

        parts: list[str] = []
        connector = self._registry.get(node_data.alias)
        schema = connector.schema
        if not isinstance(schema, SQLSchema):
            self._status.update(Text(""))
            return

        if node_data.kind == _NODE_KIND_DB:
            tables = list(schema.tables)
            parts.append(node_data.alias)
            parts.append(f"{len(tables):,} tables")

        elif node_data.kind == _NODE_KIND_SCHEMA:
            tables = [t for t in schema.tables if t.schema_name == node_data.schema_name]
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
        self._hint.update(hint)
