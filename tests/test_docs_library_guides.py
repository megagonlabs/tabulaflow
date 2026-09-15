"""Run the library guide examples against real SQLite and offline model transports."""

from collections.abc import AsyncIterator
import ast
from io import BytesIO
import json
from pathlib import Path
import runpy
from typing import Any

import httpx
from pandas.testing import assert_frame_equal
from pydantic_ai import models
from pydantic_ai.messages import (
    BinaryContent,
    ModelMessage,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
from pypdf import PdfReader
import pytest

from tabulaflow.agents import ChatSession
from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.tools.run_query import QueryExecution
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
    assert (EXAMPLES / "results/library-inventory.txt").read_text().strip() in output
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
    assert (EXAMPLES / "results/library-transfers.txt").read_text().strip() in printed
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


@pytest.fixture
def support_model(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]]:
    steps: list[tuple[str, dict[str, Any]]] = []
    returns: list[ToolReturnPart] = []
    media: list[BinaryContent] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tools = {tool.name: tool for tool in info.function_tools}
        assert set(tools) == {"view", "find_orders", "lookup_order", "open_support_ticket"}
        assert set(tools["find_orders"].parameters_json_schema["properties"]) == {"product"}
        assert tools["find_orders"].parameters_json_schema["properties"]["product"]["type"] == "string"
        assert set(tools["lookup_order"].parameters_json_schema["properties"]) == {"order_id"}
        assert tools["lookup_order"].parameters_json_schema["properties"]["order_id"]["type"] == "integer"
        assert set(tools["open_support_ticket"].parameters_json_schema["properties"]) == {"order_id", "issue"}
        assert set(info.output_tools[0].parameters_json_schema["properties"]) == {
            "message",
            "suggested_steps",
            "references",
            "ticket_id",
        }
        assert info.instructions is not None
        assert "Follow faq.txt for support guidance" in info.instructions
        returns[:] = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]
        media[:] = [
            item
            for message in messages
            for part in message.parts
            if isinstance(part, UserPromptPart) and isinstance(part.content, list)
            for item in part.content
            if isinstance(item, BinaryContent)
        ]
        if len(returns) < len(steps):
            name, arguments = steps[len(returns)]
            return ModelResponse(parts=[ToolCallPart(name, arguments)])
        ticket_id = None
        references = []
        for part in returns:
            if part.tool_name == "open_support_ticket":
                assert isinstance(part.content, str)
                if not part.content.startswith("(error:"):
                    ticket_id = part.content
            elif part.tool_name == "view" and isinstance(part.content, str):
                if part.content.startswith("File: faq.txt"):
                    references.append("faq.txt")
                elif part.content.startswith("PDF: dock-guide.pdf"):
                    references.append("dock-guide.pdf, page 1")
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {
                        "message": (
                            f"The documented steps have not helped. I've opened ticket {ticket_id}."
                            if ticket_id
                            else "Please confirm which troubleshooting steps you have tried."
                        ),
                        "suggested_steps": []
                        if ticket_id
                        else [
                            "Enable Laptop charging in Dock settings > Power.",
                            "Reconnect the host USB-C cable.",
                        ],
                        "references": references,
                        "ticket_id": ticket_id,
                    },
                )
            ]
        )

    def make_test_agent(model: Any, **kwargs: Any) -> Any:
        return make_agent(FunctionModel(function=respond), **kwargs)

    monkeypatch.setattr("tabulaflow.agents.llm.make_agent", make_test_agent)
    return steps, returns, media


