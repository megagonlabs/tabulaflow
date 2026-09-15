"""Exercise the downloadable quick start without paid model requests."""

from collections.abc import AsyncIterator
import json
from pathlib import Path
import runpy
from typing import Any

from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
import pytest

from tabulaflow.agents import ChatSession
from tabulaflow.agents.llm import make_agent
from tabulaflow.data import SQLConnector
from tabulaflow.output.resolver import OutputResolver, ResolvedChartArtifact, ResolvedTableArtifact


@pytest.mark.parametrize("reverse_artifacts", [False, True])
async def test_quick_start(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], reverse_artifacts: bool
) -> None:
    script = Path(__file__).resolve().parents[1] / "docs/examples/quick_start.py"
    example = runpy.run_path(str(script))
    chart_spec = {
        "mark": "bar",
        "encoding": {"x": {"field": "region", "type": "nominal"}, "y": {"field": "revenue", "type": "quantitative"}},
    }
    steps = [
        (
            "run_query",
            {
                "connector_alias": "sales",
                "query": "SELECT region, SUM(revenue_usd) AS revenue FROM sales GROUP BY region",
            },
        ),
        (
            "run_query",
            {
                "connector_alias": "support",
                "query": "SELECT * FROM support WHERE priority = 'high' AND status = 'open' ORDER BY ticket_id",
            },
        ),
        ("render_chart", {"source_id": "S1", "vegalite_spec": json.dumps(chart_spec)}),
        (
            "show_artifacts",
            {
                "artifacts": [
                    {"id": "CHART1", "label": "Revenue by region"},
                    {"id": "S2", "label": "Open high-priority tickets"},
                ]
            },
        ),
    ]

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str | dict[int, DeltaToolCall]]:
        returns = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]
        for part in returns:
            assert isinstance(part.content, str)
            assert "(error:" not in part.content
        if len(returns) == len(steps):
            yield "ANSWER:\nWest: $2,000. East: $1,500. Two high-priority tickets remain open."
        else:
            name, arguments = steps[len(returns)]
            yield {0: DeltaToolCall(name=name, json_args=json.dumps(arguments))}

    def make_test_agent(model: Any, **kwargs: Any) -> Any:
        return make_agent(FunctionModel(stream_function=respond), **kwargs)

    original_run = ChatSession.run

    async def verify_run(self: ChatSession, question: str) -> Any:
        assert set(self._registry.list_aliases()) == {"sales", "support"}
        assert self._registry.get("sales").global_id != self._registry.get("support").global_id
        assert self._workspace is None
        result = await original_run(self, question)
        resolved = await OutputResolver(self.output_store).resolve(result.output)
        chart, table = resolved.artifacts
        assert isinstance(chart, ResolvedChartArtifact)
        assert isinstance(table, ResolvedTableArtifact)
        assert chart.result.metadata.connector_alias == "sales"
        assert table.result.metadata.connector_alias == "support"
        assert chart.result.df is not None
        assert table.result.df is not None
        assert dict(zip(chart.result.df["region"], chart.result.df["revenue"])) == {"West": 2000, "East": 1500}
        assert table.result.df["ticket_id"].tolist() == [201, 202]
        assert chart.spec["mark"] == "bar"
        if reverse_artifacts:
            result.output.artifacts.reverse()
        return result

    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("TABULAFLOW_SCHEMA_CACHE_MODE", "off")
    monkeypatch.setenv("TABULAFLOW_SQL_QUERY_CACHE_MODE", "off")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    monkeypatch.setattr("tabulaflow.agents.chat.session.make_agent", make_test_agent)
    monkeypatch.setattr("tabulaflow.agents.trace.compute_api_cost", lambda *args, **kwargs: 0)
    monkeypatch.setattr(ChatSession, "run", verify_run)

    await example["main"]()

    output = capsys.readouterr().out
    for expected in (
        "Answer:",
        "Artifact: Revenue by region",
        "Artifact: Open high-priority tickets",
        "Source: sales",
        "Source: support",
        "SQL: SELECT region, SUM(revenue_usd) AS revenue FROM sales GROUP BY region",
        "SQL: SELECT * FROM support WHERE priority = 'high' AND status = 'open' ORDER BY ticket_id",
        "2000",
        "1500",
        "201",
        "202",
    ):
        assert expected in output
    assert output.count("DataFrame:\n") == 2
    printed_spec, _ = json.JSONDecoder().raw_decode(output.split("Vega-Lite: ", 1)[1])
    assert printed_spec == chart_spec
    assert (output.index("Source: support") < output.index("Source: sales")) == reverse_artifacts


@pytest.mark.parametrize("failure", ["connection", "preparation", "model"])
async def test_quick_start_closes_resources_on_failure(failure: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("TABULAFLOW_SCHEMA_CACHE_MODE", "off")
    monkeypatch.setenv("TABULAFLOW_SQL_QUERY_CACHE_MODE", "off")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    script = Path(__file__).resolve().parents[1] / "docs/examples/quick_start.py"
    example = runpy.run_path(str(script))
    connectors: list[SQLConnector] = []
    closed: list[SQLConnector] = []
    closed_sessions: list[ChatSession] = []
    original_open = SQLConnector.from_url_async
    original_close = SQLConnector.close_async
    original_session_close = ChatSession.aclose

    async def open_connector(cls: type[SQLConnector], *args: Any, **kwargs: Any) -> SQLConnector:
        if failure == "connection" and connectors:
            raise RuntimeError("example failure")
        connector = await original_open(*args, **kwargs)
        connectors.append(connector)
        return connector

    async def close_connector(self: SQLConnector) -> None:
        await original_close(self)
        closed.append(self)

    async def close_session(self: ChatSession) -> None:
        await original_session_close(self)
        closed_sessions.append(self)

    async def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("example failure")

    monkeypatch.setattr(SQLConnector, "from_url_async", classmethod(open_connector))
    monkeypatch.setattr(SQLConnector, "close_async", close_connector)
    monkeypatch.setattr(ChatSession, "aclose", close_session)
    if failure == "preparation":
        monkeypatch.setitem(example["main"].__globals__, "load_sample_data", fail)
    elif failure == "model":
        monkeypatch.setattr(ChatSession, "run", fail)

    with pytest.raises(RuntimeError, match="example failure"):
        await example["main"]()
    assert closed == list(reversed(connectors))
    assert len(closed) == (1 if failure == "connection" else 2)
    assert len(closed_sessions) == (1 if failure == "model" else 0)
