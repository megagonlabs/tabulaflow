"""Run the library guide examples against real SQLite and offline model transports."""

from collections.abc import AsyncIterator
import json
from pathlib import Path
import runpy
from typing import Any

from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
import pytest

from tabulaflow.agents import ChatSession
from tabulaflow.agents.llm import make_agent
from tabulaflow.core import ErrorInfo, ExecResult
from tabulaflow.data import SQLConnector
from tabulaflow.output.resolver import OutputResolver, ResolvedChartArtifact, ResolvedOutput, ResolvedTableArtifact
from tabulaflow.output.specs import OutputSpec


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
    capsys: pytest.CaptureFixture[str], queries: list[tuple[str, ExecResult]], closed_connectors: list[SQLConnector]
) -> None:
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
    output = capsys.readouterr().out
    for expected in ("Tables: ['inventory']", "CREATE TABLE inventory", "DataFrame:", "As text:", "units_to_order"):
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


async def test_structured_outputs_resolve_lazily_and_reuse_results(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
    closed_connectors: list[SQLConnector],
) -> None:
    resolutions: list[ResolvedOutput] = []
    original_resolve = OutputResolver.resolve

    async def record_resolution(self: OutputResolver, output: OutputSpec, selection: Any = None) -> ResolvedOutput:
        if not resolutions:
            assert not queries
        assert OutputSpec.model_validate_json(output.model_dump_json()) == output
        resolved = await original_resolve(self, output, selection)
        resolutions.append(resolved)
        return resolved

    monkeypatch.setattr(OutputResolver, "resolve", record_resolution)
    example = runpy.run_path(str(EXAMPLES / "structured_outputs.py"))
    await example["main"]()

    assert len(queries) == 2
    assert "SUM(revenue_usd)" in queries[0][0]
    assert "SUM(profit_usd)" in queries[1][0]
    for resolved, amounts, result_id in zip(resolutions, ([1500, 2000], [450, 400], [1500, 2000]), ("R1", "R2", "R1")):
        table, chart = resolved.artifacts
        assert isinstance(table, ResolvedTableArtifact)
        assert isinstance(chart, ResolvedChartArtifact)
        assert table.result is chart.result
        assert table.result.metadata.id == result_id
        assert table.result.metadata.connector_alias == "sales"
        assert table.result.df is not None
        assert table.result.df["region"].tolist() == ["East", "West"]
        assert table.result.df["amount"].tolist() == amounts
        assert chart.spec["mark"] == "bar"
    assert len(resolutions) == 3
    printed = capsys.readouterr().out
    assert printed.count("Result ID: R1") == 2
    assert "Unavailable:" not in printed
    assert "Output JSON:" in printed
    assert len(closed_connectors) == 1


async def test_structured_outputs_report_unavailable_artifacts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], closed_connectors: list[SQLConnector]
) -> None:
    original_query = SQLConnector.run_query_async

    async def fail_profit(self: SQLConnector, query: str, **kwargs: Any) -> ExecResult:
        if "SUM(profit_usd)" in query:
            return ExecResult(error=ErrorInfo(exc_type="RuntimeError", message="profit unavailable"))
        return await original_query(self, query, **kwargs)

    monkeypatch.setattr(SQLConnector, "run_query_async", fail_profit)
    await runpy.run_path(str(EXAMPLES / "structured_outputs.py"))["main"]()
    printed = capsys.readouterr().out
    assert "Unavailable: regional_table profit unavailable" in printed
    assert "Unavailable: regional_chart profit unavailable" in printed
    assert printed.count("Result ID: R1") == 2
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
