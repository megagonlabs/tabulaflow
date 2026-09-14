"""Run the library guide examples against real SQLite and offline model transports."""

from collections.abc import AsyncIterator
import json
from pathlib import Path
import runpy
from typing import Any

from pandas.testing import assert_frame_equal
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
import pytest

from tabulaflow.agents import ChatSession
from tabulaflow.agents.llm import make_agent
from tabulaflow.core import ErrorInfo, ExecResult
from tabulaflow.data import SQLConnector
from tabulaflow.output.resolver import (
    OutputResolutionError,
    OutputResolver,
    ResolvedGraphArtifact,
    ResolvedOutput,
    ResolvedTableArtifact,
)
from tabulaflow.output.specs import GraphArtifactSpec, NumberParameter, OutputSpec
from tabulaflow.output.store import MaterializedResult, OutputStore


EXAMPLES = Path(__file__).resolve().parents[1] / "docs/examples"


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("TABULAFLOW_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TABULAFLOW_SCHEMA_CACHE_MODE", "off")
    monkeypatch.setenv("TABULAFLOW_SQL_QUERY_CACHE_MODE", "off")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    monkeypatch.setattr("tabulaflow.agents.trace.compute_api_cost", lambda *args, **kwargs: 0)


@pytest.fixture
def closed_connectors(monkeypatch: pytest.MonkeyPatch) -> list[SQLConnector]:
    closed: list[SQLConnector] = []
    original_close = SQLConnector.close_async

    async def record_close(self: SQLConnector) -> None:
        await original_close(self)
        closed.append(self)

    monkeypatch.setattr(SQLConnector, "close_async", record_close)
    return closed


@pytest.fixture
def queries(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ExecResult]]:
    calls: list[tuple[str, ExecResult]] = []
    original_query = SQLConnector.run_query_async

    async def record_query(self: SQLConnector, query: str, **kwargs: Any) -> ExecResult:
        result = await original_query(self, query, **kwargs)
        calls.append((query, result))
        return result

    monkeypatch.setattr(SQLConnector, "run_query_async", record_query)
    return calls


async def test_working_with_data(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
    closed_connectors: list[SQLConnector],
) -> None:
    restored_results: list[ExecResult] = []
    original_restore = ExecResult.model_validate_json

    def record_restore(cls: type[ExecResult], /, payload: str, **kwargs: Any) -> ExecResult:
        restored = original_restore(payload, **kwargs)
        restored_results.append(restored)
        return restored

    monkeypatch.setattr(ExecResult, "model_validate_json", classmethod(record_restore))
    example = runpy.run_path(str(EXAMPLES / "working_with_data.py"))
    await example["main"]()

    assert len(queries) == 1
    result = queries[0][1]
    assert result.error is None
    assert result.df is not None
    assert result.df.to_dict("records") == [
        {"product": "HDMI cable", "units_to_order": 8},
        {"product": "USB-C dock", "units_to_order": 7},
    ]
    assert len(restored_results) == 1
    restored = restored_results[0]
    assert restored.df is not None
    # Arrow restores string extension columns as object columns.
    assert_frame_equal(restored.df, result.df, check_dtype=False)
    assert restored.model_dump(exclude={"df"}) == result.model_dump(exclude={"df"})
    output = capsys.readouterr().out
    for expected in (
        "Tables: ['inventory']",
        "CREATE TABLE inventory",
        "DataFrame:",
        "As text:",
        "Restored DataFrame:",
        "units_to_order",
    ):
        assert expected in output
    assert len(closed_connectors) == 1


async def test_data_example_closes_after_query_failure(
    monkeypatch: pytest.MonkeyPatch, closed_connectors: list[SQLConnector]
) -> None:
    async def fail_query(self: SQLConnector, query: str, **kwargs: Any) -> ExecResult:
        return ExecResult(error=ErrorInfo(exc_type="RuntimeError", message="query unavailable"))

    monkeypatch.setattr(SQLConnector, "run_query_async", fail_query)
    example = runpy.run_path(str(EXAMPLES / "working_with_data.py"))
    with pytest.raises(RuntimeError, match="query unavailable"):
        await example["main"]()
    assert len(closed_connectors) == 1


