"""Compose a cited result record into structured browser-pane data."""

from __future__ import annotations

import html
import json
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from tabulaflow.app.page import TEXT, render_page
from tabulaflow.app.pane_types import PaneRecord, ViewKind, record_payload
from tabulaflow.app.render.charts import build_chart_data
from tabulaflow.app.render.maps import build_map_data
from tabulaflow.app.render.tables import PANE_TABLE_MAX_HEIGHT, _build_table_data

if TYPE_CHECKING:
    import pandas as pd


class ResultRecordLike(Protocol):
    df: "pd.DataFrame | None"
    chart_spec: dict[str, object] | None
    query: str | None
    label: str | None
    query_lexer: str


class MapRecordLike(Protocol):
    map_id: str
    label: str | None
    map_spec: dict[str, object]
    sources: "dict[str, pd.DataFrame]"


_QUERY_BG = "#1e1e1e"


_QUERY_CSS = (
    "#content { padding: 0; }"
    "body { margin: 0; background: %(bg)s; }"
    ".query-card { background: %(bg)s; color: %(text)s; }"
    ".query-bar { height: 42px; display: flex; align-items: center; justify-content: space-between;"
    " padding: 0 14px 0 18px; box-sizing: border-box; border-bottom: 1px solid #303030;"
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
    query_data = build_query_data(sql, lexer=lexer)["query"]
    assert isinstance(query_data, dict)
    body = (
        '<section class="query-card">'
        '<div class="query-bar">'
        f'<span class="query-lang">{html.escape(str(query_data["language"]))}</span>'
        '<button class="query-copy" type="button" data-copy-query aria-label="Copy query" title="Copy query">'
        '<span class="copy-icon" aria-hidden="true"></span>'
        "</button>"
        "</div>"
        f"{query_data['html']}"
        "</section>"
    )
    script = _QUERY_SCRIPT.replace("__QUERY_JSON__", json.dumps(sql))
    page = render_page(title="Query", body=body, head=f"<style>{_QUERY_CSS}</style>", scripts=script)
    html_path.write_text(page, encoding="utf-8")


def build_query_data(sql: str, *, lexer: str = "sql") -> dict[str, object]:
    """Build a structured query payload for the browser pane."""
    try:
        lex = get_lexer_by_name(lexer or "sql")
    except ClassNotFound:
        lex = get_lexer_by_name("sql")
    highlighted = highlight(sql, lex, HtmlFormatter(style="dracula", noclasses=True))
    language = lex.name or (lexer or "sql").upper()
    return {"query": {"sql": sql, "lexer": lexer or "sql", "language": language, "html": highlighted}}


def render_record_data(record: ResultRecordLike, pane_dir: Path) -> PaneRecord | None:
    """Render a record's chart/data/query payload to JSON; return a pane manifest.

    The descriptor is ordered chart -> data -> query, including only the views
    the record has, or ``None`` when the record has nothing displayable.
    """
    views: list[ViewKind] = []
    record_id = f"rec_{secrets.token_hex(6)}"
    record_data: dict[str, object] = {}
    df = record.df
    if df is not None and not df.empty:
        table_build = _build_table_data(
            df,
            asset_stem=record_id,
            output_dir=pane_dir,
            max_height=PANE_TABLE_MAX_HEIGHT,
        )
        record_data.update(table_build.data)
        if record.chart_spec is not None:
            record_data.update(build_chart_data(df, record.chart_spec, field_by_column=table_build.field_by_column))
            views.append("chart")
        views.append("data")
    if record.query:
        record_data.update(build_query_data(record.query, lexer=record.query_lexer or "sql"))
        views.append("query")
    if not views:
        return None
    pane_dir.mkdir(parents=True, exist_ok=True)
    (pane_dir / f"{record_id}.data.json").write_text(
        json.dumps(record_data, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return record_payload(record_id=record_id, label=record.label, views=views)


def render_map_card_data(map_record: MapRecordLike, pane_dir: Path) -> PaneRecord | None:
    """Render a standalone map card's payload to JSON; return a pane manifest.

    A map-only card (no chart/data/query views) assembled from one or more query
    results: each source DataFrame becomes a bundled dataset, and each layer reads
    from its ``source`` dataset. Returns ``None`` when no valid layer resolves.
    """
    # ``rec_`` prefix: the pane server only serves session files under this
    # convention (see ``app/pane.py``); the map's ``MAP*`` id lives in its label.
    card_id = f"rec_{secrets.token_hex(6)}"
    sources_payload: dict[str, dict[str, object]] = {}
    for source_id, df in map_record.sources.items():
        if df is None or df.empty:
            continue
        table_build = _build_table_data(
            df,
            asset_stem=f"{card_id}_{source_id}",
            output_dir=pane_dir,
            max_height=None,
        )
        dataset = table_build.data.get("dataset")
        table_payload = table_build.data.get("table")
        sources_payload[source_id] = {
            "rows": dataset.get("rows", []) if isinstance(dataset, dict) else [],
            "columns": table_payload.get("columns", []) if isinstance(table_payload, dict) else [],
            "field_by_column": table_build.field_by_column,
        }
    map_data = build_map_data(map_record.map_spec, sources_payload)
    if map_data is None:
        return None
    pane_dir.mkdir(parents=True, exist_ok=True)
    (pane_dir / f"{card_id}.data.json").write_text(
        json.dumps(map_data, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return record_payload(record_id=card_id, label=map_record.label, views=["map"])
