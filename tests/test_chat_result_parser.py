from pathlib import Path
import json

import pandas as pd
import pytest
from pydantic_ai.messages import ToolReturnPart

from tabulaflow.chat import AnswerPanel, ChoiceControl, ControlChoice, SliderControl
from tabulaflow.chat.agent import _build_chat_result, _declared_bundle, _TextStreamRouter, _strip_answer_marker
from tabulaflow.chat.artifact_resolver import ArtifactResolver
from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub import (
    ArtifactRef,
    ArtifactBundle,
    Choice,
    Dimension,
    QueryDimension,
    QueryHistory,
    RenderChartTool,
    RunQueryForEachCombinationTool,
)


def _record_id(artifact: object) -> str:
    assert getattr(artifact, "kind") == "table"
    record_id = getattr(artifact, "record_id")
    assert isinstance(record_id, str)
    return record_id


def test_strip_answer_marker_removes_the_marker() -> None:
    assert _strip_answer_marker("<answer>\nThere are 3 rows.") == "There are 3 rows."


def test_strip_answer_marker_leaves_unmarked_text_alone() -> None:
    text = "I'm tabulaflow, an interactive data assistant.\n\n---\nAsk me anything about your data."

    assert _strip_answer_marker(text) == text


def test_panel_default_selection_uses_first_choice() -> None:
    panel = AnswerPanel(
        controls=[
            ChoiceControl(
                id="ranking",
                label="Ranking",
                choices=[ControlChoice(id="net", label="Net"), ControlChoice(id="count", label="Count")],
            )
        ]
    )

    assert panel.default_selection == {"ranking": "net"}


def test_panel_accepts_slider_controls_without_dimensions() -> None:
    panel = AnswerPanel(
        controls=[SliderControl(id="height_cm", label="Minimum height", min=180, max=220, step=1, default=200)],
    )

    assert panel.controls[0].kind == "slider"
    assert panel.default_selection == {"height_cm": 200}


def test_text_stream_router_waits_for_the_answer_marker() -> None:
    router = _TextStreamRouter()

    assert router.feed("<ans") == ""
    assert router.feed("wer>") == ""
    assert router.feed("\nThere") == "There"
    assert router.is_answer
    assert router.feed(" are 3 rows.") == " are 3 rows."


def test_text_stream_router_routes_plain_prose_as_narration() -> None:
    router = _TextStreamRouter()

    assert router.feed("Thinking out loud.") == "Thinking out loud."
    assert not router.is_answer


def test_text_stream_router_resets_between_runs() -> None:
    router = _TextStreamRouter()

    assert router.feed("Looking at the schema.") == "Looking at the schema."
    assert not router.is_answer
    router.reset()
    assert router.feed("<answer>Done.") == "Done."
    assert router.is_answer


def _show_artifacts_part(call_id: str, bundle: ArtifactBundle | None) -> ToolReturnPart:
    return ToolReturnPart(
        tool_name="show_artifacts",
        content="showing" if bundle is not None else "(error: unknown artifact id 'Q9')",
        tool_call_id=call_id,
        metadata=bundle,
    )


def test_declared_bundle_skips_failed_calls_and_takes_the_last() -> None:
    first = ArtifactBundle(artifacts=(ArtifactRef(id="Q1", label="first"),))
    second = ArtifactBundle(artifacts=(ArtifactRef(id="Q1", label="second"),))
    completed = {
        "a": _show_artifacts_part("a", first),
        "b": ToolReturnPart(tool_name="run_query", content="1 row", tool_call_id="b"),
        "c": _show_artifacts_part("c", second),
        "d": _show_artifacts_part("d", None),  # a later call that errored
    }

    assert _declared_bundle(completed) is second
    assert _declared_bundle({"b": completed["b"]}) is None


@pytest.mark.asyncio
async def test_build_chat_result_resolves_the_declared_bundle() -> None:
    history = QueryHistory()
    await history.add(
        "workspace", "sql", PredQuery(query="SELECT 1", exec_result=ExecResult(df=pd.DataFrame({"a": [1]})))
    )
    bundle = ArtifactBundle(artifacts=(ArtifactRef(id="Q1", label="row count"),))

    result = await _build_chat_result("<answer>\nThere is 1 row.", bundle, history)

    assert result.text == "There is 1 row."
    assert [(artifact.source_id, artifact.label) for artifact in result.artifacts] == [("Q1", "row count")]
    assert result.primary_artifact_index == 0

    without = await _build_chat_result("<answer>\nNothing to show.", None, history)
    assert without.artifacts == []
    assert without.primary_artifact_index is None
    assert without.panel is None


