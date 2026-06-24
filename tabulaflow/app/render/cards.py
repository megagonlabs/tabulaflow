"""Compose a cited result record into a tabbed card for the browser pane.

Renders a record's available views (chart / data / query) to self-contained files
in the dumps dir and returns a small descriptor the pane uses to build a
``Chart | Data | Query`` tab strip. The table/chart renderers are reused unchanged;
the tab UI itself lives in the pane (one iframe whose ``src`` swaps between views).
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.style import Style
from pygments.token import Comment, Keyword, Name, Number, Operator, Punctuation, String, Token
from pygments.util import ClassNotFound

from tabulaflow.app.page import CARD_BG, TEXT, render_page
from tabulaflow.app.render.charts import render_chart_html
from tabulaflow.app.render.tables import TABLE_RENDER_MAX_ROWS, render_table_html
from tabulaflow.app.theme import ACCENT

if TYPE_CHECKING:
    from tabulaflow.chat.result import ChatResultRecord

# Fixed pixel cap for the data-table panel: short tables hug, long ones cap +
# scroll internally (≈ the chart panel height), rather than tracking the viewport.
_PANE_TABLE_MAX_H = 520

_QUERY_BG = CARD_BG  # same panel surface as the chart/data views


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}" if n == 1 else f"{n:,} {word}s"


def _data_view_meta(num_rows: int, num_cols: int, *, max_rows: int = TABLE_RENDER_MAX_ROWS) -> str:
    row_text = (
        f"showing {max_rows:,} of {_plural(num_rows, 'row')}" if num_rows > max_rows else _plural(num_rows, "row")
    )
    return f"{row_text} · {_plural(num_cols, 'column')}"


class _SqlStyle(Style):  # type: ignore[misc]  # pygments ships no type stubs
    """Mint-accented dark SQL syntax theme, cohesive with the pane palette."""

    background_color = _QUERY_BG
    styles = {  # noqa: RUF012
        Token: TEXT,
        Comment: "italic #6a737d",
        Keyword: f"bold {ACCENT}",
        Operator: "#9aa4b2",
        Punctuation: "#9aa4b2",
        Name: TEXT,
        Name.Function: "#6cb6ff",
        Name.Builtin: ACCENT,
        String: "#98c379",
        Number: "#d19a66",
    }


_QUERY_CSS = (
    "#content { padding: 0; }"
    "body { margin: 0; background: %(bg)s; }"
    ".highlight { margin: 0; }"
    ".highlight pre { margin: 0; padding: 18px 20px; white-space: pre-wrap; word-break: break-word;"
    " font: 13px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace; }"
) % {"bg": _QUERY_BG}


def render_query_html(sql: str, html_path: Path, *, lexer: str = "sql") -> None:
    """Render SQL as a self-contained, syntax-highlighted HTML page."""
    try:
        lex = get_lexer_by_name(lexer or "sql")
    except ClassNotFound:
        lex = get_lexer_by_name("sql")
    body = highlight(sql, lex, HtmlFormatter(style=_SqlStyle, noclasses=True))
    page = render_page(title="Query", body=body, head=f"<style>{_QUERY_CSS}</style>")
    html_path.write_text(page, encoding="utf-8")


def render_record_card(record: "ChatResultRecord", dumps_dir: Path) -> dict[str, object] | None:
    """Render a record's chart/data/query views to files; return a card descriptor.

    The descriptor is ``{"label": str | None, "views": [{"kind", "file"}, ...]}``
    ordered chart -> data -> query, including only the views the record has, or
    ``None`` when the record has nothing displayable.
    """
    views: list[dict[str, str]] = []
    df = record.df
    if df is not None and not df.empty:
        if record.chart_spec is not None:
            path = dumps_dir / f"V_{secrets.token_hex(3)}.html"
            render_chart_html(df, record.chart_spec, path, title=record.label)
            views.append({"kind": "chart", "file": path.name})
        path = dumps_dir / f"T_{secrets.token_hex(3)}.html"
        render_table_html(df, path, title=record.label, max_height=_PANE_TABLE_MAX_H)
        views.append({"kind": "data", "file": path.name, "meta": _data_view_meta(len(df), len(df.columns))})
    if record.query:
        path = dumps_dir / f"Q_{secrets.token_hex(3)}.html"
        render_query_html(record.query, path, lexer=record.query_lexer or "sql")
        views.append({"kind": "query", "file": path.name})
    if not views:
        return None
    return {"label": record.label, "views": views}