@pytest.mark.parametrize(
    "script", ["working_with_data.py", "chat_sessions.py", "structured_outputs.py", "custom_agents.py"]
)
async def test_examples_close_after_data_preparation_failure(
    script: str, monkeypatch: pytest.MonkeyPatch, closed_connectors: list[SQLConnector]
) -> None:
    async def fail_write(self: SQLConnector, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("sample data unavailable")

    monkeypatch.setattr(SQLConnector, "write_dataframe_async", fail_write)
    with pytest.raises(RuntimeError, match="sample data unavailable"):
        await runpy.run_path(str(EXAMPLES / script))["main"]()
    assert len(closed_connectors) == 1


async def test_structured_outputs_resolve_lazily_and_reuse_results(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
    closed_connectors: list[SQLConnector],
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resolutions: list[ResolvedOutput] = []
    source_results: list[MaterializedResult] = []
    original_resolve = OutputResolver.resolve
    original_resolve_source = OutputStore.resolve_artifact_source

    async def record_source(self: OutputStore, source_id: str, selection: Any = None) -> MaterializedResult:
        result = await original_resolve_source(self, source_id, selection)
        source_results.append(result)
        return result

    async def record_resolution(self: OutputResolver, output: OutputSpec, selection: Any = None) -> ResolvedOutput:
        if not resolutions:
            assert not queries
            (parameter,) = output.parameters
            assert isinstance(parameter, NumberParameter)
            assert (parameter.min, parameter.max, parameter.step, parameter.default) == (0, 500, 50, 100)
            assert output.default_selection == {"min_units": 100}
            graph = output.artifacts[1]
            assert isinstance(graph, GraphArtifactSpec)
            assert graph.source_ids == [output.sources[0].id]
        assert OutputSpec.model_validate_json(output.model_dump_json()) == output
        resolved = await original_resolve(self, output, selection)
        resolutions.append(resolved)
        return resolved

    monkeypatch.setattr(OutputResolver, "resolve", record_resolution)
    monkeypatch.setattr(OutputStore, "resolve_artifact_source", record_source)
    example = runpy.run_path(str(EXAMPLES / "structured_outputs.py"))
    await example["main"]()

    assert len(queries) == 2
    assert "units >= 100" in queries[0][0]
    assert "units >= 300" in queries[1][0]
    assert len(resolutions) == len(source_results) == 3
    routes = [
        ("Chicago", "Dallas", 500),
        ("Chicago", "Denver", 200),
        ("Dallas", "Austin", 350),
    ]
    for resolved, source_result, threshold, result_id in zip(
        resolutions, source_results, (100, 300, 100), ("R1", "R2", "R1"), strict=True
    ):
        assert resolved.selection == {"min_units": threshold}
        table, graph = resolved.artifacts
        assert isinstance(table, ResolvedTableArtifact)
        assert isinstance(graph, ResolvedGraphArtifact)
        assert table.result is source_result
        assert table.result.metadata.id == result_id
        assert table.result.metadata.connector_alias == "logistics"
        assert table.result.df is not None
        expected_routes = [route for route in routes if route[2] >= threshold]
        assert table.result.df.to_dict("records") == [
            {"origin": origin, "destination": destination, "units": units}
            for origin, destination, units in expected_routes
        ]
        assert {node.id for node in graph.graph.nodes} == {
            warehouse for origin, destination, _ in expected_routes for warehouse in (origin, destination)
        }
        assert [(edge.source, edge.target, edge.label) for edge in graph.graph.edges] == [
            (origin, destination, str(units)) for origin, destination, units in expected_routes
        ]
        assert all(edge.directed for edge in graph.graph.edges)
    printed = capsys.readouterr().out
    assert printed.count("Result ID: R1") == 2
    assert "Unavailable:" not in printed
    assert printed.count("Graph nodes:") == printed.count("Graph edges:") == 3
    assert "Output JSON:" in printed
    assert len(closed_connectors) == 1


async def test_structured_outputs_report_unavailable_artifacts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], closed_connectors: list[SQLConnector]
) -> None:
    original_query = SQLConnector.run_query_async

    async def fail_threshold(self: SQLConnector, query: str, **kwargs: Any) -> ExecResult:
        if "units >= 300" in query:
            return ExecResult(error=ErrorInfo(exc_type="RuntimeError", message="transfers unavailable"))
        return await original_query(self, query, **kwargs)

    monkeypatch.setattr(SQLConnector, "run_query_async", fail_threshold)
    await runpy.run_path(str(EXAMPLES / "structured_outputs.py"))["main"]()
    printed = capsys.readouterr().out
    assert "Unavailable: transfer_table transfers unavailable" in printed
    assert "Unavailable: transfer_graph transfers unavailable" in printed
    assert printed.count("Result ID: R1") == 2
    assert len(closed_connectors) == 1


@pytest.mark.parametrize("threshold", [-50, 125, 550])
async def test_structured_outputs_reject_invalid_thresholds(
    threshold: int,
    monkeypatch: pytest.MonkeyPatch,
    queries: list[tuple[str, ExecResult]],
    closed_connectors: list[SQLConnector],
) -> None:
    original_resolve = OutputResolver.resolve

    async def invalid_selection(self: OutputResolver, output: OutputSpec, selection: Any = None) -> ResolvedOutput:
        return await original_resolve(self, output, {"min_units": threshold})

    monkeypatch.setattr(OutputResolver, "resolve", invalid_selection)
    with pytest.raises(OutputResolutionError, match="min_units"):
        await runpy.run_path(str(EXAMPLES / "structured_outputs.py"))["main"]()
    assert not queries
    assert len(closed_connectors) == 1


