"""Tool that renders a chart from a Vega-Lite spec using plotext."""

from __future__ import annotations

import json
from typing import Any, ClassVar

import pandas as pd
from pydantic_ai import Tool

from tabulaflow.toolhub.query_history import QueryHistory


_SUPPORTED_MARKS = {"bar", "line", "point", "rect"}

_MARK_TO_PLOTEXT = {
    "bar": "bar",
    "line": "line",
    "point": "scatter",
    "rect": "bar",
}

# Largest result that may be charted. The data is embedded inline in the
# browser HTML, so beyond this the file balloons and Vega janks; a chart over
# this many raw rows is also almost always un-aggregated. The tool refuses
# rather than truncating (a partial chart would silently misrepresent the data).
_MAX_CHART_ROWS = 20_000

# Marks plotext can draw faithfully as a single x/y series.
_PLOTEXT_MARKS = {"bar", "line", "point"}
# Top-level keys that make a spec multi-view (no single mark to preview).
_MULTIVIEW_KEYS = ("layer", "concat", "hconcat", "vconcat", "facet", "repeat", "spec")
# Encoding channels that, when bound to a field, reshape the chart beyond a
# single x/y series (grouping, faceting, second positions, polar, ...).
_GROUPING_CHANNELS = (
    "color",
    "size",
    "shape",
    "detail",
    "opacity",
    "theta",
    "theta2",
    "radius",
    "x2",
    "y2",
    "xOffset",
    "yOffset",
    "column",
    "row",
    "facet",
)
# Encoding-level transforms that change the data plotext would see (it plots
# raw columns, so these diverge from what Vega computes).
_RESHAPING_KEYS = ("aggregate", "bin", "timeUnit")

_MARK_LABELS = {
    "bar": "Bar chart",
    "line": "Line chart",
    "point": "Scatter plot",
    "circle": "Scatter plot",
    "square": "Scatter plot",
    "tick": "Strip plot",
    "area": "Area chart",
    "arc": "Pie chart",
    "rect": "Heatmap",
    "boxplot": "Box plot",
    "rule": "Rule chart",
    "text": "Text chart",
    "trail": "Line chart",
    "geoshape": "Map",
}


def parse_vegalite_spec(spec: dict[str, Any]) -> tuple[str, str, str, str]:
    """Extract (mark, x_field, y_field, title) from a Vega-Lite spec.

    Returns the plotext-compatible mark name. Raises ValueError on
    unsupported or malformed specs.
    """
    mark_raw = spec.get("mark", "")
    if isinstance(mark_raw, dict):
        mark_type = mark_raw.get("type", "")
    else:
        mark_type = str(mark_raw)

    if mark_type not in _SUPPORTED_MARKS:
        supported = ", ".join(sorted(_SUPPORTED_MARKS))
        raise ValueError(f"unsupported mark '{mark_type}'. Supported: {supported}")

    encoding = spec.get("encoding", {})
    x_enc = encoding.get("x", {})
    y_enc = encoding.get("y", {})

    x_field = x_enc.get("field")
    y_field = y_enc.get("field")

    if not x_field:
        raise ValueError("encoding.x.field is required")
    if not y_field:
        raise ValueError("encoding.y.field is required")

    title = spec.get("title", "")
    if isinstance(title, dict):
        title = title.get("text", "")

    return _MARK_TO_PLOTEXT[mark_type], str(x_field), str(y_field), str(title)


def resolve_column(df: pd.DataFrame, name: str) -> str | None:
    """Case-insensitive column name resolution."""
    for col in df.columns:
        if str(col).lower() == name.lower():
            return str(col)
    return None


def _mark_type(spec: dict[str, Any]) -> str:
    """Extract the mark type string from a spec (``""`` if absent/multi-view)."""
    mark = spec.get("mark", "")
    return str(mark.get("type", "")) if isinstance(mark, dict) else str(mark)


def is_plotext_renderable(spec: dict[str, Any]) -> bool:
    """Whether a Vega-Lite spec maps faithfully onto a plotext terminal chart.

    plotext plots raw DataFrame columns as a single x/y series, so only
    single-view specs with a supported mark, x and y fields, no grouping
    channels, and no data-reshaping transforms render the same as the browser
    (full Vega-Lite) would. Everything else falls back to the "open in browser"
    card rather than a misleading approximation.
    """
    if not isinstance(spec, dict):
        return False
    if "transform" in spec or any(key in spec for key in _MULTIVIEW_KEYS):
        return False
    if _mark_type(spec) not in _PLOTEXT_MARKS:
        return False
    encoding = spec.get("encoding")
    if not isinstance(encoding, dict):
        return False
    for channel in _GROUPING_CHANNELS:
        enc = encoding.get(channel)
        if isinstance(enc, dict) and enc.get("field"):
            return False
    for axis in ("x", "y"):
        enc = encoding.get(axis)
        if not isinstance(enc, dict) or not enc.get("field"):
            return False
        if any(key in enc for key in _RESHAPING_KEYS):
            return False
    return True


def chart_type_label(spec: dict[str, Any]) -> str:
    """Human-readable chart-type label for a spec (for UI cards and messages)."""
    if not isinstance(spec, dict):
        return "Chart"
    if any(key in spec for key in ("layer", "hconcat", "vconcat", "concat")):
        return "Composite chart"
    if "facet" in spec or "repeat" in spec:
        return "Faceted chart"
    return _MARK_LABELS.get(_mark_type(spec), "Chart")


