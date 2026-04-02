"""Tool that renders a chart from a Vega-Lite spec using plotext."""

from __future__ import annotations

import json
from typing import Any, ClassVar, Protocol

import pandas as pd
from pydantic_ai import Tool

from mintq.schema import PredQuery


class _QueryToolLike(Protocol):
    """Minimal interface for a tool that tracks the last executed query."""

    def last_pred_query(self) -> PredQuery: ...


_SUPPORTED_MARKS = {"bar", "line", "point", "rect"}

_MARK_TO_PLOTEXT = {
    "bar": "bar",
    "line": "line",
    "point": "scatter",
    "rect": "bar",
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


def render_plotext(
    mark: str,
    x_field: str,
    y_field: str,
    title: str,
    df: pd.DataFrame,
    width: int,
) -> str:
    """Render a plotext chart and return the built string.

    Raises on failure so the caller can report the error.
    """
    import plotext as plt

    from mintq.cli.theme import ACCENT_RGB

    effective_width = min(width, 60)
    effective_height = 25

    plt.clear_figure()
    plt.theme("dark")
    plt.plotsize(effective_width, effective_height)

    plt.axes_color("default")
    plt.ticks_color("default")

    x_data = df[x_field].tolist()
    y_data = df[y_field].tolist()

    color = ACCENT_RGB

    if mark == "bar":
        plt.bar([str(v) for v in x_data], y_data, color=color)
    elif mark == "line":
        plt.plot(x_data, y_data, color=color)
    elif mark == "scatter":
        plt.scatter(x_data, y_data, color=color)

    if title:
        plt.title(title)
    plt.xlabel(x_field)
    plt.ylabel(y_field)

    return str(plt.build())


class RenderPlotextChartTool:
    """Render a terminal chart from the last query result.

    Accepts a Vega-Lite spec (JSON string), extracts the core fields
    (mark, encoding.x, encoding.y, title), validates against the
    DataFrame, and does a test render via plotext. On success the spec
    and DataFrame are stored for later display.
    """

    name: ClassVar = "render_chart"

    def __init__(self, run_query_tool: _QueryToolLike, *, width: int = 120) -> None:
        self._run_query_tool = run_query_tool
        self._width = width
        self.last_vegalite_spec: dict[str, Any] | None = None
        self.last_chart_df: pd.DataFrame | None = None

    async def __call__(self, vegalite_spec: str) -> str:
        """Render a terminal chart from the last query result using a Vega-Lite specification.

        Call this after run_query to visualize the result. Only simple
        Vega-Lite specs are supported (single mark with x/y encoding).

        Supported marks: bar, line, point, rect.

        Example spec:
            {"mark": "bar", "encoding": {"x": {"field": "status", "type": "nominal"}, "y": {"field": "count", "type": "quantitative"}}, "title": "Schools by Status"}

        Args:
            vegalite_spec: A Vega-Lite JSON specification string.
        """
        try:
            spec = json.loads(vegalite_spec)
        except (json.JSONDecodeError, TypeError) as e:
            return f"(error: invalid JSON — {e})"

        if not isinstance(spec, dict):
            return "(error: spec must be a JSON object)"

        try:
            mark, x_field, y_field, title = parse_vegalite_spec(spec)
        except ValueError as e:
            return f"(error: {e})"

        try:
            pred = self._run_query_tool.last_pred_query()
        except ValueError:
            return "(error: no query has been executed yet — run a query first)"

        if pred.exec_result is None or pred.exec_result.df is None:
            return "(error: last query returned no data)"

        df = pred.exec_result.df
        if df.empty:
            return "(error: last query result is empty)"

        available = list(df.columns)

        x_col = resolve_column(df, x_field)
        if x_col is None:
            return f"(error: column '{x_field}' not found. Available: {available})"

        y_col = resolve_column(df, y_field)
        if y_col is None:
            return f"(error: column '{y_field}' not found. Available: {available})"

        try:
            render_plotext(mark, x_col, y_col, title, df, self._width)
        except Exception as e:
            return f"(error rendering chart: {e})"

        self.last_vegalite_spec = spec
        self.last_chart_df = df

        return f"Chart rendered: {mark} chart with {len(df)} data points (x={x_col}, y={y_col})"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
