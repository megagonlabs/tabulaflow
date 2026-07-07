"""Browser-pane rendering payloads and media helpers.

Public API re-exported here so callers keep ``from tabulaflow.app.render import ...``.
"""

from tabulaflow.app.render.cards import build_query_data, render_map_data, render_record_data
from tabulaflow.app.render.charts import _add_line_hover, build_chart_data
from tabulaflow.app.render.media import (
    sniff_binary,
    try_decode_base64,
)
from tabulaflow.app.render.tables import build_table_data

__all__ = [
    "_add_line_hover",
    "build_chart_data",
    "build_query_data",
    "build_table_data",
    "render_map_data",
    "render_record_data",
    "sniff_binary",
    "try_decode_base64",
]
