"""Tests for building TUI result views from a ChatResult's artifacts."""

from __future__ import annotations

import pandas as pd
from rich.console import Console

from tabulaflow.app.display import (
    VIEW_KIND_CHART,
    VIEW_KIND_DATA,
    VIEW_KIND_GRAPH,
    VIEW_KIND_MAP,
    VIEW_KIND_QUERY,
    build_card_views,
)
from tabulaflow.chat.result import ChatResult, ChatResultChart, ChatResultGraph, ChatResultMap, ChatResultRecord
from tabulaflow.core.types import GraphView


def _record(record_id: str, label: str) -> ChatResultRecord:
    return ChatResultRecord(
        record_id=record_id,
        label=label,
        query="SELECT 1",
        df=pd.DataFrame({"a": [1, 2]}),
        query_lexer="sql",
    )


def _browser_only_chart(chart_id: str, label: str) -> ChatResultChart:
    return ChatResultChart(
        chart_id=chart_id,
        record_id="Q1",
        label=label,
        chart_spec={
            "mark": "bar",
            "encoding": {
                "x": {"field": "region"},
                "y": {"field": "revenue"},
                "color": {"field": "region"},
            },
        },
        query=None,
        df=pd.DataFrame({"region": ["north", "south"], "revenue": [10, 20]}),
        query_lexer="sql",
    )


def _map(map_id: str, label: str) -> ChatResultMap:
    return ChatResultMap(
        map_id=map_id,
        label=label,
        map_spec={"title": "Cities", "layers": [{"type": "points", "source": "Q1", "lat": "c0", "lng": "c1"}]},
        sources={"Q1": pd.DataFrame({"lat": [37.7], "lng": [-122.4]})},
    )


def _graph(graph_id: str, label: str) -> ChatResultGraph:
    return ChatResultGraph(
        graph_id=graph_id,
        label=label,
        graph_spec={
            "layout": "force",
            "nodes": [{"record_id": "Q1", "id": "src"}, {"record_id": "Q1", "id": "dst"}],
            "edges": [{"record_id": "Q1", "source": "src", "target": "dst"}],
        },
        sources={"Q1": pd.DataFrame({"src": ["a"], "dst": ["b"]})},
    )


def test_map_artifact_yields_single_map_placeholder_view() -> None:
    result = ChatResult(text="x", artifacts=[_map("MAP1", "cities")])
    groups = build_card_views(result)
    assert len(groups) == 1
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_MAP]
    assert groups[0].artifact_id == "MAP1"


def test_artifacts_render_in_citation_order() -> None:
    result = ChatResult(
        text="x",
        artifacts=[_record("Q1", "table1"), _map("MAP1", "map1"), _graph("GRAPH1", "graph1"), _record("Q2", "table2")],
    )
    groups = build_card_views(result)
    assert [g.artifact_id for g in groups] == ["Q1", "MAP1", "GRAPH1", "Q2"]
    # The map group is map-only; the record groups keep their data/query views.
    assert [v.kind for v in groups[1].views] == [VIEW_KIND_MAP]
    assert [v.kind for v in groups[2].views] == [VIEW_KIND_GRAPH]
    assert VIEW_KIND_DATA in [v.kind for v in groups[0].views]
    assert VIEW_KIND_QUERY in [v.kind for v in groups[0].views]


def test_chart_artifact_yields_chart_data_views_with_source_record() -> None:
    result = ChatResult(text="x", artifacts=[_browser_only_chart("CHART1", "chart")])
    groups = build_card_views(result)
    assert groups[0].artifact_id == "CHART1"
    assert groups[0].source_record_id == "Q1"
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_CHART, VIEW_KIND_DATA]


def test_record_artifact_has_no_chart_view() -> None:
    result = ChatResult(text="x", artifacts=[_record("Q1", "table1")])
    groups = build_card_views(result)
    assert groups[0].source_record_id == "Q1"
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_DATA, VIEW_KIND_QUERY]


def test_record_artifact_with_graph_has_graph_data_query_views() -> None:
    record = _record("Q1", "paths")
    record.query_lexer = "cypher"
    record.graph = GraphView(
        nodes=[{"id": "a", "label": "Alice", "group": "Person"}, {"id": "b", "label": "Bob", "group": "Person"}],
        edges=[{"source": "a", "target": "b", "label": "KNOWS", "directed": True}],
    )
    result = ChatResult(text="x", artifacts=[record])

    groups = build_card_views(result)

    assert [v.kind for v in groups[0].views] == [VIEW_KIND_GRAPH, VIEW_KIND_DATA, VIEW_KIND_QUERY]


def test_browser_only_chart_placeholder_uses_artifact_caption() -> None:
    result = ChatResult(text="x", artifacts=[_browser_only_chart("CHART1", "chart")])
    groups = build_card_views(result)
    chart_view = groups[0].views[0]
    assert chart_view.kind == VIEW_KIND_CHART

    console = Console(width=80, record=True)
    console.print(chart_view.renderable)
    rendered = console.export_text()

    assert "Open the browser pane to view this chart." in rendered
    assert "Open this one in your browser" not in rendered


def test_map_artifact_sources_released_after_render() -> None:
    chat_map = _map("MAP1", "cities")
    result = ChatResult(text="x", artifacts=[chat_map])
    build_card_views(result)
    # DataFrame references are dropped once previews are rendered.
    assert chat_map.sources == {}


def test_graph_artifact_sources_released_after_render() -> None:
    chat_graph = _graph("GRAPH1", "lineage")
    result = ChatResult(text="x", artifacts=[chat_graph])
    build_card_views(result)
    assert chat_graph.sources == {}
