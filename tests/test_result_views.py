"""Tests for building TUI result views from resolved output artifacts."""

from __future__ import annotations

from typing import Literal

import pandas as pd
from rich.console import Console

from tabulaflow.app.display import (
    CardGroup,
    VIEW_KIND_INFO,
    VIEW_KIND_CHART,
    VIEW_KIND_DATA,
    VIEW_KIND_GRAPH,
    VIEW_KIND_MAP,
    VIEW_KIND_QUERY,
    build_resolved_output_card_views,
)
from tabulaflow.app.widgets import AgentResultWidget
from tabulaflow.agents.chat import ChatResult
from tabulaflow.output.specs import (
    ChoiceOption,
    ChoiceParameter,
    NumberParameter,
    OutputSpec,
    ParameterSpec,
)
from tabulaflow.core import GraphResult, GraphResultEdge, GraphResultNode
from tabulaflow.output.resolver import (
    ResolvedChartArtifact,
    ResolvedArtifact,
    ResolvedGraphArtifact,
    ResolvedMapArtifact,
    ResolvedOutput,
    ResolvedTableArtifact,
    UnavailableArtifact,
)
from tabulaflow.output.store import ResultMetadata, ResultPayload


def _payload(
    result_id: str,
    *,
    df: pd.DataFrame | None = None,
    query: str = "SELECT 1",
    graph: GraphResult | None = None,
    connector_type: Literal["sql", "property_graph"] = "sql",
) -> ResultPayload:
    return ResultPayload(
        metadata=ResultMetadata(
            id=result_id,
            db_alias="debug",
            query=query,
            connector_type=connector_type,
            row_count=len(df) if df is not None else None,
            columns=[str(column) for column in df.columns] if df is not None else None,
        ),
        df=df,
        graph=graph,
    )


def _table(result_id: str, label: str) -> ResolvedTableArtifact:
    return ResolvedTableArtifact(
        artifact_id=result_id,
        source_id=result_id,
        label=label,
        payload=_payload(result_id, df=pd.DataFrame({"a": [1, 2]})),
    )


def _chart(chart_id: str, label: str) -> ResolvedChartArtifact:
    return ResolvedChartArtifact(
        artifact_id=chart_id,
        source_id="Q1",
        label=label,
        spec={
            "mark": "bar",
            "encoding": {
                "x": {"field": "region"},
                "y": {"field": "revenue"},
                "color": {"field": "region"},
            },
        },
        payload=_payload("Q1", df=pd.DataFrame({"region": ["north", "south"], "revenue": [10, 20]}), query=""),
    )


def _map(map_id: str, label: str) -> ResolvedMapArtifact:
    return ResolvedMapArtifact(
        artifact_id=map_id,
        label=label,
        spec={"title": "Cities", "layers": [{"type": "points", "source": "Q1", "lat": "c0", "lng": "c1"}]},
        payload_by_source={"Q1": _payload("Q1", df=pd.DataFrame({"lat": [37.7], "lng": [-122.4]}))},
    )


def _graph(graph_id: str, label: str) -> ResolvedGraphArtifact:
    return ResolvedGraphArtifact(
        artifact_id=graph_id,
        label=label,
        graph=GraphResult(
            nodes=[GraphResultNode(id="a"), GraphResultNode(id="b")], edges=[GraphResultEdge(source="a", target="b")]
        ),
        layout="force",
    )


def _groups(*artifacts: ResolvedArtifact) -> list[CardGroup]:
    return build_resolved_output_card_views(ResolvedOutput(selection={}, artifacts=list(artifacts)))


def test_map_artifact_yields_single_map_placeholder_view() -> None:
    groups = _groups(_map("MAP1", "cities"))
    assert len(groups) == 1
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_MAP]
    assert groups[0].artifact_id == "MAP1"


def test_artifacts_render_in_citation_order() -> None:
    groups = _groups(_table("Q1", "table1"), _map("MAP1", "map1"), _graph("GRAPH1", "graph1"), _table("Q2", "table2"))
    assert [g.artifact_id for g in groups] == ["Q1", "MAP1", "GRAPH1", "Q2"]
    assert [v.kind for v in groups[1].views] == [VIEW_KIND_MAP]
    assert [v.kind for v in groups[2].views] == [VIEW_KIND_GRAPH]
    assert VIEW_KIND_DATA in [v.kind for v in groups[0].views]
    assert VIEW_KIND_QUERY in [v.kind for v in groups[0].views]


def test_chart_artifact_yields_chart_data_views_with_source_result() -> None:
    groups = _groups(_chart("CHART1", "chart"))
    assert groups[0].artifact_id == "CHART1"
    assert groups[0].result_id == "Q1"
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_CHART, VIEW_KIND_DATA]


def test_table_artifact_has_no_chart_view() -> None:
    groups = _groups(_table("Q1", "table1"))
    assert groups[0].result_id == "Q1"
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_DATA, VIEW_KIND_QUERY]


def test_empty_table_artifact_keeps_data_view() -> None:
    card = ResolvedTableArtifact(
        artifact_id="Q1",
        source_id="Q1",
        label="empty",
        payload=_payload(
            "Q1", df=pd.DataFrame({"customer": pd.Series(dtype="object"), "value": pd.Series(dtype="int64")})
        ),
    )

    groups = _groups(card)

    assert [v.kind for v in groups[0].views] == [VIEW_KIND_DATA, VIEW_KIND_QUERY]
    assert groups[0].views[0].data_shape == (0, 2)


