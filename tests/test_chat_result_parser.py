from pathlib import Path
import json

import pandas as pd
import pytest
from pydantic_ai.messages import ToolReturnPart

from tabulaflow.chat.agent import _build_chat_result, _declared_bundle, _TextStreamRouter, _strip_answer_marker
from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.core.outputs import ChoiceOption, ChoiceParameter
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub import (
    ArtifactRef,
    ArtifactBundle,
    CreateParameterizedSourceTool,
    OutputResolver,
    OutputStore,
    RenderChartTool,
    ResolvedChartArtifact,
    ResolvedTableArtifact,
)


def _result_id(artifact: object, source_id: str | None = None) -> str:
    assert isinstance(artifact, ResolvedTableArtifact | ResolvedChartArtifact)
    if source_id is not None:
        assert artifact.source_id == source_id
    return artifact.payload.metadata.id


def test_strip_answer_marker_removes_the_marker() -> None:
    assert _strip_answer_marker("<answer>\nThere are 3 rows.") == "There are 3 rows."


def test_strip_answer_marker_leaves_unmarked_text_alone() -> None:
    text = "I'm tabulaflow, an interactive data assistant.\n\n---\nAsk me anything about your data."

    assert _strip_answer_marker(text) == text

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
        content="showing" if bundle is not None else "(error: unknown artifact id 'S9')",
        tool_call_id=call_id,
        metadata=bundle,
    )


def test_declared_bundle_skips_failed_calls_and_takes_the_last() -> None:
    first = ArtifactBundle(artifacts=(ArtifactRef(id="S1", label="first"),))
    second = ArtifactBundle(artifacts=(ArtifactRef(id="S1", label="second"),))
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
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace", "sql", PredQuery(query="SELECT 1", exec_result=ExecResult(df=pd.DataFrame({"a": [1]})))
    )
    bundle = ArtifactBundle(artifacts=(ArtifactRef(id="S1", label="row count"),))

    result = await _build_chat_result("<answer>\nThere is 1 row.", bundle, output_store)

    assert result.text == "There is 1 row."
    assert [artifact.id for artifact in result.output.artifacts] == ["S1"]
    assert result.output.sources[0].kind == "fixed"

    without = await _build_chat_result("<answer>\nNothing to show.", None, output_store)
    assert without.output.artifacts == []


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
    output_store = OutputStore(registry=registry)
    create_source = CreateParameterizedSourceTool(registry, output_store)
    # S1 varies over both dimensions; S2 only over period.
    await create_source(
        "workspace",
        [
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
        ],
        """
        SELECT customer, {% if ranking == "net" %} SUM(net) {% else %} COUNT(*) {% endif %} AS value
        FROM orders WHERE quarter = '{{ period }}' GROUP BY customer
        """,
    )
    await create_source(
        "workspace",
        [
            ChoiceParameter(
                id="period",
                label="Period",
                choices=[ChoiceOption(id="q2", label="Q2"), ChoiceOption(id="q3", label="Q3")],
            )
        ],
        "SELECT COUNT(*) AS orders FROM orders WHERE quarter = '{{ period }}'",
    )
    bundle = ArtifactBundle(
        artifacts=(ArtifactRef(id="S1", label="top customers"), ArtifactRef(id="S2", label="order count")),
    )

    result = await _build_chat_result("<answer>\nAcme leads.", bundle, output_store)

    assert result.output.default_selection == {"ranking": "net", "period": "q2"}
    resolved_output = await OutputResolver(output_store).resolve(
        result.output, {"ranking": "count", "period": "q3"}
    )
    assert _result_id(resolved_output.artifacts[0], "S1") == "R4"
    assert _result_id(resolved_output.artifacts[1], "S2") == "R6"
    resolver = OutputResolver(output_store)
    default_cards = await resolver.resolve(result.output)
    assert [_result_id(a) for a in default_cards.artifacts] == ["R1", "R5"]

    count_q2 = await resolver.resolve(result.output, {"ranking": "count", "period": "q2"})
    count_q3 = await resolver.resolve(result.output, {"ranking": "count", "period": "q3"})
    # "order count" ignores `ranking`, while "top customers" varies over both.
    assert [_result_id(a) for a in count_q2.artifacts] == ["R3", "R5"]
    assert [_result_id(a) for a in count_q3.artifacts] == ["R4", "R6"]


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
    output_store = OutputStore(registry=registry)
    await CreateParameterizedSourceTool(registry, output_store)(
        "workspace",
        [
            ChoiceParameter(
                id="period",
                label="Period",
                choices=[ChoiceOption(id="q2", label="Q2"), ChoiceOption(id="q3", label="Q3")],
            )
        ],
        "SELECT customer, SUM(net) AS value FROM orders WHERE quarter = '{{ period }}' GROUP BY customer",
    )
    spec = {"mark": "bar", "encoding": {"x": {"field": "customer"}, "y": {"field": "value"}}}
    await RenderChartTool(output_store=output_store)(source_id="S1", vegalite_spec=json.dumps(spec))
    bundle = ArtifactBundle(artifacts=(ArtifactRef(id="CHART1", label="top customers"),))

    result = await _build_chat_result("<answer>\nChart shown.", bundle, output_store)

    assert result.output.artifacts[0].kind == "chart"
    resolved_output = await OutputResolver(output_store).resolve(result.output, {"period": "q3"})
    assert _result_id(resolved_output.artifacts[0], "S1") == "R2"
    resolver = OutputResolver(output_store)
    default_cards = await resolver.resolve(result.output)
    q3_cards = await resolver.resolve(result.output, {"period": "q3"})
    chart_ids = [
        _result_id(default_cards.artifacts[0], "S1"),
        _result_id(q3_cards.artifacts[0], "S1"),
    ]
    assert chart_ids == ["R1", "R2"]


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
    output_store = OutputStore(registry=registry)
    await CreateParameterizedSourceTool(registry, output_store)(
        "workspace",
        [ChoiceParameter(id="period", label="Period", choices=[ChoiceOption(id="q2", label="Q2")])],
        "SELECT SUM(net) AS net FROM orders WHERE quarter = '{{ period }}'",
    )
    bundle = ArtifactBundle(artifacts=(ArtifactRef(id="S1", label="net revenue"),))

    result = await _build_chat_result("<answer>\n17 in the last quarter.", bundle, output_store)

    assert result.output.default_selection == {"period": "q2"}
    with pytest.raises(Exception, match="not a valid choice"):
        await OutputResolver(output_store).resolve(result.output, {"period": "q3"})
    assert [a.label for a in result.output.artifacts] == ["net revenue"]
