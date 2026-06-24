"""Render a Vega-Lite spec over a DataFrame to a self-contained interactive HTML chart."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING

from tabulaflow.app.page import CARD_BG, TEXT, TEXT_MUTED, render_page
from tabulaflow.app.theme import ACCENT

if TYPE_CHECKING:
    import pandas as pd

# ---------------------------------------------------------------------------
# Chart HTML rendering (Vega-Lite)
# ---------------------------------------------------------------------------

# Above this row count, render with canvas instead of SVG: thousands of SVG
# mark nodes bog the browser down, while canvas stays smooth. The render_chart
# tool caps attachable results well below pathological sizes; this is just the
# crisp-vs-fast tradeoff within that range.
_SVG_ROW_LIMIT = 5_000
_CHART_GRID = "#3a4352"

# Dark/mint Vega config applied as *defaults* (lowest precedence). Anything the
# spec sets explicitly — including agent-requested colors — overrides it, since
# Vega layers config underneath the spec's own mark/encoding properties.
_VEGA_DARK_CONFIG: dict[str, object] = {
    "background": CARD_BG,
    "view": {"stroke": "transparent"},
    "font": "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    "title": {"color": TEXT, "subtitleColor": TEXT_MUTED, "fontSize": 17, "fontWeight": 600},
    "axis": {
        "labelColor": TEXT_MUTED,
        "titleColor": TEXT,
        "gridColor": _CHART_GRID,
        "gridOpacity": 0.9,
        "domainColor": _CHART_GRID,
        "tickColor": _CHART_GRID,
        "labelFontSize": 12,
        "titleFontSize": 14,
        "labelLimit": 160,
    },
    "legend": {"labelColor": TEXT_MUTED, "titleColor": TEXT, "labelFontSize": 12, "titleFontSize": 13},
    # Categorical palette: the mint accent first, then off-palette hues used
    # only for chart series (not part of the page design tokens).
    "range": {
        "category": [
            ACCENT,  # mint
            "#5ac8fa",  # sky blue
            "#f5a623",  # amber
            "#bd6cf0",  # violet
            "#f06292",  # pink
            "#4dd0e1",  # cyan
            "#aed581",  # lime
            "#ff8a65",  # coral
        ],
        "ramp": {"scheme": "greens"},
        "heatmap": {"scheme": "greens"},
    },
    "mark": {"color": ACCENT, "tooltip": True},
    "bar": {"fill": ACCENT},
    "line": {"stroke": ACCENT},
    "point": {"fill": ACCENT},
    "area": {"fill": ACCENT},
    "arc": {"stroke": CARD_BG},
}

_CHART_CSS = """
/* Top-anchored, horizontally-centered column (Notion-style document flow):
   the card sits just under the banner and is centered left-to-right, capped so
   it isn't full-bleed on wide monitors. */
#vis-stage {
    display: flex;
    align-items: flex-start;
    justify-content: center;
}
/* Bounded, centered card — capped so the chart isn't full-bleed on wide
   monitors. */
#vis-wrap {
    width: 100%;
    max-width: 720px;
    box-sizing: border-box;
}
/* Single-view charts fill a fixed-height card in both dimensions
   (spec width/height = "container"). */
#vis-wrap.fill { height: 480px; }
#vis-wrap.fill #vis,
#vis-wrap.fill #vis > .vega-embed { width: 100%; height: 100%; }
/* Multi-view / faceted charts keep their intrinsic size (Vega-Lite can't size
   those to a container). The parent pane/browser owns vertical scrolling. */
#vis-wrap.content { overflow: visible; }
#vis-wrap.content #vis { width: 100%; }
.vis-error { color: var(--error); white-space: pre-wrap;
    font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 13px; }
.vega-embed { width: 100%; }
/* vega-embed action ("...") menu — dark to match the page. vega-embed injects
   its own light stylesheet at runtime with equal specificity, so we override on
   its own selectors with !important (it only uses !important on `display`, so
   this is safe). Covers the button, popup, links, and caret. */
.vega-embed summary {
    background: var(--popover-bg) !important; color: var(--text-muted) !important;
    border-color: var(--popover-border) !important; opacity: 0.55 !important;
}
.vega-embed summary svg { fill: currentColor !important; }
.vega-embed details[open] summary,
.vega-embed summary:hover { opacity: 1 !important; color: var(--accent) !important; }
.vega-embed .vega-actions {
    background: var(--popover-bg) !important; border-color: var(--popover-border) !important;
}
.vega-embed .vega-actions a { color: var(--text) !important; }
.vega-embed .vega-actions a:hover,
.vega-embed .vega-actions a:focus { background: var(--hover) !important; color: var(--accent) !important; }
/* The caret pointing from the menu up to the button (border + fill triangles). */
.vega-embed .vega-actions::before { border-bottom-color: var(--popover-border) !important; }
.vega-embed .vega-actions::after { border-bottom-color: var(--popover-bg) !important; }
/* Bound-input widgets (slider/checkbox/radio/dropdown/text). ``accent-color``
   is inherited, so one declaration recolors the range track+thumb, checkboxes,
   and radios from the browser's default blue to mint; selects/text inputs have
   no accent fill, so they're dark-themed explicitly. */