async def test_custom_agent_finds_order_reads_documents_and_opens_ticket(
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
    closed_connectors: list[SQLConnector],
) -> None:
    steps, returns, media = support_model
    issue = "USB-C dock still not charging after enabling Laptop charging and reconnecting the USB-C cable."
    steps.extend(
        [
            ("view", {"path": "."}),
            ("view", {"path": "faq.txt"}),
            ("find_orders", {"product": "dock"}),
            ("lookup_order", {"order_id": 1001}),
            ("view", {"path": "dock-guide.pdf", "view_range": [1, 1]}),
            ("open_support_ticket", {"order_id": 1001, "issue": issue}),
        ]
    )
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()

    for part in returns[:-1]:
        assert isinstance(part.content, str)
        assert "(error:" not in part.content
    assert returns[-1].content == "SUP-1"
    assert "faq.txt" in str(returns[0].content)
    assert "dock-guide.pdf" in str(returns[0].content)
    assert "Consult dock-guide.pdf" in str(returns[1].content)
    assert "Share the ticket ID for follow-up" in str(returns[1].content)
    search = returns[2].metadata
    assert isinstance(search, QueryExecution)
    assert search.parameter_values == {"product": "dock", "customer_id": 7}
    assert search.exec_result.df is not None
    assert search.exec_result.df.to_dict("records") == [
        {"order_id": 1001, "product": "USB-C dock", "purchased_on": "2026-08-18"},
        {"order_id": 1004, "product": "USB-C dock", "purchased_on": "2025-11-05"},
    ]
    execution = returns[3].metadata
    assert isinstance(execution, QueryExecution)
    assert execution.parameter_values == {"order_id": 1001, "customer_id": 7}
    assert execution.parameter_values["order_id"] == search.exec_result.df.iloc[0]["order_id"]
    assert execution.query == (
        "SELECT order_id, product, status FROM orders WHERE order_id = :order_id AND customer_id = :customer_id"
    )
    assert execution.exec_result.df is not None
    assert execution.exec_result.df.to_dict("records") == [
        {"order_id": 1001, "product": "USB-C dock", "status": "delivered"}
    ]
    assert len(media) == 1 and media[0].media_type == "application/pdf"
    pdf = PdfReader(BytesIO(media[0].data))
    assert len(pdf.pages) == 1
    assert len(pdf.pages[0].images) == 1
    screenshot = pdf.pages[0].images[0].image
    assert screenshot is not None
    pixels = screenshot.convert("RGB").tobytes()
    assert (
        sum(
            red > 180 and green < 90 and blue < 90
            for red, green, blue in zip(pixels[::3], pixels[1::3], pixels[2::3], strict=True)
        )
        > 1000
    )
    assert "Reconnect the laptop" in pdf.pages[0].extract_text()
    assert len(queries) == 3
    assert queries[0][0] == search.query
    assert all(query == execution.query for query, _ in queries[1:])
    printed = capsys.readouterr().out
    assert "Reply: The documented steps have not helped. I've opened ticket SUP-1." in printed
    assert "Suggested steps: []" in printed
    assert "References: ['faq.txt', 'dock-guide.pdf, page 1']" in printed
    assert "Ticket ID: SUP-1" in printed
    tickets = ast.literal_eval(printed.split("Stored tickets: ", 1)[1].splitlines()[0])
    assert tickets == [
        {
            "ticket_id": "SUP-1",
            "order_id": 1001,
            "issue": issue,
        }
    ]
    assert "Query calls: 3" in printed
    assert len(closed_connectors) == 1


@pytest.mark.parametrize(
    "product, expected_ids",
    [(" DOCK ", [1001, 1004]), ("Monitor", []), ("%", []), ("' OR 1=1 --", [])],
)
async def test_order_search_is_customer_scoped_and_uses_literal_product_names(
    product: str,
    expected_ids: list[int],
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
) -> None:
    steps, returns, _ = support_model
    steps.append(("find_orders", {"product": product}))
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()
    execution = returns[0].metadata
    assert isinstance(execution, QueryExecution)
    assert execution.parameter_values == {"product": product.strip(), "customer_id": 7}
    assert execution.exec_result.error is None
    assert execution.exec_result.df is not None
    assert execution.exec_result.df["order_id"].tolist() == expected_ids
    assert execution.exec_result.df.columns.tolist() == ["order_id", "product", "purchased_on"]


async def test_order_search_rejects_blank_product_names(
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    queries: list[tuple[str, ExecResult]],
) -> None:
    steps, returns, _ = support_model
    steps.append(("find_orders", {"product": "  "}))
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()
    assert returns[0].content == "(error: product must not be empty)"
    assert not queries


