"""Tool that renders a Vega-Lite chart from a query result as a chart artifact.

Simple x/y specs also get a plotext terminal preview here; the full chart
renders in the browser output pane.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, ClassVar

import pandas as pd
from pydantic_ai import Tool

from tabulaflow.output.charts import (
    ChartSpecError,
    chart_type_label,
    validate_chart_spec,
)
from tabulaflow.output.specs import FixedResultSource, ParameterizedSource
from tabulaflow.output.store import OutputStore


# Marks plotext can draw faithfully as a single x/y series, mapped to the
# plotext function used to draw each. ``_PLOTEXT_MARKS`` is derived so the two
# never drift.
_MARK_TO_PLOTEXT = {
    "bar": "bar",
    "line": "line",
    "point": "scatter",
}
_PLOTEXT_MARKS = frozenset(_MARK_TO_PLOTEXT)


def _mark_type(spec: dict[str, Any]) -> str:
    mark = spec.get("mark", "")
    return str(mark.get("type", "")) if isinstance(mark, dict) else str(mark)


def _resolve_column(df: pd.DataFrame, name: str) -> str | None:
    for column in df.columns:
        if str(column).casefold() == name.casefold():
            return str(column)
    return None


def _validate_source_id(source_id: str) -> None:
    if source_id.startswith("S"):
        return
    raise ValueError(f"source_id must start with 'S', got {source_id!r}")


@dataclass(frozen=True)
class _SourceVariant:
    label: str
    result_id: str
    df: pd.DataFrame


# Terminal preview gets unreadable past these counts (bar labels collapse to a
# char; plotext slows on dense series). Beyond them ``render_plotext`` raises
# ``ChartNotRenderable`` so the caller shows the browser card instead.
_PLOTEXT_MAX_BARS = 50
_PLOTEXT_MAX_POINTS = 1_000

# Bar thickness as a fraction of its slot, so plotext leaves a gap between bars
# instead of drawing them flush (the default ~1.0 makes few bars merge into one
# block). Half-slot keeps a gap even at the short preview height; gaps still fade at
# high bar counts — a terminal-resolution limit, not a value this can beat.
_BAR_WIDTH = 0.5

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
# Encoding-level transforms that change the data plotext would see (it plots raw
# columns, so these diverge from what Vega computes). ``sort`` is intentionally not
# here: charted data is virtually always already ordered by the query, so a sorted
# spec still previews faithfully — losing the preview for every sorted bar chart to
# cover the rare unsorted case isn't worth it.
_RESHAPING_KEYS = ("aggregate", "bin", "timeUnit")


def parse_vegalite_spec(spec: dict[str, Any]) -> tuple[str, str, str, str]:
    """Extract (mark, x_field, y_field, title) from a Vega-Lite spec.

    Returns the plotext-compatible mark name. Raises ValueError on
    unsupported or malformed specs.
    """
    mark_type = _mark_type(spec)

    if mark_type not in _PLOTEXT_MARKS:
        supported = ", ".join(sorted(_PLOTEXT_MARKS))
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


def _fill_bars_with_background(rendered: str, color: tuple[int, int, int]) -> str:
    """Repaint plotext bar fills as a background-colored space run.

    macOS Terminal adds line spacing that a foreground block glyph doesn't
    cover, leaving horizontal gaps in solid bars. A space with the bar color set
    as the cell *background* fills the whole cell (spacing included), so bars
    render gap-free. In a bar chart the bar color is the only thing drawn in that
    color, so converting every foreground run of it to background + spaces is safe.
    """
    r, g, b = color
    fg = f"\x1b[38;2;{r};{g};{b}m"
    bg = f"\x1b[48;2;{r};{g};{b}m"
    return re.compile(re.escape(fg) + r"([^\x1b\n]*)").sub(lambda m: bg + " " * len(m.group(1)), rendered)


def _is_numeric_column(col: pd.Series) -> bool:
    """True when the column's dtype is numeric (nullable ``Int64``/``Float64``
    included, ``bool`` excluded).

    plotext compares x/y values numerically, so a categorical/temporal column
    (strings, timestamps) must be plotted against integer positions instead.
    Dtype-based, so a NULL doesn't demote a numeric column to categorical the way a
    per-value check would.
    """
    return pd.api.types.is_numeric_dtype(col) and not pd.api.types.is_bool_dtype(col)


def _truncate_tick_labels(values: list[Any], width: int, *, stacked: bool = False) -> list[str]:
    """Stringify axis values and truncate each so the tick labels fit.

    Side-by-side ticks (a vertical bar's x-axis, a line/scatter x-axis) share the
    width without plotext dropping overlapping ones. ``stacked`` ticks (a horizontal
    bar's y-axis, one label per row) instead get a fixed left-margin budget, since
    they don't compete for horizontal space.
    """
    labels = [str(v) for v in values]
    if stacked:
        max_len = min(24, max(4, width // 4))
    else:
        max_len = max(1, (width - 4) // max(len(labels), 1) - 1)
    return [s[:max_len] if len(s) > max_len else s for s in labels]


class ChartNotRenderable(Exception):
    """A structurally valid spec whose data can't be drawn faithfully in the
    terminal (e.g. no numeric measure axis). The caller falls back to the browser
    card instead of surfacing this as an error."""


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

    The measure axis is the numeric column, inferred from the data, so a bar chart
    draws vertically (categories on x) or horizontally (categories on y) as the spec
    intends. Fields resolve case-insensitively; rows null on either axis (and
    non-finite measures) are dropped first. Raises ``ChartNotRenderable`` when a
    field is missing, no rows remain, no axis is numeric, or the mark is unsupported
    — the caller falls back to the browser card; other failures raise for the caller
    to report.
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

    x_col = _resolve_column(df, x_field)
    y_col = _resolve_column(df, y_field)
    if x_col is None or y_col is None:
        raise ChartNotRenderable(f"chart field not found (x='{x_field}', y='{y_field}')")

    # Keep only rows plottable on both axes: drop nulls and non-finite measures,
    # which break plotext's numeric axis. Bail to the card if nothing remains.
    data = pd.DataFrame({"x": df[x_col], "y": df[y_col]})
    data = data.replace([float("inf"), float("-inf")], float("nan")).dropna()
    if data.empty:
        raise ChartNotRenderable(f"no plottable rows for '{x_field}'/'{y_field}'")
    max_rows = _PLOTEXT_MAX_BARS if mark == "bar" else _PLOTEXT_MAX_POINTS
    if len(data) > max_rows:
        raise ChartNotRenderable(f"too many rows for a terminal {mark} chart ({len(data)} > {max_rows})")
    x_numeric = _is_numeric_column(data["x"])
    y_numeric = _is_numeric_column(data["y"])
    x_data = data["x"].tolist()
    y_data = data["y"].tolist()

    # Caller (e.g. the app) may pass a brand color; otherwise plotext's default.
    color_kw = {"color": color} if color is not None else {}

    positions = list(range(1, len(x_data) + 1))
    if mark == "bar":
        # A bar pairs a numeric measure axis with a categorical dimension axis.
        # Whichever column is numeric is the measure; orientation follows from the
        # channel it sits on — measure on y draws vertical bars, measure on x draws
        # horizontal bars (categories on the y-axis).
        if y_numeric:
            plt.bar([str(v) for v in x_data], y_data, width=_BAR_WIDTH, **color_kw)
            plt.xticks(positions, _truncate_tick_labels(x_data, effective_width))
        elif x_numeric:
            # plotext stacks the first category at the bottom; reverse so the first
            # data row sits at the top, matching the browser (Vega-Lite) and natural
            # reading order.
            rev_cats = list(reversed(y_data))
            plt.bar(
                [str(v) for v in rev_cats],
                list(reversed(x_data)),
                orientation="horizontal",
                width=_BAR_WIDTH,
                **color_kw,
            )
            plt.yticks(positions, _truncate_tick_labels(rev_cats, effective_width, stacked=True))
        else:
            raise ChartNotRenderable(f"bar chart has no numeric axis (x='{x_field}', y='{y_field}')")
    elif mark in ("line", "scatter"):
        if not y_numeric:
            raise ChartNotRenderable(f"{mark} chart needs a numeric y axis ('{y_field}')")
        plot = plt.plot if mark == "line" else plt.scatter
        if x_numeric:
            plot(x_data, y_data, **color_kw)
        else:
            # Categorical/temporal x (month names, date strings, …): plot against
            # integer positions with labeled ticks, since plotext compares x values
            # numerically and raises on strings.
            plot(positions, y_data, **color_kw)
            plt.xticks(positions, _truncate_tick_labels(x_data, effective_width))
    else:
        raise ChartNotRenderable(f"unsupported terminal mark '{mark}'")

    if title:
        plt.title(title)
    plt.xlabel(x_col)
    plt.ylabel(y_col)

    rendered = str(plt.build())
    # Bars are filled with a foreground block glyph, which leaves line-spacing
    # gaps in macOS Terminal; repaint them as background-colored spaces.
    if mark == "bar" and color is not None:
        rendered = _fill_bars_with_background(rendered, color)
    return rendered


class RenderChartTool:
    """Create a standalone chart artifact from a result or family source.

    Validates the spec against the source DataFrame(s) and stores it as a citable
    clean chart ``ArtifactSpec``. Simple x/y specs also get a terminal (plotext) preview;
    richer specs render in the browser via the full Vega runtime.
    """

    name: ClassVar = "render_chart"

    def __init__(self, output_store: OutputStore | None = None) -> None:
        self._output_store = output_store or OutputStore()

    async def __call__(self, source_id: str, *, vegalite_spec: str) -> str:
        """Create a Vega-Lite chart from a result or result-lookup source source.

        Accepts any Vega-Lite spec — single or multi-view: bar, line, point,
        area, arc/pie, heatmap, stacked/grouped bars via a color encoding,
        faceting, transforms, etc. Simple x/y charts preview in the terminal;
        richer charts open in the browser at full fidelity.

        Specs may bind inputs (e.g. a range slider via ``params``/``bind``) or
        selections for interactive filtering and zoom in the browser.

        A dark theme is applied by the viewer, so leave colors unset unless the
        user asked for specific ones.

        In a layered spec where any layer is colored by a field, every layer
        must declare a color: ``{"datum": "<series name>"}`` gives an overlay
        (e.g. a total line) its own legend entry and palette color;
        ``{"value": "<css color>"}`` sets a fixed color.

        Example spec:
            {"mark": "bar", "encoding": {"x": {"field": "status", "type": "nominal"}, "y": {"field": "count", "type": "quantitative"}}, "title": "Schools by Status"}

        Returns the new chart id (``CHART1``, ``CHART2``, …) to cite in the answer.

        Args:
            source_id: Output-store source ID, such as ``"S1"``.
            vegalite_spec: A Vega-Lite JSON specification string.
        """
        if not isinstance(source_id, str) or not source_id.strip():
            return "(error: source_id must be a non-empty string)"
        try:
            _validate_source_id(source_id)
        except ValueError as e:
            return f"(error: {e})"

        try:
            spec = json.loads(vegalite_spec)
        except (json.JSONDecodeError, TypeError) as e:
            return f"(error: invalid JSON — {e})"

        if not isinstance(spec, dict):
            return "(error: spec must be a JSON object)"

        try:
            variants = await self._source_variants(source_id)
        except KeyError:
            return f"(error: unknown source_id {source_id!r})"
        except ValueError as e:
            return f"(error: {e})"

        try:
            validate_chart_spec(spec, {variant.label: variant.df for variant in variants})
        except ChartSpecError as e:
            return f"(error: {e})"

        label = chart_type_label(spec)
        chart = self._output_store.add_chart_artifact(source_id, spec)
        chart_id = chart.id
        rows = len(variants[0].df)
        suffix = f" — {rows:,} rows" if len(variants) == 1 else f" — {len(variants):,} source variants"
        return f"{label} {chart_id} created from {source_id}{suffix}"

    async def _source_variants(self, source_id: str) -> list[_SourceVariant]:
        source = self._output_store.get_source(source_id)
        if isinstance(source, ParameterizedSource):
            out: list[_SourceVariant] = []
            for key, result_id in self._output_store.cached_parameterized_results(source.id).items():
                selection_dict = json.loads(key)
                selection = ";".join(f"{name}={value}" for name, value in sorted(selection_dict.items()))
                out.append(
                    _SourceVariant(
                        label=selection,
                        result_id=result_id,
                        df=(await self._output_store.get_payload(result_id)).df,
                    )
                )
            return out
        if isinstance(source, FixedResultSource):
            result_id = source.result_id
            return [
                _SourceVariant(
                    label=source_id, result_id=result_id, df=(await self._output_store.get_payload(result_id)).df
                )
            ]
        raise ValueError(f"source_id {source_id!r} is not chartable yet")

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
