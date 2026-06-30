"""HTML rendering for the app: tables, charts, and cell/media serialization.

Public API re-exported here so callers keep ``from tabulaflow.app.render import ...``.
"""

from tabulaflow.app.render.cards import build_query_data, render_record_data
from tabulaflow.app.render.charts import _add_line_hover, build_chart_data, render_chart_html
from tabulaflow.app.render.media import (
    serialize_cell,
    sniff_binary,
    try_decode_base64,
    write_cell_dump,
)
from tabulaflow.app.render.tables import build_table_data, render_table_html

__all__ = [
    "_add_line_hover",
    "build_chart_data",
    "build_query_data",
    "build_table_data",
    "render_chart_html",
    "render_record_data",
    "render_table_html",
    "serialize_cell",
    "sniff_binary",
    "try_decode_base64",
    "write_cell_dump",
]
