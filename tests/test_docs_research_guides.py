"""Exercise the custom research method with real execution and offline models."""

from pathlib import Path
import runpy
from typing import Any

import pandas as pd
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from tabulaflow.agents.llm import make_agent
from tabulaflow.data import SQLConnector
from tabulaflow.research.types import GoldQuery, NL2QDataset, NL2QRunResult, SimpleNL2QTask, SimpleNL2QTaskOutput


@pytest.mark.parametrize("fail_prediction", [False, True])
async def test_custom_research_agent_comparison(
    fail_prediction: bool, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompts = [part.content for message in messages for part in message.parts if isinstance(part, UserPromptPart)]
        prompt = str(prompts)
        assert "reference-only" not in prompt
        assert "reference-only" not in (info.instructions or "")
        assert "orders" in (info.instructions or "")
        question = next(question for question in questions if question in prompt)
        if info.output_tools:
            if fail_prediction and question == "What is the total amount?":
                raise RuntimeError("offline model failure")
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"query": questions[question]})])
        return ModelResponse(parts=[TextPart(questions[question])])

    def make_test_agent(model: Any, **kwargs: Any) -> Any:
        return make_agent(FunctionModel(function=respond), **kwargs)

    try:
        await connector.write_dataframe_async(pd.DataFrame({"amount": [10, 20]}), "orders")
        await connector.refresh_schema_async()
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
        monkeypatch.setattr("tabulaflow.research.agents.direct_prompt.make_agent", make_test_agent)
        script = Path(__file__).resolve().parents[1] / "docs/examples/custom_research_agent.py"
        await runpy.run_path(str(script))["main"]()
        assert closed == [connector]

        for name in ("direct_prompting", "structured_query"):
            run_dir = tmp_path / "runs" / name
            result = NL2QRunResult.model_validate_json((run_dir / "result.json").read_text())
            assert result.agent == name
            assert [task.qid for task in result.tasks] == ["0", "1", "2"]
            expected_accuracy = round(2 / 3, 4) if fail_prediction and name == "structured_query" else 1.0
            assert result.aggregated_eval_metrics["bird_sql_ex"]["avg"] == expected_accuracy
            assert (run_dir / "result_summary.csv").is_file()
            for task in result.tasks:
                assert isinstance(task, SimpleNL2QTaskOutput)
                assert (run_dir / "readable" / task.qid / "task_readable.md").is_file()
                if fail_prediction and name == "structured_query" and task.qid == "1":
                    assert task.pred_query is None
                    continue
                assert task.pred_query is not None and task.pred_query.exec_result is not None
                assert task.pred_query.exec_result.error is None
                assert task.usage is not None and task.trajectory is not None
                assert task.inference_metrics["latency_seconds"] >= 0
    finally:
        if connector not in closed:
            await connector.close_async()