async def test_support_reply_can_return_guidance_without_a_ticket(
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    steps, returns, _ = support_model
    steps.extend(
        [
            ("view", {"path": "faq.txt"}),
            ("view", {"path": "dock-guide.pdf"}),
            ("lookup_order", {"order_id": 1001}),
        ]
    )
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()
    assert all(part.tool_name != "open_support_ticket" for part in returns)
    printed = capsys.readouterr().out
    assert "Reply: Please confirm which troubleshooting steps you have tried." in printed
    assert "Suggested steps: ['Enable Laptop charging" in printed
    assert "References: ['faq.txt', 'dock-guide.pdf, page 1']" in printed
    assert "Ticket ID: None" in printed
    assert "Stored tickets: []" in printed


async def test_ticket_action_accepts_an_owned_undelivered_order(
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
) -> None:
    steps, returns, _ = support_model
    steps.append(("open_support_ticket", {"order_id": 1003, "issue": "Charging stopped."}))
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()
    assert returns[0].content == "SUP-1"
    assert len(queries) == 1
    printed = capsys.readouterr().out
    tickets = ast.literal_eval(printed.split("Stored tickets: ", 1)[1].splitlines()[0])
    assert tickets == [{"ticket_id": "SUP-1", "order_id": 1003, "issue": "Charging stopped."}]
    assert "Ticket ID: SUP-1" in printed


async def test_support_workflow_uses_the_supplied_customer_identity(
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    tmp_path: Path,
    closed_connectors: list[SQLConnector],
) -> None:
    steps, returns, _ = support_model
    steps.extend(
        [
            ("find_orders", {"product": "Monitor"}),
            ("lookup_order", {"order_id": 1002}),
            ("open_support_ticket", {"order_id": 1001, "issue": "Charging stopped."}),
        ]
    )
    example = runpy.run_path(str(EXAMPLES / "custom_agents.py"))
    orders = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    try:
        await example["prepare_example"](orders, tmp_path)
        await example["run_support_agent"](orders, str(tmp_path), customer_id=8)
        assert not closed_connectors
    finally:
        await orders.close_async()
    search = returns[0].metadata
    assert isinstance(search, QueryExecution)
    assert search.parameter_values == {"product": "Monitor", "customer_id": 8}
    assert search.exec_result.df is not None
    assert search.exec_result.df["order_id"].tolist() == [1002]
    execution = returns[1].metadata
    assert isinstance(execution, QueryExecution)
    assert execution.parameter_values == {"order_id": 1002, "customer_id": 8}
    assert execution.exec_result.df is not None
    assert execution.exec_result.df.to_dict("records") == [
        {"order_id": 1002, "product": "Monitor", "status": "shipped"}
    ]
    assert returns[2].content == "(error: order not found for this customer)"


async def test_support_example_cleans_up_after_model_failure(
    monkeypatch: pytest.MonkeyPatch, closed_connectors: list[SQLConnector]
) -> None:
    directories: list[Path] = []

    def fail_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError("model unavailable")

    def make_test_agent(model: Any, **kwargs: Any) -> Any:
        return make_agent(FunctionModel(function=fail_model), **kwargs)

    monkeypatch.setattr("tabulaflow.agents.llm.make_agent", make_test_agent)
    example = runpy.run_path(str(EXAMPLES / "custom_agents.py"))
    original_prepare = example["prepare_example"]

    async def record_prepare(orders: SQLConnector, support_dir: Path) -> None:
        directories.append(support_dir)
        await original_prepare(orders, support_dir)

    monkeypatch.setitem(example["main"].__globals__, "prepare_example", record_prepare)
    with pytest.raises(RuntimeError, match="model unavailable"):
        await example["main"]()
    assert len(closed_connectors) == len(directories) == 1
    assert not directories[0].exists()


@pytest.mark.parametrize("order_id", [1002, 9999])
async def test_custom_agent_cannot_read_or_act_on_unowned_orders(
    order_id: int,
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
    closed_connectors: list[SQLConnector],
) -> None:
    steps, returns, _ = support_model
    steps.extend(
        [
            ("lookup_order", {"order_id": order_id}),
            ("open_support_ticket", {"order_id": order_id, "issue": "Delivery problem."}),
        ]
    )
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()

    lookup = returns[0].metadata
    assert isinstance(lookup, QueryExecution)
    assert lookup.parameter_values == {"order_id": order_id, "customer_id": 7}
    assert lookup.exec_result.df is not None and lookup.exec_result.df.empty
    assert returns[1].content == "(error: order not found for this customer)"
    assert len(queries) == 2
    printed = capsys.readouterr().out
    assert "Stored tickets: []" in printed
    assert "Ticket ID: None" in printed
    assert len(closed_connectors) == 1


async def test_ticket_action_checks_ownership_without_prior_lookup(
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
) -> None:
    steps, returns, _ = support_model
    steps.append(("open_support_ticket", {"order_id": 1002, "issue": "Delivery problem."}))
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()
    assert returns[0].content == "(error: order not found for this customer)"
    assert len(queries) == 1
    assert "Stored tickets: []" in capsys.readouterr().out


async def test_ticket_action_records_each_request_with_a_distinct_id(
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    steps, returns, _ = support_model
    steps.extend(
        [
            ("open_support_ticket", {"order_id": 1001, "issue": "Charging stopped."}),
            ("open_support_ticket", {"order_id": 1001, "issue": "Still not charging."}),
        ]
    )
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()
    assert returns[0].content == "SUP-1"
    assert returns[1].content == "SUP-2"
    printed = capsys.readouterr().out
    tickets = ast.literal_eval(printed.split("Stored tickets: ", 1)[1].splitlines()[0])
    assert tickets == [
        {"ticket_id": "SUP-1", "order_id": 1001, "issue": "Charging stopped."},
        {"ticket_id": "SUP-2", "order_id": 1001, "issue": "Still not charging."},
    ]


async def test_ticket_action_rejects_blank_issue(
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    capsys: pytest.CaptureFixture[str],
    queries: list[tuple[str, ExecResult]],
) -> None:
    steps, returns, _ = support_model
    steps.append(("open_support_ticket", {"order_id": 1001, "issue": "  "}))
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()
    assert returns[0].content == "(error: issue must not be empty)"
    assert not queries
    assert "Stored tickets: []" in capsys.readouterr().out


async def test_support_documents_are_scoped_to_the_support_directory(
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
) -> None:
    steps, returns, _ = support_model
    steps.append(("view", {"path": ".."}))
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()
    assert isinstance(returns[0].content, str)
    assert returns[0].content.startswith("(error:")
    assert "outside the allowed roots" in returns[0].content


async def test_support_tools_report_query_errors_without_creating_tickets(
    monkeypatch: pytest.MonkeyPatch,
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    capsys: pytest.CaptureFixture[str],
    closed_connectors: list[SQLConnector],
) -> None:
    async def fail_query(self: SQLConnector, query: str, **kwargs: Any) -> ExecResult:
        return ExecResult(error=ErrorInfo(exc_type="RuntimeError", message="orders unavailable"))

    monkeypatch.setattr(SQLConnector, "run_query_async", fail_query)
    steps, returns, _ = support_model
    steps.extend(
        [
            ("find_orders", {"product": "dock"}),
            ("lookup_order", {"order_id": 1001}),
            ("open_support_ticket", {"order_id": 1001, "issue": "Charging stopped."}),
        ]
    )
    await runpy.run_path(str(EXAMPLES / "custom_agents.py"))["main"]()
    for part in returns:
        assert isinstance(part.content, str)
        assert part.content.startswith("(error:") and "orders unavailable" in part.content
    assert "Stored tickets: []" in capsys.readouterr().out
    assert len(closed_connectors) == 1


@pytest.mark.parametrize("status", [200, 404])
async def test_remote_support_example_prepares_bundled_assets(
    status: int,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    support_model: tuple[list[tuple[str, dict[str, Any]]], list[ToolReturnPart], list[BinaryContent]],
    closed_connectors: list[SQLConnector],
) -> None:
    requested: list[str] = []
    original_client = httpx.AsyncClient

    def download(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        name = request.url.path.rsplit("/", 1)[1]
        return httpx.Response(status, content=(EXAMPLES / "support" / name).read_bytes())

    def make_client(**kwargs: Any) -> httpx.AsyncClient:
        return original_client(transport=httpx.MockTransport(download), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", make_client)
    example = runpy.run_path(str(EXAMPLES / "custom_agents.py"))
    monkeypatch.setitem(example["prepare_example"].__globals__, "__file__", str(tmp_path / "custom_agents.py"))
    steps, returns, media = support_model
    steps.extend(
        [
            ("view", {"path": "faq.txt"}),
            ("view", {"path": "dock-guide.pdf"}),
        ]
    )
    if status == 404:
        with pytest.raises(httpx.HTTPStatusError):
            await example["main"]()
        assert len(requested) == 1
        assert not returns
    else:
        await example["main"]()
        assert "Customer support FAQ" in str(returns[0].content)
        assert len(media) == 1 and media[0].media_type == "application/pdf"
        assert requested == [
            f"https://megagonlabs.github.io/tabulaflow/examples/support/{name}"
            for name in ("faq.txt", "dock-guide.pdf")
        ]
    assert len(closed_connectors) == 1
