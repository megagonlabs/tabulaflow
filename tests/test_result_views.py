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
)
from tabulaflow.chat.result import (
    ChatResult,
    ResolvedArtifact,
    ResolvedChartArtifact,
    ResolvedGraphArtifact,
    ResolvedMapArtifact,
    ArtifactPlaceholder,
    ResolvedTableArtifact,
)
from tabulaflow.core.types import GraphView, GraphViewEdge, GraphViewNode
from tabulaflow.core.outputs import ChoiceOption, ChoiceParameter, NumberParameter, OutputSpec, ParameterDef


def _record(record_id: str, label: str) -> ResolvedTableArtifact:
    return ResolvedTableArtifact(
        record_id=record_id,
        label=label,
        query="SELECT 1",
        df=pd.DataFrame({"a": [1, 2]}),
        query_lexer="sql",
    )


def _browser_only_chart(chart_id: str, label: str) -> ResolvedChartArtifact:
    return ResolvedChartArtifact(
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


def _map(map_id: str, label: str) -> ResolvedMapArtifact:
    return ResolvedMapArtifact(
        map_id=map_id,
        label=label,
        map_spec={"title": "Cities", "layers": [{"type": "points", "source": "Q1", "lat": "c0", "lng": "c1"}]},
        sources={"Q1": pd.DataFrame({"lat": [37.7], "lng": [-122.4]})},
    )


def _graph(graph_id: str, label: str) -> ResolvedGraphArtifact:
    return ResolvedGraphArtifact(
        graph_id=graph_id,
        label=label,
        graph=GraphView(nodes=[GraphViewNode(id="a"), GraphViewNode(id="b")], edges=[GraphViewEdge(source="a", target="b")]),
        layout="force",
    )


def test_map_artifact_yields_single_map_placeholder_view() -> None:
    groups = build_artifact_card_views([_map("MAP1", "cities")])
    assert len(groups) == 1
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_MAP]
    assert groups[0].artifact_id == "MAP1"


def test_artifacts_render_in_citation_order() -> None:
    groups = build_artifact_card_views(
        [_record("Q1", "table1"), _map("MAP1", "map1"), _graph("GRAPH1", "graph1"), _record("Q2", "table2")]
    )
    assert [g.artifact_id for g in groups] == ["Q1", "MAP1", "GRAPH1", "Q2"]
    # The map group is map-only; the record groups keep their data/query views.
    assert [v.kind for v in groups[1].views] == [VIEW_KIND_MAP]
    assert [v.kind for v in groups[2].views] == [VIEW_KIND_GRAPH]
    assert VIEW_KIND_DATA in [v.kind for v in groups[0].views]
    assert VIEW_KIND_QUERY in [v.kind for v in groups[0].views]


def test_chart_artifact_yields_chart_data_views_with_source_record() -> None:
    groups = build_artifact_card_views([_browser_only_chart("CHART1", "chart")])
    assert groups[0].artifact_id == "CHART1"
    assert groups[0].source_record_id == "Q1"
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_CHART, VIEW_KIND_DATA]


def test_record_artifact_has_no_chart_view() -> None:
    groups = build_artifact_card_views([_record("Q1", "table1")])
    assert groups[0].source_record_id == "Q1"
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_DATA, VIEW_KIND_QUERY]


def test_record_artifact_with_graph_has_graph_data_query_views() -> None:
    record = _record("Q1", "paths")
    record.query_lexer = "cypher"
    record.graph = GraphView(
        nodes=[GraphViewNode(id="a", label="Alice", group="Person"), GraphViewNode(id="b", label="Bob", group="Person")],
        edges=[GraphViewEdge(source="a", target="b", label="KNOWS", directed=True)],
    )
    groups = build_artifact_card_views([record])

    assert [v.kind for v in groups[0].views] == [VIEW_KIND_GRAPH, VIEW_KIND_DATA, VIEW_KIND_QUERY]


def test_placeholder_artifact_yields_single_info_view() -> None:
    groups = build_artifact_card_views(
        [ArtifactPlaceholder(label="QoQ change", message="only applies when Time period = Q2")]
    )

    assert len(groups) == 1
    assert groups[0].label == "QoQ change"
    assert groups[0].artifact_id == "placeholder:QoQ change"
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_INFO]

    console = Console(width=80, record=True)
    console.print(groups[0].views[0].renderable)
    assert "only applies when Time period = Q2" in console.export_text()


