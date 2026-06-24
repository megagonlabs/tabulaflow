"""Compose a cited result record into a tabbed card for the browser pane.

Renders a record's available views (chart / data / query) to self-contained files
in the dumps dir and returns a small descriptor the pane uses to build a
``Chart | Data | Query`` tab strip. The table/chart renderers are reused unchanged;
the tab UI itself lives in the pane (one iframe whose ``src`` swaps between views).
"""

from __future__ import annotations

import html
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from tabulaflow.app.page import CARD_BG, TEXT, render_page
from tabulaflow.app.render.charts import render_chart_html
from tabulaflow.app.render.tables import render_table_html

if TYPE_CHECKING:
    from tabulaflow.chat.result import ChatResultRecord

_QUERY_CSS = (
    "body { background: %(bg)s; color: %(fg)s; margin: 0; }"
    "pre.sql { margin: 0; padding: 16px; white-space: pre-wrap; word-break: break-word;"
    " font: 13px ui-monospace, SFMono-Regular, Menlo, monospace; }"
) % {"bg": CARD_BG, "fg": TEXT}


def render_query_html(sql: str, html_path: Path) -> None:
    """Render a SQL string as a simple self-contained HTML page."""
    body = f'<pre class="sql">{html.escape(sql)}</pre>'
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
        render_table_html(df, path, title=record.label)
        views.append({"kind": "data", "file": path.name})
    if record.query:
        path = dumps_dir / f"Q_{secrets.token_hex(3)}.html"
        render_query_html(record.query, path)
        views.append({"kind": "query", "file": path.name})
    if not views:
        return None
    return {"label": record.label, "views": views}