def test_empty_chart_artifact_skips_chart_but_keeps_data_view() -> None:
    card = _chart("CHART1", "empty chart")
    card = ResolvedChartArtifact(
        artifact_id=card.artifact_id,
        source_id=card.source_id,
        label=card.label,
        spec=card.spec,
        payload=_payload(
            "Q1", df=pd.DataFrame({"region": pd.Series(dtype="object"), "revenue": pd.Series(dtype="int64")}), query=""
        ),
    )

    groups = _groups(card)

    assert [v.kind for v in groups[0].views] == [VIEW_KIND_DATA]


def test_table_artifact_with_graph_has_graph_data_query_views() -> None:
    graph = GraphResult(
        nodes=[
            GraphResultNode(id="a", label="Alice", group="Person"),
            GraphResultNode(id="b", label="Bob", group="Person"),
        ],
        edges=[GraphResultEdge(source="a", target="b", label="KNOWS", directed=True)],
    )
    card = ResolvedTableArtifact(
        artifact_id="Q1",
        source_id="Q1",
        label="paths",
        payload=_payload("Q1", df=pd.DataFrame({"a": [1, 2]}), graph=graph, connector_type="property_graph"),
    )

    groups = _groups(card)

    assert [v.kind for v in groups[0].views] == [VIEW_KIND_GRAPH, VIEW_KIND_DATA, VIEW_KIND_QUERY]


def test_unavailable_artifact_yields_single_info_view() -> None:
    groups = _groups(
        UnavailableArtifact(
            artifact_id="placeholder:QoQ change",
            label="QoQ change",
            reason="only applies when Time period = Q2",
            status="not_applicable",
        )
    )

    assert len(groups) == 1
    assert groups[0].label == "QoQ change"
    assert groups[0].artifact_id == "placeholder:QoQ change"
    assert [v.kind for v in groups[0].views] == [VIEW_KIND_INFO]

    console = Console(width=80, record=True)
    console.print(groups[0].views[0].renderable)
    assert "only applies when Time period = Q2" in console.export_text()


def test_panel_result_widget_switches_combinations_and_preserves_card_views() -> None:
    controls: list[ParameterSpec] = [
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
    first_artifacts = [_table("Q1", "top"), _table("Q5", "fixed")]
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            output=OutputSpec(parameters=controls),
        ),
        _groups(*first_artifacts),
    )

    assert [(card.artifact_id, card.views[0].kind) for card in widget._cards] == [
        ("Q1", VIEW_KIND_DATA),
        ("Q5", VIEW_KIND_DATA),
    ]

    widget._move_interpretation_cursor(1)
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"ranking": "count", "period": "q2"}
    assert [(card.artifact_id, card.views[0].kind) for card in widget._cards] == [
        ("Q1", VIEW_KIND_DATA),
        ("Q5", VIEW_KIND_DATA),
    ]

    widget._move_interpretation_cursor(2)
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"ranking": "count", "period": "q3"}
    assert [(card.artifact_id, card.views[0].kind) for card in widget._cards] == [
        ("Q1", VIEW_KIND_DATA),
        ("Q5", VIEW_KIND_DATA),
    ]


def test_panel_result_widget_uses_choice_controls_as_primary_model() -> None:
    controls: list[ParameterSpec] = [
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
        _groups(_table("Q1", "top")),
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
        _groups(_table("Q1", "top")),
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
        _groups(_table("Q1", "players")),
    )

    assert widget._choice_count() == 0
    widget._move_interpretation_cursor(1)
    widget._apply_interpretation_cursor()
    assert widget._applied_selection == {"height_cm": 200}


def test_number_control_adjusts_pending_value_and_applies_on_space() -> None:
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            output=OutputSpec(
                parameters=[NumberParameter(id="threshold", label="Threshold", min=0, max=1, step=0.1, default=0.5)],
            ),
        ),
        _groups(_table("Q1", "players")),
    )

    widget._adjust_number_control(1)
    widget._adjust_number_control(1)

    assert abs(float(widget._pending_selection["threshold"]) - 0.7) < 1e-9
    assert widget._applied_selection == {"threshold": 0.5}
    widget._apply_interpretation_cursor()
    assert abs(float(widget._applied_selection["threshold"]) - 0.7) < 1e-9


def test_number_control_draft_reverts_when_cursor_moves_away() -> None:
    widget = AgentResultWidget(
        ChatResult(
            text="x",
            output=OutputSpec(
                parameters=[
                    NumberParameter(id="threshold", label="Threshold", min=0, max=1, step=0.1, default=0.5),
                    ChoiceParameter(id="metric", label="Metric", choices=[ChoiceOption(id="a", label="A")]),
                ],
            ),
        ),
        _groups(_table("Q1", "players")),
    )

    widget._adjust_number_control(1)
    widget._move_interpretation_cursor(1)

    assert widget._pending_selection["threshold"] == 0.5
    assert widget._applied_selection["threshold"] == 0.5


def test_browser_only_chart_placeholder_uses_artifact_caption() -> None:
    groups = _groups(_chart("CHART1", "chart"))
    chart_view = groups[0].views[0]
    assert chart_view.kind == VIEW_KIND_CHART

    console = Console(width=80, record=True)
    console.print(chart_view.renderable)
    rendered = console.export_text()

    assert "Open the browser pane to view this chart." in rendered
    assert "Open this one in your browser" not in rendered


def test_map_artifact_payload_survives_terminal_render() -> None:
    artifact = _map("MAP1", "cities")
    _groups(artifact)
    assert artifact.payload_by_source["Q1"].df is not None


def test_graph_artifact_graph_result_survives_terminal_render() -> None:
    artifact = _graph("GRAPH1", "lineage")
    _groups(artifact)
    assert len(artifact.graph.nodes) == 2
