"""Exercise the custom research method with real execution and offline models."""

from pathlib import Path
import runpy
from typing import Any

import pandas as pd
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.usage import RequestUsage
import pytest

from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.trace import Usage
from tabulaflow.data import SQLConnector
from tabulaflow.research.types import GoldQuery, NL2QDataset, NL2QRunResult, SimpleNL2QTask, SimpleNL2QTaskOutput


@pytest.mark.parametrize("failure", [None, "table_linking", "sql_generation", "unknown_table"])
async def test_table_linking_agent(failure: str | None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("TABULAFLOW_SCHEMA_CACHE_MODE", "off")
    monkeypatch.setenv("TABULAFLOW_SQL_QUERY_CACHE_MODE", "off")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    monkeypatch.setattr("tabulaflow.agents.trace.compute_api_cost", lambda *args, **kwargs: 0)
    monkeypatch.chdir(tmp_path)
    connector = await SQLConnector.from_url_async("sqlite+aiosqlite:///:memory:", read_only=False)
    closed: list[SQLConnector] = []
    original_close = SQLConnector.close_async

    async def record_close(self: SQLConnector) -> None:
        await original_close(self)
        closed.append(self)

    monkeypatch.setattr(SQLConnector, "close_async", record_close)
    questions = {
        "How many orders are there?": "SELECT COUNT(*) FROM orders",
        "What is the total amount?": "SELECT SUM(amount) FROM orders",
        "What is the largest amount?": "SELECT MAX(amount) FROM orders",
    }
    calls: list[tuple[str, str]] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompts = [part.content for message in messages for part in message.parts if isinstance(part, UserPromptPart)]
        prompt = str(prompts)
        assert "reference-only" not in prompt
        assert "reference-only" not in (info.instructions or "")
        assert "orders" in (info.instructions or "")
        question = next(question for question in questions if question in prompt)
        linking = "tables" in info.output_tools[0].parameters_json_schema["properties"]
        stage = "table_linking" if linking else "sql_generation"
        calls.append((stage, question))
        assert ("unrelated_notes" in (info.instructions or "")) == linking
        assert "unrelated_notes" not in prompt
        if failure == stage and question == "What is the total amount?":
            raise RuntimeError("offline model failure")
        output: dict[str, Any]
        if linking:
            table = (
                "missing_table" if failure == "unknown_table" and question == "What is the total amount?" else "orders"
            )
            output = {"tables": [{"schema_name": None, "table_name": table}]}
        else:
            output = {"query": questions[question]}
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, output)],
            usage=RequestUsage(input_tokens=10, output_tokens=5),
        )

    def make_test_agent(model: Any, **kwargs: Any) -> Any:
        return make_agent(FunctionModel(function=respond), **kwargs)

    try:
        await connector.write_dataframe_async(pd.DataFrame({"amount": [10, 20]}), "orders")
        await connector.write_dataframe_async(pd.DataFrame({"note": ["not needed"]}), "unrelated_notes")
        original_schema = connector.schema.model_dump_json()
        dataset = NL2QDataset(
            name="bird-sql",
            split="dev",
            tasks=[
                SimpleNL2QTask(
                    qid=str(index),
                    db="california_schools",
                    question=question,
                    gold_query=GoldQuery(query=f"{query} -- reference-only"),
                    extra_info={"reference-only": query},
                )
                for index, (question, query) in enumerate(questions.items())
            ],
            db_connectors={"california_schools": connector},
        )

        class LocalLoader:
            async def get_split_async(self, split: str, **kwargs: Any) -> NL2QDataset:
                assert split == "dev"
                assert kwargs == {"databases": ["california_schools"], "subsample_size": 3}
                return dataset

        monkeypatch.setattr("tabulaflow.research.benchmarks.BirdSQLDatasetLoader", LocalLoader)
        monkeypatch.setattr("tabulaflow.agents.llm.make_agent", make_test_agent)
        script = Path(__file__).resolve().parents[1] / "docs/examples/table_linking_agent.py"
        await runpy.run_path(str(script))["main"]()
        assert closed == [connector]
        assert connector.schema.model_dump_json() == original_schema

        run_dir = tmp_path / "runs" / "table_linking"
        result = NL2QRunResult.model_validate_json((run_dir / "result.json").read_text())
        assert result.agent == "table_linking"
        assert [task.qid for task in result.tasks] == ["0", "1", "2"]
        expected_accuracy = round(2 / 3, 4) if failure else 1.0
        assert result.aggregated_eval_metrics["bird_sql_ex"]["avg"] == expected_accuracy
        assert (run_dir / "result_summary.csv").is_file()
        for task in result.tasks:
            assert isinstance(task, SimpleNL2QTaskOutput)
            assert (run_dir / "readable" / task.qid / "task_readable.md").is_file()
            stages = [stage for stage, question in calls if question == task.question]
            if failure and task.qid == "1":
                assert task.pred_query is None
                assert stages == (
                    ["table_linking", "sql_generation"] if failure == "sql_generation" else ["table_linking"]
                )
                continue
            assert task.pred_query is not None and task.pred_query.exec_result is not None
            assert task.pred_query.exec_result.error is None
            assert task.usage is not None and task.trajectory is not None
            assert stages == ["table_linking", "sql_generation"]
            assert task.usage.api_requests == 2
            assert task.usage.input_tokens == 20
            assert task.usage.output_tokens == 10
            assert isinstance(task.trajectory, list)
            assert [trajectory.id for trajectory in task.trajectory] == ["TRJY-TABLE-LINKING", "TRJY-SQL-GENERATION"]
            for trajectory in task.trajectory:
                assert (run_dir / "readable" / task.qid / "trajectory" / f"{trajectory.id}.md").is_file()

    finally:
        if connector not in closed:
            await connector.close_async()


def test_research_run_summary() -> None:
    script = Path(__file__).resolve().parents[1] / "docs/examples/compare_research_agents.py"
    comparison = runpy.run_path(str(script))
    tracked = NL2QRunResult.model_construct(
        agent="example",
        aggregated_eval_metrics={"bird_sql_ex": {"avg": 0.8}, "executable": {"avg": 1.0}},
        total_usage=Usage.create(input_tokens=20, output_tokens=10, api_cost_usd=0.01),
        aggregated_inference_metrics={"latency_seconds": {"avg": 0.5}},
    )
    untracked = tracked.model_copy(update={"total_usage": None, "aggregated_inference_metrics": {}})
    summary = comparison["summarize_runs"]([tracked, untracked])
    assert summary["Accuracy"].tolist() == [0.8, 0.8]
    assert summary["Executable"].tolist() == [1.0, 1.0]
    assert summary.loc[0, "Tokens"] == 30
    assert summary.loc[0, "Avg. latency (s)"] == 0.5
    assert pd.isna(summary.loc[1, "Tokens"])
    assert pd.isna(summary.loc[1, "Cost (USD)"])
    assert pd.isna(summary.loc[1, "Avg. latency (s)"])