def render_plotext(
    mark: str,
    x_field: str,
    y_field: str,
    title: str,
    df: pd.DataFrame,
    console_width: int | None = None,
    console_height: int | None = None,
    color: tuple[int, int, int] | None = None,
) -> str:
    """Render a plotext chart and return the built string.

    Raises on failure so the caller can report the error.
    """
    import plotext as plt

    effective_height = console_height or 18
    # In preview mode (no explicit height), cap width by an aspect ratio of
    # ~3:1 so the chart reads as a landscape preview — shorter and wider than
    # the chat-log content above it, giving room for axis labels without
    # crowding vertical space. In full-screen mode (explicit height), use the
    # full available width.
    if console_height is not None:
        effective_width = max(20, (console_width or 62) - 2)
    else:
        effective_width = min(max(20, (console_width or 62) - 2), effective_height * 3)

    plt.clear_figure()
    plt.theme("dark")
    plt.plotsize(effective_width, effective_height)

    plt.axes_color("default")
    plt.ticks_color("default")
    # Emit ANSI 49 ("default bg") for canvas cells so the chart composites
    # against the parent widget's bg at render time, instead of baking in
    # plt.theme("dark")'s concrete canvas color.
    plt.canvas_color("default")

    x_data = df[x_field].tolist()
    y_data = df[y_field].tolist()

    # Caller (e.g. the app) may pass a brand color; otherwise plotext's default.
    color_kw = {"color": color} if color is not None else {}

    if mark == "bar":
        x_labels = [str(v) for v in x_data]
        # Truncate labels so plotext doesn't skip any due to overlap.
        # Reserve ~4 chars for y-axis; divide remaining width among bars.
        max_label_len = max(1, (effective_width - 4) // max(len(x_labels), 1) - 1)
        tick_labels = [s[:max_label_len] if len(s) > max_label_len else s for s in x_labels]
        plt.bar(x_labels, y_data, **color_kw)
        plt.xticks(list(range(1, len(x_labels) + 1)), tick_labels)
    elif mark == "line":
        plt.plot(x_data, y_data, **color_kw)
    elif mark == "scatter":
        plt.scatter(x_data, y_data, **color_kw)

    if title:
        plt.title(title)
    plt.xlabel(x_field)
    plt.ylabel(y_field)

    return str(plt.build())


class RenderPlotextChartTool:
    """Attach a Vega-Lite chart spec to a stored query result.

    Validates the spec against the result DataFrame and stores it on the
    record. Simple x/y specs also get a terminal (plotext) preview; richer
    specs render in the browser via the full Vega runtime.
    """

    name: ClassVar = "render_chart"

    def __init__(self, history: QueryHistory | None = None) -> None:
        self._history = history or QueryHistory()

    async def __call__(self, record_id: str | None = None, *, vegalite_spec: str) -> str:
        """Attach a Vega-Lite chart specification to a query result.

        Accepts any Vega-Lite spec — single or multi-view: bar, line, point,
        area, arc/pie, heatmap, stacked/grouped bars via a color encoding,
        faceting, transforms, etc. Simple x/y charts preview in the terminal;
        richer charts open in the browser at full fidelity. When ``record_id``
        is omitted, the most recent query result is used.

        A dark theme is applied by the viewer, so leave colors unset unless the
        user asked for specific ones.

        Example spec:
            {"mark": "bar", "encoding": {"x": {"field": "status", "type": "nominal"}, "y": {"field": "count", "type": "quantitative"}}, "title": "Schools by Status"}

        Args:
            record_id: Optional query-history record ID (e.g. ``"Q3"``).
                If omitted, use the most recent query result.
            vegalite_spec: A Vega-Lite JSON specification string.
        """
        try:
            spec = json.loads(vegalite_spec)
        except (json.JSONDecodeError, TypeError) as e:
            return f"(error: invalid JSON — {e})"

        if not isinstance(spec, dict):
            return "(error: spec must be a JSON object)"

        if "mark" not in spec and not any(key in spec for key in _MULTIVIEW_KEYS):
            return "(error: spec must have a 'mark' or be a multi-view spec (layer/facet/concat))"

        try:
            record = await self._history.get(record_id) if record_id else await self._history.last()
        except KeyError:
            return f"(error: unknown record_id {record_id!r})"
        except ValueError:
            return "(error: no query has been executed yet — run a query first)"

        pred = record.pred_query

        if pred.exec_result is None or pred.exec_result.df is None:
            return f"(error: query {record.record_id} returned no data)"

        df = pred.exec_result.df
        if df.empty:
            return f"(error: query {record.record_id} result is empty)"

        if len(df) > _MAX_CHART_ROWS:
            return (
                f"(error: {len(df):,} rows is too large to chart — aggregate the result first "
                f"(e.g. GROUP BY) and chart the summary; max {_MAX_CHART_ROWS:,} rows)"
            )

        label = chart_type_label(spec)

        # Fail fast on the simple case, where x/y must be real columns. Richer
        # specs (color/facet/transform/multi-view) are validated by the browser
        # renderer; field-case mismatches are normalized at render time.
        if is_plotext_renderable(spec):
            mark, x_field, y_field, title = parse_vegalite_spec(spec)
            x_col = resolve_column(df, x_field)
            if x_col is None:
                return f"(error: column '{x_field}' not found. Available: {list(df.columns)})"
            y_col = resolve_column(df, y_field)
            if y_col is None:
                return f"(error: column '{y_field}' not found. Available: {list(df.columns)})"
            # Best-effort terminal preview; never fail the attach on plotext.
            try:
                render_plotext(mark, x_col, y_col, title, df)
            except Exception:
                pass
            self._history.attach_chart(record.record_id, spec)
            return f"{label} attached to {record.record_id} (x={x_col}, y={y_col}), {len(df):,} rows"

        self._history.attach_chart(record.record_id, spec)
        return f"{label} attached to {record.record_id} — {len(df):,} rows, renders in the browser"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
