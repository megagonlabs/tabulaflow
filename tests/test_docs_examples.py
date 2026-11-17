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


@pytest.mark.parametrize("reverse_artifacts", [False, True])
async def test_quick_start(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], reverse_artifacts: bool
) -> None:
    script = Path(__file__).resolve().parents[1] / "tabulaflow/examples/quick_start.py"
    example = runpy.run_path(str(script))
    chart_spec = {
        "mark": "bar",
        "encoding": {
            "x": {"field": "customer_id", "type": "nominal"},
            "y": {"field": "total_revenue_usd", "type": "quantitative"},
        },
    }
    join_query = (
        "SELECT r.customer_id, r.total_revenue_usd, "
        "COALESCE(t.open_high_priority_tickets, 0) AS open_high_priority_tickets "
        "FROM customer_revenue r LEFT JOIN open_high_priority_tickets t USING (customer_id) "
        "ORDER BY r.customer_id"
    )
    steps = [
        (
            "run_query",
            {
                "connector_alias": "sales",
                "query": ("SELECT customer_id, SUM(revenue_usd) AS total_revenue_usd FROM sales GROUP BY customer_id"),
            },
        ),
        (
            "run_query",
            {
                "connector_alias": "support",
                "query": (
                    "SELECT customer_id, COUNT(*) AS open_high_priority_tickets FROM support "
                    "WHERE priority = 'high' AND status = 'open' GROUP BY customer_id"
                ),
            },
        ),
        (
            "write_result_table",
            {
                "source_id": "S1",
                "target_alias": "workspace",
                "target_schema": None,
                "target_table": "customer_revenue",
            },
        ),
        (
            "write_result_table",
            {
                "source_id": "S2",
                "target_alias": "workspace",
                "target_schema": None,
                "target_table": "open_high_priority_tickets",
            },
        ),
        ("run_query", {"connector_alias": "workspace", "query": join_query}),
        ("render_chart", {"source_id": "S3", "vegalite_spec": json.dumps(chart_spec)}),
        (
            "show_artifacts",
            {
                "artifacts": [
                    {"id": "CHART1", "label": "Revenue by customer"},
                    {"id": "S3", "label": "Customer revenue and support"},
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
            yield "ANSWER:\nCustomer 101 has $2,000 revenue and one open high-priority ticket."
        else:
            name, arguments = steps[len(returns)]
            yield {0: DeltaToolCall(name=name, json_args=json.dumps(arguments))}

    def make_test_agent(model: Any, **kwargs: Any) -> Any:
        return make_agent(FunctionModel(stream_function=respond), **kwargs)

    original_run = ChatSession.run

    async def verify_run(self: ChatSession, question: str) -> Any:
        assert set(self._registry.list_aliases()) == {"sales", "support", "workspace"}
        assert self._registry.get("sales").global_id != self._registry.get("support").global_id
        assert self._workspace is self._registry.get("workspace")
        result = await original_run(self, question)
        resolved = await OutputResolver(self.output_store).resolve(result.output)
        chart, table = resolved.artifacts
        assert isinstance(chart, ResolvedChartArtifact)
        assert isinstance(table, ResolvedTableArtifact)
        assert chart.result.metadata.connector_alias == "workspace"
        assert table.result.metadata.connector_alias == "workspace"
        assert chart.result.df is not None
        assert table.result.df is not None
        assert dict(zip(chart.result.df["customer_id"], chart.result.df["total_revenue_usd"])) == {
            101: 2000,
            102: 900,
            103: 600,
        }
        assert dict(zip(table.result.df["customer_id"], table.result.df["open_high_priority_tickets"])) == {
            101: 1,
            102: 1,
            103: 0,
        }
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
        "Artifact: Revenue by customer",
        "Artifact: Customer revenue and support",
        "Source: workspace",
        join_query,
        "2000",
        "900",
        "600",
        "open_high_priority_tickets",
        "Vega-Lite spec:",
        '"mark": "bar"',
    ):
        assert expected in output
    assert output.count("DataFrame:\n") == 2
    assert output.count("-" * 72) == 2
    assert (
        output.index("Artifact: Customer revenue and support") < output.index("Artifact: Revenue by customer")
    ) == reverse_artifacts
