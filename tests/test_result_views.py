"""Tests for building TUI result views from a ChatResult's artifacts."""

from __future__ import annotations

import pandas as pd

from tabulaflow.app.display import VIEW_KIND_DATA, VIEW_KIND_GRAPH, VIEW_KIND_MAP, VIEW_KIND_QUERY, build_card_views
from tabulaflow.chat.result import ChatResult, ChatResultGraph, ChatResultMap, ChatResultRecord


def _record(record_id: str, label: str) -> ChatResultRecord:
    return ChatResultRecord(
        record_id=record_id,
        label=label,
        query="SELECT 1",
        df=pd.DataFrame({"a": [1, 2]}),
        chart_spec=None,
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
        graph_spec={"layout": "force", "nodes": [], "edges": [{"record_id": "Q1", "source": "src", "target": "dst"}]},
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