def test_panel_result_widget_switches_combinations_and_preserves_card_views() -> None:
    controls: list[ParameterDef] = [
        ChoiceParameter(
            id="ranking",
            label="Ranking",
            choices=[ChoiceOption(id="net", label="Net"), ChoiceOption(id="count", label="Count")],
        ),
        ChoiceParameter(
            id="period",
            label="Period",
            choices=[ChoiceOption(id="q2", label="Q2"), ChoiceOption(id="q3", label="Q3")],
        ),
    ]
    first_artifacts = [_record("Q1", "top"), _record("Q5", "fixed")]
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            output=OutputSpec(parameters=controls),
        ),
        build_artifact_card_views(cast(list[ResolvedArtifact], first_artifacts)),
    )

    assert [(card.artifact_id, card.views[0].kind) for card in widget._cards] == [
        ("Q1", VIEW_KIND_DATA),
        ("Q5", VIEW_KIND_DATA),
    ]

    widget._move_interpretation_cursor(1)  # ranking=count
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"ranking": "count", "period": "q2"}
    # Without a query-history resolver, the widget updates selection state but keeps
    # the default fallback cards.
    assert [(card.artifact_id, card.views[0].kind) for card in widget._cards] == [
        ("Q1", VIEW_KIND_DATA),
        ("Q5", VIEW_KIND_DATA),
    ]

    widget._move_interpretation_cursor(2)  # period=q3
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"ranking": "count", "period": "q3"}
    assert [(card.artifact_id, card.views[0].kind) for card in widget._cards] == [
        ("Q1", VIEW_KIND_DATA),
        ("Q5", VIEW_KIND_DATA),
    ]


def test_panel_result_widget_uses_choice_controls_as_primary_model() -> None:
    controls: list[ParameterDef] = [
        ChoiceParameter(
            id="ranking",
            label="Ranking",
            choices=[ChoiceOption(id="net", label="Net"), ChoiceOption(id="count", label="Count")],
        )
    ]
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            output=OutputSpec(parameters=controls),
        ),
        build_artifact_card_views([_record("Q1", "top")]),
    )

    assert widget._choice_count() == 2
    widget._move_interpretation_cursor(1)
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"ranking": "count"}
    assert [card.artifact_id for card in widget._cards] == ["Q1"]


def test_result_widget_uses_output_parameters_without_legacy_panel() -> None:
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            output=OutputSpec(
                parameters=[
                    ChoiceParameter(
                        id="ranking",
                        label="Ranking",
                        choices=[ChoiceOption(id="net", label="Net"), ChoiceOption(id="count", label="Count")],
                    )
                ]
            ),
        ),
        build_artifact_card_views([_record("Q1", "top")]),
    )

    assert widget._choice_count() == 2
    widget._move_interpretation_cursor(1)
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"ranking": "count"}


def test_slider_only_panel_does_not_crash_choice_navigation() -> None:
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            output=OutputSpec(
                parameters=[
                    NumberParameter(id="height_cm", label="Minimum height", min=180, max=220, step=1, default=200)
                ],
            ),
        ),
        build_artifact_card_views([_record("Q1", "players")]),
    )

    assert widget._choice_count() == 0
    widget._move_interpretation_cursor(1)
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"height_cm": 200}


def test_browser_only_chart_placeholder_uses_artifact_caption() -> None:
    groups = build_artifact_card_views([_browser_only_chart("CHART1", "chart")])
    chart_view = groups[0].views[0]
    assert chart_view.kind == VIEW_KIND_CHART

    console = Console(width=80, record=True)
    console.print(chart_view.renderable)
    rendered = console.export_text()

    assert "Open the browser pane to view this chart." in rendered
    assert "Open this one in your browser" not in rendered


def test_map_artifact_sources_released_after_render() -> None:
    chat_map = _map("MAP1", "cities")
    build_artifact_card_views([chat_map])
    # DataFrame references are dropped once previews are rendered.
    assert chat_map.sources == {}


def test_graph_artifact_graph_view_survives_terminal_render() -> None:
    chat_graph = _graph("GRAPH1", "lineage")
    build_artifact_card_views([chat_graph])
    assert len(chat_graph.graph.nodes) == 2
