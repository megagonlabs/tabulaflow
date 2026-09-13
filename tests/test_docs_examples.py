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
from tabulaflow.output.resolver import OutputResolver, ResolvedChartArtifact, ResolvedTableArtifact


async def test_quick_start(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
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
            assert "(error:" not in str(part.content)
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
        "Table: sales",
        "Columns: ['order_id', 'region', 'revenue_usd']",
        "Answer:",
        "Data sources:",
        "Artifact count: 2",
        "Artifact type: chart",
        "Artifact type: table",
    ):
        assert expected in output
