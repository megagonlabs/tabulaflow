"""Build structured Vega-Lite chart payloads for the browser output pane."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from tabulaflow.app.pane.types import ChartCardData

if TYPE_CHECKING:
    import pandas as pd

# Above this row count, render with canvas instead of SVG: thousands of SVG
# mark nodes bog the browser down, while canvas stays smooth. The render_chart
# tool caps attachable results well below pathological sizes; this is just the
# crisp-vs-fast tradeoff within that range.
_SVG_ROW_LIMIT = 5_000


def _normalize_field_refs(node: object, colmap: dict[str, str]) -> None:
    """Rewrite ``field`` references to the DataFrame's column-name casing, in place.

    Vega is case-sensitive on field names; an agent may emit a different case
    than the actual columns. Walks the spec and, for any ``{"field": "x"}`` whose
    value case-insensitively matches a column, replaces it with the real column
    name. Transform-derived fields (no matching column) are left untouched.
    """
    if isinstance(node, dict):
        for key, val in node.items():
            if key == "field" and isinstance(val, str):
                actual = colmap.get(val.lower())
                if actual is not None:
                    node[key] = actual
            else:
                _normalize_field_refs(val, colmap)
    elif isinstance(node, list):
        for item in node:
            _normalize_field_refs(item, colmap)


def _alias_field_refs(node: object, alias: dict[str, str], *, in_encoding: bool = False) -> None:
    """Rewrite normalized field references to shared dataset field names."""
    if isinstance(node, dict):
        field = node.get("field")
        if isinstance(field, str):
            target = alias.get(field)
            if target is not None:
                node["field"] = target
                if in_encoding and "title" not in node:
                    node["title"] = field
        for key, val in node.items():
            _alias_field_refs(val, alias, in_encoding=key == "encoding" or in_encoding)
    elif isinstance(node, list):
        for item in node:
            _alias_field_refs(item, alias, in_encoding=in_encoding)


def _has_input_binding(spec: dict[str, object]) -> bool:
    """Whether the spec binds a param to an HTML input widget (slider/dropdown/…).

    Such charts render interactive controls that need vertical room below the
    plot, so they're sized differently from a plain fill-the-card chart.
    """
    params = spec.get("params")
    if not isinstance(params, list):
        return False
    for param in params:
        bind = param.get("bind") if isinstance(param, dict) else None
        if isinstance(bind, dict) and "input" in bind:
            return True
    return False


def _add_line_hover(spec: dict[str, object]) -> dict[str, object]:
    """Layer a nearest-point hover dot onto a plain single-series line chart.

    Only the narrow, safe shape is transformed — a unit ``line`` mark with x and
    y fields and no layering, params, transforms, or grouping channel. Anything
    richer is returned unchanged (the agent can author hover itself). Applied in
    the pane payload only, so the stored spec and terminal preview stay the
    plain line.
    """
    mark = spec.get("mark")
    mark_type = mark.get("type") if isinstance(mark, dict) else mark
    if mark_type != "line":
        return spec
    if any(key in spec for key in ("layer", "params", "transform", "facet", "repeat", "concat", "hconcat", "vconcat")):
        return spec
    encoding = spec.get("encoding")
    if not isinstance(encoding, dict):
        return spec
    x_enc, y_enc = encoding.get("x"), encoding.get("y")
    if not (isinstance(x_enc, dict) and x_enc.get("field") and isinstance(y_enc, dict) and y_enc.get("field")):
        return spec
    # Single series only — a grouping channel makes "nearest point by x" ambiguous.
    for channel in ("color", "detail", "shape", "size", "opacity"):
        ch_enc = encoding.get(channel)
        if isinstance(ch_enc, dict) and ch_enc.get("field"):
            return spec

    hover_layer = {
        "params": [
            {
                "name": "tf_hover",
                "select": {
                    "type": "point",
                    "on": "pointerover",
                    "nearest": True,
                    "clear": "pointerout",
                    "fields": [x_enc["field"]],
                },
            }
        ],
        "mark": {"type": "point", "size": 70, "filled": True},
        "encoding": {
            "y": copy.deepcopy(y_enc),
            "opacity": {"condition": {"param": "tf_hover", "empty": False, "value": 1}, "value": 0},
        },
    }
    # Shared x moves to the wrapper; the line keeps its mark + remaining
    # encoding (y, tooltip, …). Other top-level keys (title, agent-set width/
    # height) ride along on the wrapper.
    wrapper = {key: val for key, val in spec.items() if key not in ("mark", "encoding")}
    wrapper["encoding"] = {"x": x_enc}
    wrapper["layer"] = [
        {"mark": spec["mark"], "encoding": {k: v for k, v in encoding.items() if k != "x"}},
        hover_layer,
    ]
    return wrapper


def build_chart_data(
    df: "pd.DataFrame",
    vegalite_spec: dict[str, object],
    *,
    field_by_column: dict[str, str] | None = None,
) -> ChartCardData:
    """Build a structured chart payload for the browser pane.

    Args:
        df: Source data.
        vegalite_spec: The Vega-Lite specification.
        field_by_column: Optional mapping from DataFrame column names to shared
            dataset field names.

    Returns:
        A record-data fragment containing a ``chart`` payload. Row values are
        not included; the live pane attaches the record-level dataset at mount.
    """
    spec = copy.deepcopy(vegalite_spec)
    colmap = {str(c).lower(): str(c) for c in df.columns}
    _normalize_field_refs(spec, colmap)
    spec = _add_line_hover(spec)
    if field_by_column:
        _alias_field_refs(spec, field_by_column)

    spec.setdefault("$schema", "https://vega.github.io/schema/vega-lite/v5.json")

    encoding = spec.get("encoding")
    has_facet_channel = isinstance(encoding, dict) and any(ch in encoding for ch in ("facet", "row", "column"))
    is_single_cell = ("mark" in spec or "layer" in spec) and not has_facet_channel
    if is_single_cell and not _has_input_binding(spec):
        spec.setdefault("width", "container")
        spec.setdefault("height", "container")
        wrap_class = "fill"
    elif is_single_cell:
        spec.setdefault("width", "container")
        spec.setdefault("height", 460)
        wrap_class = "content"
    else:
        wrap_class = "content"

    renderer = "canvas" if len(df) > _SVG_ROW_LIMIT else "svg"
    return {"chart": {"spec": spec, "renderer": renderer, "wrapClass": wrap_class}}
