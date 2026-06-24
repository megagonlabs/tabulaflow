"""Compose a cited result record into a tabbed card for the browser pane.

Renders a record's available views (chart / data / query) to self-contained files
in the dumps dir and returns a small descriptor the pane uses to build a
``Chart | Data | Query`` tab strip. The table/chart renderers are reused unchanged;
the tab UI itself lives in the pane (one iframe whose ``src`` swaps between views).
"""

from __future__ import annotations

import html
import json
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from tabulaflow.app.page import TEXT, render_page
from tabulaflow.app.render.charts import render_chart_html
from tabulaflow.app.render.tables import TABLE_RENDER_MAX_ROWS, render_table_html

if TYPE_CHECKING:
    from tabulaflow.chat.result import ChatResultRecord

# Fixed pixel cap for the data-table panel: short tables hug, long ones cap +
# scroll internally (≈ the chart panel height), rather than tracking the viewport.
_PANE_TABLE_MAX_H = 520

# URL base the pane serves the bundled Vega/Tabulator libs under (see pane.py);
# linking beats re-inlining ~0.8 MB of Vega into every chart dump.
_ASSET_BASE = "/assets"

_QUERY_BG = "#202020"


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}" if n == 1 else f"{n:,} {word}s"


def _data_view_meta(num_rows: int, num_cols: int, *, max_rows: int = TABLE_RENDER_MAX_ROWS) -> str:
    row_text = (
        f"showing {max_rows:,} of {_plural(num_rows, 'row')}" if num_rows > max_rows else _plural(num_rows, "row")
    )
    return f"{row_text} · {_plural(num_cols, 'column')}"


_QUERY_CSS = (
    "#content { padding: 0; }"
    "body { margin: 0; background: %(bg)s; }"
    ".query-card { background: %(bg)s; color: %(text)s; }"
    ".query-bar { height: 42px; display: flex; align-items: center; justify-content: space-between;"
    " padding: 0 14px 0 18px; box-sizing: border-box; border-bottom: 1px solid #242424;"
    " color: #f5f5f5; font: 600 13px/1.2 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }"
    ".query-lang { letter-spacing: 0; }"
    ".query-copy { display: inline-flex; align-items: center; justify-content: center; height: 30px; width: 30px;"
    " border: 0; border-radius: 6px; background: transparent; color: #f5f5f5;"
    " font: 500 12px/1 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; cursor: pointer; }"
    ".query-copy:hover { background: #242424; }"
    ".query-copy:focus-visible { outline: 2px solid #3eb489; outline-offset: 2px; }"
    ".copy-icon { position: relative; width: 16px; height: 16px; flex: 0 0 auto; }"
    ".copy-icon::before, .copy-icon::after { content: ''; position: absolute; width: 10px; height: 12px;"
    " border: 2px solid currentColor; border-radius: 4px; box-sizing: border-box; }"
    ".copy-icon::before { left: 1px; top: 4px; opacity: 0.72; }"
    ".copy-icon::after { left: 5px; top: 0; background: %(bg)s; }"
    ".highlight { margin: 0; background: %(bg)s !important; }"
    ".highlight pre { margin: 0; padding: 18px 20px 20px; white-space: pre-wrap; word-break: break-word;"
    " background: %(bg)s !important; font: 13px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace; }"
) % {"bg": _QUERY_BG, "text": TEXT}

_QUERY_SCRIPT = """
<script>
(function () {
  var code = __QUERY_JSON__;
  var button = document.querySelector('[data-copy-query]');
  if (!button) return;
  button.addEventListener('click', function () {
    function done(ok) {
      button.setAttribute('aria-label', ok ? 'Copied query' : 'Copy failed');
      button.title = ok ? 'Copied' : 'Copy failed';
      window.setTimeout(function () {
        button.setAttribute('aria-label', 'Copy query');
        button.title = 'Copy query';
      }, 1200);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(code).then(function () { done(true); }, function () { done(false); });
      return;
    }
    var textarea = document.createElement('textarea');
    textarea.value = code;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      done(document.execCommand('copy'));
    } catch (_err) {
      done(false);
    }
    textarea.remove();
  });
})();
</script>
"""


def render_query_html(sql: str, html_path: Path, *, lexer: str = "sql") -> None:
    """Render SQL as a self-contained, syntax-highlighted HTML page."""
    try:
        lex = get_lexer_by_name(lexer or "sql")
    except ClassNotFound:
        lex = get_lexer_by_name("sql")
    highlighted = highlight(sql, lex, HtmlFormatter(style="dracula", noclasses=True))
    language = lex.name or (lexer or "sql").upper()
    body = (
        '<section class="query-card">'
        '<div class="query-bar">'
        f'<span class="query-lang">{html.escape(language)}</span>'
        '<button class="query-copy" type="button" data-copy-query aria-label="Copy query" title="Copy query">'
        '<span class="copy-icon" aria-hidden="true"></span>'
        "</button>"
        "</div>"
        f"{highlighted}"
        "</section>"
    )
    script = _QUERY_SCRIPT.replace("__QUERY_JSON__", json.dumps(sql))
    page = render_page(title="Query", body=body, head=f"<style>{_QUERY_CSS}</style>", scripts=script)
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
            render_chart_html(df, record.chart_spec, path, title=record.label, asset_base=_ASSET_BASE)
            views.append({"kind": "chart", "file": path.name})
        path = dumps_dir / f"T_{secrets.token_hex(3)}.html"
        render_table_html(df, path, title=record.label, max_height=_PANE_TABLE_MAX_H, asset_base=_ASSET_BASE)
        views.append({"kind": "data", "file": path.name, "meta": _data_view_meta(len(df), len(df.columns))})
    if record.query:
        path = dumps_dir / f"Q_{secrets.token_hex(3)}.html"
        render_query_html(record.query, path, lexer=record.query_lexer or "sql")
        views.append({"kind": "query", "file": path.name})
    if not views:
        return None
    return {"label": record.label, "views": views}