@pytest.mark.asyncio
async def test_build_chat_result_resolves_a_panel(tmp_path: Path) -> None:
    """Each card resolves at the dimensions its own query ran; the rest broadcast."""
    connector = await SQLConnector.from_url_async(
        global_id="test-chat-panel",
        url=f"duckdb:///{tmp_path / 'w.duckdb'}",
        db_name="w",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    await connector.run_query_async("CREATE TABLE orders(customer TEXT, net INT, quarter TEXT)")
    await connector.run_query_async("INSERT INTO orders VALUES ('Acme', 10, 'q2'), ('Globex', 7, 'q3')")
    registry = DBRegistry()
    registry.register("workspace", connector)
    history = QueryHistory()
    runner = RunQueryForEachCombinationTool(registry, history=history)
    # QS1 varies over both dimensions; QS2 only over period.
    await runner(
        "workspace",
        [
            QueryDimension(id="ranking", choices=["net", "count"]),
            QueryDimension(id="period", choices=["q2", "q3"]),
        ],
        """
        SELECT customer, {% if ranking == "net" %} SUM(net) {% else %} COUNT(*) {% endif %} AS value
        FROM orders WHERE quarter = '{{ period }}' GROUP BY customer
        """,
    )
    await runner(
        "workspace",
        [QueryDimension(id="period", choices=["q2", "q3"])],
        "SELECT COUNT(*) AS orders FROM orders WHERE quarter = '{{ period }}'",
    )
    bundle = ArtifactBundle(
        artifacts=(ArtifactRef(id="QS1", label="top customers"), ArtifactRef(id="QS2", label="order count")),
        dimensions=(
            Dimension(
                id="ranking",
                label="Ranking",
                choices=[Choice(id="net", label="Net revenue"), Choice(id="count", label="Orders")],
            ),
            Dimension(id="period", label="Quarter", choices=[Choice(id="q2", label="Q2"), Choice(id="q3", label="Q3")]),
        ),
    )

    result = await _build_chat_result("<answer>\nAcme leads.", bundle, history)

    assert result.panel is not None
    assert result.panel.default_selection == {"ranking": "net", "period": "q2"}
    assert [artifact.kind for artifact in result.artifacts] == ["table", "table"]
    resolver = ArtifactResolver(history)
    default_cards = await resolver.resolve(result)
    assert [_record_id(a) for a in default_cards] == ["QS1_v0", "QS2_v0"]

    count_q2 = await resolver.resolve(result, {"ranking": "count", "period": "q2"})
    count_q3 = await resolver.resolve(result, {"ranking": "count", "period": "q3"})
    # "order count" ignores `ranking`, while "top customers" varies over both.
    assert [_record_id(a) for a in count_q2] == ["QS1_v2", "QS2_v0"]
    assert [_record_id(a) for a in count_q3] == ["QS1_v3", "QS2_v1"]


@pytest.mark.asyncio
async def test_build_chat_result_resolves_source_backed_chart_in_panel(tmp_path: Path) -> None:
    connector = await SQLConnector.from_url_async(
        global_id="test-chat-chart-panel",
        url=f"duckdb:///{tmp_path / 'w.duckdb'}",
        db_name="w",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    await connector.run_query_async("CREATE TABLE orders(customer TEXT, net INT, quarter TEXT)")
    await connector.run_query_async("INSERT INTO orders VALUES ('Acme', 10, 'q2'), ('Globex', 7, 'q3')")
    registry = DBRegistry()
    registry.register("workspace", connector)
    history = QueryHistory()
    runner = RunQueryForEachCombinationTool(registry, history=history)
    await runner(
        "workspace",
        [QueryDimension(id="period", choices=["q2", "q3"])],
        "SELECT customer, SUM(net) AS value FROM orders WHERE quarter = '{{ period }}' GROUP BY customer",
    )
    spec = {"mark": "bar", "encoding": {"x": {"field": "customer"}, "y": {"field": "value"}}}
    await RenderChartTool(history=history)(source_id="QS1", vegalite_spec=json.dumps(spec))
    bundle = ArtifactBundle(
        artifacts=(ArtifactRef(id="CHART1", label="top customers"),),
        dimensions=(
            Dimension(id="period", label="Quarter", choices=[Choice(id="q2", label="Q2"), Choice(id="q3", label="Q3")]),
        ),
    )

    result = await _build_chat_result("<answer>\nChart shown.", bundle, history)

    assert result.panel is not None
    assert [artifact.kind for artifact in result.artifacts] == ["chart"]
    resolver = ArtifactResolver(history)
    default_cards = await resolver.resolve(result)
    q3_cards = await resolver.resolve(result, {"period": "q3"})
    chart_ids = [getattr(default_cards[0], "record_id"), getattr(q3_cards[0], "record_id")]
    assert chart_ids == ["QS1_v0", "QS1_v1"]


@pytest.mark.asyncio
async def test_build_chat_result_placeholders_a_partially_covered_card(tmp_path: Path) -> None:
    connector = await SQLConnector.from_url_async(
        global_id="test-chat-partial",
        url=f"duckdb:///{tmp_path / 'w.duckdb'}",
        db_name="w",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    await connector.run_query_async("CREATE TABLE orders(net INT, quarter TEXT)")
    await connector.run_query_async("INSERT INTO orders VALUES (10, 'q2')")
    registry = DBRegistry()
    registry.register("workspace", connector)
    history = QueryHistory()
    runner = RunQueryForEachCombinationTool(registry, history=history)
    await runner(
        "workspace",
        [QueryDimension(id="period", choices=["q2"])],
        "SELECT SUM(net) AS net FROM orders WHERE quarter = '{{ period }}'",
    )
    bundle = ArtifactBundle(
        artifacts=(ArtifactRef(id="QS1", label="net revenue"),),
        dimensions=(
            Dimension(
                id="period",
                label="Time period",
                choices=[Choice(id="q2", label="Last completed quarter"), Choice(id="q3", label="Current quarter")],
            ),
        ),
    )

    result = await _build_chat_result("<answer>\n17 in the last quarter.", bundle, history)

    assert result.panel is not None
    assert result.panel.default_selection == {"period": "q2"}
    assert result.artifacts[0].kind == "table"
    uncovered = await ArtifactResolver(history).resolve(result, {"period": "q3"})
    assert uncovered[0].kind == "placeholder"
    assert uncovered[0].message == "only applies when Time period = Last completed quarter"
    assert uncovered[0].label == "net revenue"
    assert [a.label for a in result.artifacts] == ["net revenue"]