.vega-bindings { accent-color: var(--accent); color: var(--text); font-size: 13px; margin-top: 14px; }
.vega-bindings .vega-bind { margin: 4px 0; }
.vega-bindings .vega-bind-name { color: var(--text-muted); margin-right: 8px; }
.vega-bindings select,
.vega-bindings input[type="text"],
.vega-bindings input[type="number"] {
    background: var(--bg); color: var(--text); border: 1px solid var(--border);
    border-radius: 4px; padding: 2px 6px;
}
.vega-bindings select:focus,
.vega-bindings input:focus { outline: none; border-color: var(--accent); }
"""


def _load_vega_assets() -> tuple[str, str, str]:
    """Load vendored Vega, Vega-Lite, and vega-embed JS from package resources.

    Returns ``(vega_js, vega_lite_js, vega_embed_js)``. Files are vendored under
    ``tabulaflow/app/assets/vega/`` (vega@5, vega-lite@5, vega-embed@6 — the
    canonical compatible trio).
    """
    from importlib.resources import files

    base = files("tabulaflow.app.assets.vega")
    return (
        base.joinpath("vega.min.js").read_text(encoding="utf-8"),
        base.joinpath("vega-lite.min.js").read_text(encoding="utf-8"),
        base.joinpath("vega-embed.min.js").read_text(encoding="utf-8"),
    )


def _deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    """Recursively merge ``override`` onto ``base``; ``override`` wins on conflict."""
    out = dict(base)
    for key, val in override.items():
        existing = out.get(key)
        if isinstance(val, dict) and isinstance(existing, dict):
            out[key] = _deep_merge(existing, val)
        else:
            out[key] = val
    return out


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
    richer is returned unchanged (the agent can author hover itself). Applied at
    browser-render time only, so the stored spec and terminal preview stay the
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


def render_chart_html(
    df: "pd.DataFrame",
    vegalite_spec: dict[str, object],
    html_path: Path,
    *,
    title: str | None = None,
) -> None:
    """Render a Vega-Lite spec as a self-contained interactive HTML chart.

    The DataFrame is embedded inline (offline ``file://`` blocks ``fetch``, so
    external data URLs won't load) and rendered at full fidelity by the vendored
    Vega runtime — unlike the plotext terminal preview, this honors color/facet/
    transform encodings and any mark type. A dark/mint Vega ``config`` is merged
    in as defaults; anything the spec sets explicitly (e.g. user-requested
    colors) overrides it.

    Args:
        df: Source data (already row-bounded by the render_chart tool).
        vegalite_spec: The Vega-Lite specification (semantic; unthemed).
        html_path: Output HTML path.
        title: Document title (browser tab); defaults to the file stem.
    """
    spec = copy.deepcopy(vegalite_spec)
    colmap = {str(c).lower(): str(c) for c in df.columns}
    _normalize_field_refs(spec, colmap)
    spec = _add_line_hover(spec)

    existing_config = spec.get("config")
    spec["config"] = _deep_merge(_VEGA_DARK_CONFIG, existing_config if isinstance(existing_config, dict) else {})
    spec.setdefault("$schema", "https://vega.github.io/schema/vega-lite/v5.json")
    # Sizing modes (the spec's own width/height always wins via setdefault):
    #  - single-cell spec (a unit ``mark`` or a ``layer`` of marks) -> fill a
    #    fixed-height card both ways (responsive width/height = "container").
    #  - single-cell spec with bound inputs (sliders/dropdowns) -> size the chart
    #    explicitly so the controls have room below it; the card grows/scrolls.
    #  - genuinely multi-cell: faceted (top-level facet/repeat or a
    #    facet/row/column channel) or concat -> can't size to a container, so
    #    keep the intrinsic size and scroll inside the card.
    encoding = spec.get("encoding")
    has_facet_channel = isinstance(encoding, dict) and any(ch in encoding for ch in ("facet", "row", "column"))
    # ``layer`` shares one plotting area, so it supports container sizing;
    # facet/concat/repeat have sub-views and don't.
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

    vega_js, vega_lite_js, vega_embed_js = _load_vega_assets()

    # ``</`` inside an inline <script> string can prematurely close the tag.
    data_json = (df.to_json(orient="records", date_format="iso", default_handler=str) or "[]").replace("</", "<\\/")
    spec_json = json.dumps(spec, ensure_ascii=False, default=str).replace("</", "<\\/")
    renderer = "canvas" if len(df) > _SVG_ROW_LIMIT else "svg"

    init_js = (
        "(function(){"
        f"var spec={spec_json};"
        f"spec.data={{values:{data_json}}};"
        f"var opt={{renderer:{json.dumps(renderer)},"
        'tooltip:{theme:"dark"},'
        "actions:{export:true,source:false,compiled:false,editor:false}};"
        'vegaEmbed("#vis",spec,opt).catch(function(err){'
        'var el=document.getElementById("vis");var pre=document.createElement("pre");'
        'pre.className="vis-error";pre.textContent="Chart error: "+String(err);'
        'el.innerHTML="";el.appendChild(pre);});})();'
    )

    head = (
        f"<script>{vega_js}</script>"
        f"<script>{vega_lite_js}</script>"
        f"<script>{vega_embed_js}</script>"
        f"<style>{_CHART_CSS}</style>"
    )
    doc = render_page(
        title=title or html_path.stem,
        body=f'<div id="vis-stage"><div id="vis-wrap" class="{wrap_class}"><div id="vis"></div></div></div>',
        head=head,
        scripts=f"<script>{init_js}</script>",
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(doc, encoding="utf-8")
