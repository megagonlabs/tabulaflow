"""Tool that renders a chart from a Vega-Lite spec using plotext."""

from __future__ import annotations

import json
from typing import Any, ClassVar

import pandas as pd
from pydantic_ai import Tool

from mintq.toolhub.registry_run_query import QueryHistory


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
    console_width: int | None = None,
    console_height: int | None = None,
) -> str:
    """Render a plotext chart and return the built string.

    Raises on failure so the caller can report the error.
    """
    import plotext as plt

    from mintq.cli.theme import ACCENT_RGB

    effective_height = console_height or 25
    # In preview mode (no explicit height), cap width to keep chart roughly square.
    # In full-screen mode (explicit height), use the full available width.
    if console_height is not None:
        effective_width = max(20, (console_width or 62) - 2)
    else:
        effective_width = min(max(20, (console_width or 62) - 2), effective_height * 2)

    plt.clear_figure()
    plt.theme("dark")
    plt.plotsize(effective_width, effective_height)

    plt.axes_color("default")
    plt.ticks_color("default")

    x_data = df[x_field].tolist()
    y_data = df[y_field].tolist()

    color = ACCENT_RGB

    if mark == "bar":
        x_labels = [str(v) for v in x_data]
        # Truncate labels so plotext doesn't skip any due to overlap.
        # Reserve ~4 chars for y-axis; divide remaining width among bars.
        max_label_len = max(1, (effective_width - 4) // max(len(x_labels), 1) - 1)
        tick_labels = [s[:max_label_len] if len(s) > max_label_len else s for s in x_labels]
        plt.bar(x_labels, y_data, color=color)
        plt.xticks(list(range(1, len(x_labels) + 1)), tick_labels)
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
    """Render a terminal chart from a stored query result.

    Accepts a Vega-Lite spec (JSON string), extracts the core fields
    (mark, encoding.x, encoding.y, title), validates against the
    DataFrame, and does a test render via plotext. On success the spec
    and DataFrame are stored for later display.
    """

    name: ClassVar = "render_chart"

    def __init__(self, history: QueryHistory | None = None) -> None:
        self._history = history or QueryHistory()

    async def __call__(self, record_id: str | None = None, *, vegalite_spec: str) -> str:
        """Render a terminal chart from a stored query result using a Vega-Lite specification.

        Call this after ``run_query`` to visualize a result. When
        ``record_id`` is omitted, the most recent query result is used.
        Only simple Vega-Lite specs are supported (single mark with x/y
        encoding).

        Supported marks: bar, line, point, rect.

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

        try:
            mark, x_field, y_field, title = parse_vegalite_spec(spec)
        except ValueError as e:
            return f"(error: {e})"

        try:
            record = self._history.get(record_id) if record_id else self._history.last()
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

        available = list(df.columns)

        x_col = resolve_column(df, x_field)
        if x_col is None:
            return f"(error: column '{x_field}' not found. Available: {available})"

        y_col = resolve_column(df, y_field)
        if y_col is None:
            return f"(error: column '{y_field}' not found. Available: {available})"

        try:
            render_plotext(mark, x_col, y_col, title, df)
        except Exception as e:
            return f"(error rendering chart: {e})"

        self._history.attach_chart(record.record_id, spec)

        return f"Chart rendered from {record.record_id}: {mark} chart with {len(df)} data points (x={x_col}, y={y_col})"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
