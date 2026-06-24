"""HTML rendering for the app: tables, charts, and cell/media serialization.

Public API re-exported here so callers keep ``from tabulaflow.app.render import ...``.
"""

from tabulaflow.app.render.cards import render_record_card
from tabulaflow.app.render.charts import _add_line_hover, render_chart_html
from tabulaflow.app.render.media import (
    serialize_cell,
    sniff_binary,
    try_decode_base64,
    write_cell_dump,
)
from tabulaflow.app.render.tables import render_table_html

__all__ = [
    "_add_line_hover",
    "render_chart_html",
    "render_record_card",
    "render_table_html",
    "serialize_cell",
    "sniff_binary",
    "try_decode_base64",
    "write_cell_dump",
]
