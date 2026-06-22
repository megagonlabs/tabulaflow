"""Tests for the chart spec predicate, type labels, and Vega HTML rendering."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tabulaflow.app.dump import render_chart_html
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub.query_history import QueryHistory
from tabulaflow.toolhub.render_chart import (
    RenderChartTool,
    chart_type_label,
    is_plotext_renderable,
)

SIMPLE_BAR: dict[str, object] = {"mark": "bar", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}}}


class TestIsPlotextRenderable:
    @pytest.mark.parametrize(
        "spec,expected",
        [
            (SIMPLE_BAR, True),
            ({"mark": "line", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}}}, True),
            ({"mark": "point", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}}}, True),
            # a constant color value (no field) keeps it a single series
            ({"mark": "bar", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}, "color": {"value": "#f00"}}}, True),
            # a grouping channel bound to a field reshapes it
            ({"mark": "bar", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}, "color": {"field": "c"}}}, False),
            ({"mark": "bar", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}, "facet": {"field": "c"}}}, False),
            # data-reshaping transform on an axis
            ({"mark": "bar", "encoding": {"x": {"field": "a"}, "y": {"field": "b", "aggregate": "sum"}}}, False),
            # top-level transform
            (
                {"mark": "bar", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}}, "transform": [{"filter": "1"}]},
                False,
            ),
            # unsupported marks
            ({"mark": "arc", "encoding": {"theta": {"field": "a"}}}, False),
            ({"mark": "rect", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}}}, False),
            # multi-view
            ({"layer": []}, False),
            ({"facet": {"field": "a"}, "spec": SIMPLE_BAR}, False),
            # missing axis field
            ({"mark": "bar", "encoding": {"x": {"field": "a"}}}, False),
            ({"mark": "bar"}, False),
        ],
    )
    def test_predicate(self, spec: dict[str, object], expected: bool) -> None:
        assert is_plotext_renderable(spec) is expected


class TestChartTypeLabel:
    @pytest.mark.parametrize(
        "spec,label",
        [
            ({"mark": "bar"}, "Bar chart"),
            ({"mark": {"type": "line"}}, "Line chart"),
            ({"mark": "arc"}, "Pie chart"),
            ({"mark": "rect"}, "Heatmap"),
            ({"layer": []}, "Composite chart"),
            ({"facet": {"field": "a"}, "spec": {}}, "Faceted chart"),
            ({"mark": "somethingelse"}, "Chart"),
        ],
    )
    def test_label(self, spec: dict[str, object], label: str) -> None:
        assert chart_type_label(spec) == label


class TestRenderChartHtml:
    def _render(self, tmp_path: Path, df: pd.DataFrame, spec: dict[str, object]) -> str:
        out = tmp_path / "chart.html"
        render_chart_html(df, spec, out, title="t")
        return out.read_text()

    def test_offline_self_contained(self, tmp_path: Path) -> None:
        html = self._render(tmp_path, pd.DataFrame({"a": ["x", "y"], "b": [1, 2]}), SIMPLE_BAR)
        assert "vegaEmbed" in html
        # vendored libs are inlined — no external resource loads
        assert "<script src=" not in html
        assert 'src="http' not in html
        assert "<link " not in html

    def test_dark_theme_merged(self, tmp_path: Path) -> None:
        html = self._render(tmp_path, pd.DataFrame({"a": ["x"], "b": [1]}), SIMPLE_BAR)
        assert '"background": "#131720"' in html

    def test_field_case_normalized(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"status": ["x"], "count": [1]})
        spec: dict[str, object] = {"mark": "bar", "encoding": {"x": {"field": "STATUS"}, "y": {"field": "Count"}}}
        html = self._render(tmp_path, df, spec)
        assert '"field": "status"' in html
        assert '"field": "count"' in html
        assert '"field": "STATUS"' not in html

    def test_user_color_overrides_theme(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"a": ["x"], "b": [1]})
        spec = {"mark": {"type": "bar", "color": "#e11d48"}, "encoding": {"x": {"field": "a"}, "y": {"field": "b"}}}
        assert "#e11d48" in self._render(tmp_path, df, spec)

    def test_unit_spec_gets_responsive_width(self, tmp_path: Path) -> None:
        html = self._render(tmp_path, pd.DataFrame({"a": ["x"], "b": [1]}), SIMPLE_BAR)
        assert '"width": "container"' in html

    def test_facet_channel_not_forced_width(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"a": ["x"], "b": [1], "c": ["g"]})
        spec: dict[str, object] = {
            "mark": "bar",
            "encoding": {"x": {"field": "a"}, "y": {"field": "b"}, "facet": {"field": "c"}},
        }
        assert '"width": "container"' not in self._render(tmp_path, df, spec)

    def test_data_embedded_inline(self, tmp_path: Path) -> None:
        html = self._render(tmp_path, pd.DataFrame({"a": ["xyz"], "b": [42]}), SIMPLE_BAR)
        assert "spec.data={values:" in html
        assert '{"a":"xyz","b":42}' in html


async def _history_with(df: pd.DataFrame) -> QueryHistory:
    history = QueryHistory()
    await history.add("db", "sql", PredQuery(query="SELECT 1", exec_result=ExecResult(df=df)))
    return history


class TestRenderChartTool:
    async def test_simple_bar_attaches(self) -> None:
        history = await _history_with(pd.DataFrame({"a": ["x", "y"], "b": [1, 2]}))
        spec = {"mark": "bar", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}}}
        msg = await RenderChartTool(history=history)(vegalite_spec=json.dumps(spec))
        assert "Bar chart attached" in msg
        assert (await history.last()).vegalite_spec == spec

    async def test_rich_spec_attaches_for_browser(self) -> None:
        history = await _history_with(pd.DataFrame({"a": ["x", "y"], "b": [1, 2], "c": ["g", "h"]}))
        spec = {"mark": "arc", "encoding": {"theta": {"field": "b"}, "color": {"field": "c"}}}
        msg = await RenderChartTool(history=history)(vegalite_spec=json.dumps(spec))
        assert "renders in the browser" in msg
        assert (await history.last()).vegalite_spec == spec

    async def test_oversized_result_refused_without_attaching(self) -> None:
        history = await _history_with(pd.DataFrame({"a": range(20_001), "b": range(20_001)}))
        spec = {"mark": "bar", "encoding": {"x": {"field": "a"}, "y": {"field": "b"}}}
        msg = await RenderChartTool(history=history)(vegalite_spec=json.dumps(spec))
        assert "too large" in msg
        assert (await history.last()).vegalite_spec is None

    async def test_unknown_column_errors_without_attaching(self) -> None:
        history = await _history_with(pd.DataFrame({"a": ["x"], "b": [1]}))
        spec = {"mark": "bar", "encoding": {"x": {"field": "nope"}, "y": {"field": "b"}}}
        msg = await RenderChartTool(history=history)(vegalite_spec=json.dumps(spec))
        assert "not found" in msg
        assert (await history.last()).vegalite_spec is None
