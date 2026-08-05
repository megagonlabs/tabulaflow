"""Tests for building TUI result views from a ChatResult's artifacts."""

from __future__ import annotations

from typing import cast

import pandas as pd
from rich.console import Console

from tabulaflow.app.widgets import AgentResultWidget
from tabulaflow.app.display import (
    VIEW_KIND_INFO,
    VIEW_KIND_CHART,
    VIEW_KIND_DATA,
    VIEW_KIND_GRAPH,
    VIEW_KIND_MAP,
    VIEW_KIND_QUERY,
    build_artifact_card_views,
    build_card_views,
)
from tabulaflow.chat.result import (
    ChatResult,
    ChatResultArtifact,
    ChatResultCard,
    ChatResultChart,
    ChatResultCombination,
    ChatResultGraph,
    ChatResultMap,
    ChatResultPanel,
    ChatResultPlaceholder,
    ChatResultTable,
    ChoiceControl,
    SliderControl,
)
from tabulaflow.core.types import GraphView
from tabulaflow.toolhub import Choice, Dimension


def _record(record_id: str, label: str) -> ChatResultTable:
    return ChatResultTable(
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
        graph=GraphView(nodes=[{"id": "a"}, {"id": "b"}], edges=[{"source": "a", "target": "b"}]),
        layout="force",
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


def test_placeholder_artifact_yields_single_info_view() -> None:
    groups = build_artifact_card_views(
        [ChatResultPlaceholder(label="QoQ change", message="only applies when Time period = Q2")]
    )

    assert len(groups) == 1
    assert groups[0].label == "QoQ change"
    assert groups[0].artifact_id == "placeholder:QoQ change"
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_INFO]

    console = Console(width=80, record=True)
    console.print(groups[0].views[0].renderable)
    assert "only applies when Time period = Q2" in console.export_text()


def test_panel_result_widget_switches_combinations_and_preserves_card_views() -> None:
    dims = [
        Dimension(
            id="ranking", label="Ranking", choices=[Choice(id="net", label="Net"), Choice(id="count", label="Count")]
        ),
        Dimension(id="period", label="Period", choices=[Choice(id="q2", label="Q2"), Choice(id="q3", label="Q3")]),
    ]
    first_artifacts = [_record("Q1", "top"), _record("Q5", "fixed")]
    combinations = [
        ChatResultCombination(
            selection={"ranking": "net", "period": "q2"}, artifacts=cast(list[ChatResultCard], first_artifacts)
        ),
        ChatResultCombination(
            selection={"ranking": "net", "period": "q3"}, artifacts=[_record("Q2", "top"), _record("Q5", "fixed")]
        ),
        ChatResultCombination(
            selection={"ranking": "count", "period": "q2"}, artifacts=[_record("Q3", "top"), _record("Q5", "fixed")]
        ),
        ChatResultCombination(
            selection={"ranking": "count", "period": "q3"},
            artifacts=[
                ChatResultPlaceholder(label="top", message="only applies when Period = Q2"),
                _record("Q5", "fixed"),
            ],
        ),
    ]
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            artifacts=cast(list[ChatResultArtifact], first_artifacts),
            panel=ChatResultPanel(dimensions=dims, combinations=combinations),
        )
    )

    assert [(card.artifact_id, card.views[0].kind) for card in widget._cards] == [
        ("Q1", VIEW_KIND_DATA),
        ("Q5", VIEW_KIND_DATA),
    ]

    widget._move_interpretation_cursor(1)  # ranking=count
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"ranking": "count", "period": "q2"}
    assert [(card.artifact_id, card.views[0].kind) for card in widget._cards] == [
        ("Q3", VIEW_KIND_DATA),
        ("Q5", VIEW_KIND_DATA),
    ]

    widget._move_interpretation_cursor(2)  # period=q3
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"ranking": "count", "period": "q3"}
    assert [(card.artifact_id, card.views[0].kind) for card in widget._cards] == [
        ("placeholder:top", VIEW_KIND_INFO),
        ("Q5", VIEW_KIND_DATA),
    ]


def test_panel_result_widget_uses_choice_controls_as_primary_model() -> None:
    controls = [
        ChoiceControl(
            id="ranking",
            label="Ranking",
            choices=[Choice(id="net", label="Net"), Choice(id="count", label="Count")],
        )
    ]
    stale_dimensions = [
        Dimension(id="period", label="Period", choices=[Choice(id="q2", label="Q2"), Choice(id="q3", label="Q3")])
    ]
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            artifacts=[_record("Q1", "top")],
            panel=ChatResultPanel(
                controls=controls,
                dimensions=stale_dimensions,
                combinations=[
                    ChatResultCombination(selection={"ranking": "net"}, artifacts=[_record("Q1", "top")]),
                    ChatResultCombination(selection={"ranking": "count"}, artifacts=[_record("Q2", "top")]),
                ],
            ),
        )
    )

    assert widget._choice_count() == 2
    widget._move_interpretation_cursor(1)
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"ranking": "count"}
    assert [card.artifact_id for card in widget._cards] == ["Q2"]


def test_slider_only_panel_does_not_crash_choice_navigation() -> None:
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            artifacts=[_record("Q1", "players")],
            panel=ChatResultPanel(
                controls=[SliderControl(id="height_cm", label="Minimum height", min=180, max=220, step=1, default=200)],
                combinations=[ChatResultCombination(selection={"height_cm": 200}, artifacts=[_record("Q1", "players")])],
            ),
        )
    )

    assert widget._choice_count() == 0
    widget._move_interpretation_cursor(1)
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"height_cm": 200}


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


def test_graph_artifact_graph_view_survives_terminal_render() -> None:
    chat_graph = _graph("GRAPH1", "lineage")
    result = ChatResult(text="x", artifacts=[chat_graph])
    build_card_views(result)
    assert len(chat_graph.graph.nodes) == 2