async def test_chat_sessions_keep_history_and_stream_followup(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
    closed_connectors: list[SQLConnector],
) -> None:
    closed_sessions: list[ChatSession] = []
    original_close = ChatSession.aclose

    async def record_close(self: ChatSession) -> None:
        await original_close(self)
        closed_sessions.append(self)

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str | dict[int, DeltaToolCall]]:
        prompts = [part.content for message in messages for part in message.parts if isinstance(part, UserPromptPart)]
        returns = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart) and part.tool_name == "run_query"
        ]
        assert "Which products are below their reorder point?" in prompts
        followup = "How many units of each should I order to reach those levels?" in prompts
        for part in returns:
            assert isinstance(part.content, str)
            assert "(error:" not in part.content
        expected_queries = 2 if followup else 1
        if len(returns) < expected_queries:
            query = (
                "SELECT product, reorder_point - on_hand AS units_to_order "
                "FROM inventory WHERE on_hand < reorder_point ORDER BY product"
            )
            yield {
                0: DeltaToolCall(name="run_query", json_args=json.dumps({"connector_alias": "stock", "query": query}))
            }
        elif followup:
            yield "ANSWER:\nOrder 8 HDMI cables"
            yield " and 7 USB-C docks."
        else:
            yield "ANSWER:\nHDMI cable and USB-C dock are below their reorder points."

    def make_test_agent(model: Any, **kwargs: Any) -> Any:
        return make_agent(FunctionModel(stream_function=respond), **kwargs)

    monkeypatch.setattr("tabulaflow.agents.chat.session.make_agent", make_test_agent)
    monkeypatch.setattr(ChatSession, "aclose", record_close)
    await runpy.run_path(str(EXAMPLES / "chat_sessions.py"))["main"]()

    printed = capsys.readouterr().out
    assert "HDMI cable and USB-C dock are below their reorder points." in printed
    assert "Tool: run_query" in printed
    assert "Order 8 HDMI cables and 7 USB-C docks." in printed
    assert "Usage:" in printed
    assert len(queries) == 2
    assert len(closed_sessions) == len(closed_connectors) == 1


async def test_chat_example_closes_after_model_failure(
    monkeypatch: pytest.MonkeyPatch, closed_connectors: list[SQLConnector]
) -> None:
    closed_sessions: list[ChatSession] = []
    original_close = ChatSession.aclose

    async def fail_run(self: ChatSession, question: Any) -> Any:
        raise RuntimeError("model unavailable")

    async def record_close(self: ChatSession) -> None:
        await original_close(self)
        closed_sessions.append(self)

    monkeypatch.setattr(ChatSession, "run", fail_run)
    monkeypatch.setattr(ChatSession, "aclose", record_close)
    with pytest.raises(RuntimeError, match="model unavailable"):
        await runpy.run_path(str(EXAMPLES / "chat_sessions.py"))["main"]()
    assert len(closed_sessions) == len(closed_connectors) == 1


async def test_custom_agent_uses_query_and_custom_tools(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
    closed_connectors: list[SQLConnector],
) -> None:
    steps: list[tuple[str, dict[str, Any]]] = [
        (
            "run_query",
            {
                "query": "SELECT product, reorder_point - on_hand AS shortfall, pack_size FROM inventory WHERE on_hand < reorder_point"
            },
        ),
        ("order_in_packs", {"shortfall": 7, "pack_size": 4}),
        ("order_in_packs", {"shortfall": 8, "pack_size": 5}),
    ]

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert {tool.name for tool in info.function_tools} == {"run_query", "order_in_packs"}
        assert info.instructions is not None and "CREATE TABLE inventory" in info.instructions
        returns = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]
        if returns:
            assert isinstance(returns[0].content, str)
            assert "(error:" not in returns[0].content
        if len(returns) == len(steps):
            assert [part.content for part in returns[1:]] == [8, 10]
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        info.output_tools[0].name, {"products": ["USB-C dock", "HDMI cable"], "total_units": 18}
                    )
                ]
            )
        name, arguments = steps[len(returns)]
        return ModelResponse(parts=[ToolCallPart(name, arguments)])

    def make_test_agent(model: Any, **kwargs: Any) -> Any:
        return make_agent(FunctionModel(function=respond), **kwargs)

    monkeypatch.setattr("tabulaflow.agents.llm.make_agent", make_test_agent)
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()

    printed = capsys.readouterr().out
    assert "Products: ['USB-C dock', 'HDMI cable']" in printed
    assert "Total units: 18" in printed
    assert "Query calls: 1" in printed
    assert len(queries) == 1
    assert len(closed_connectors) == 1


@pytest.mark.parametrize("shortfall, pack_size, expected", [(7, 4, 8), (8, 5, 10), (0, 4, 0), (8, 4, 8)])
def test_custom_tool_rounds_to_supplier_packs(shortfall: int, pack_size: int, expected: int) -> None:
    tool = runpy.run_path(str(EXAMPLES / "custom_agents.py"))["order_in_packs"]
    assert tool(shortfall, pack_size) == expected


@pytest.mark.parametrize("shortfall, pack_size", [(-1, 4), (3, 0), (3, -1)])
def test_custom_tool_rejects_invalid_quantities(shortfall: int, pack_size: int) -> None:
    tool = runpy.run_path(str(EXAMPLES / "custom_agents.py"))["order_in_packs"]
    with pytest.raises(ValueError):
        tool(shortfall, pack_size)
