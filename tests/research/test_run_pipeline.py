import inspect
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

from tabulaflow.research.agents.user_simulator import (
    DEFAULT_USER_SIMULATOR_LLM,
    UserSimulator,
    UserSimulatorConfig,
)
from tabulaflow.research.metrics.registry import MetricProtocol
from tabulaflow.research.pipelines import predict as predict_pipeline
from tabulaflow.research.pipelines import run as run_pipeline
from tabulaflow.research.types import (
    AmbigNL2QTask,
    GoldQuery,
    NL2QDataset,
    NL2QRunResult,
    StructuredAmbigNL2QTaskOutput,
)


class _AgentConfig(BaseModel):
    pass


def test_user_simulator_has_stable_paper_default() -> None:
    config = UserSimulatorConfig(task="Question", ambig_points=[])
    factory_default = inspect.signature(UserSimulator.from_ambig_nl2q_task).parameters["llm"].default

    assert config.llm == DEFAULT_USER_SIMULATOR_LLM
    assert factory_default == DEFAULT_USER_SIMULATOR_LLM


@pytest.mark.asyncio
async def test_run_experiment_composes_pipeline_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    result = cast(NL2QRunResult, SimpleNamespace())
    predict = AsyncMock(return_value=result)
    execute = AsyncMock(return_value=result)
    evaluate = AsyncMock(return_value=result)
    monkeypatch.setattr(run_pipeline, "predict_async", predict)
    monkeypatch.setattr(run_pipeline, "execute_async", execute)
    monkeypatch.setattr(run_pipeline, "evaluate_async", evaluate)

    agent_cls = type("Agent", (), {})
    agent_config = _AgentConfig()
    dataset = cast(NL2QDataset, SimpleNamespace())
    metrics = cast(list[MetricProtocol], [SimpleNamespace()])

    returned = await run_pipeline.run_experiment_async(
        agent_cls,
        agent_config,
        dataset,
        metrics,
        batch_size=3,
        user_simulator_llm="anthropic:simulator",
    )

    assert returned is result
    predict.assert_awaited_once_with(
        agent_cls,
        agent_config,
        dataset,
        batch_size=3,
        user_simulator_llm="anthropic:simulator",
    )
    execute.assert_awaited_once_with(result, dataset, batch_size=3)
    evaluate.assert_awaited_once_with(result, dataset, metrics=metrics, batch_size=3)


@pytest.mark.asyncio
async def test_predict_uses_user_simulator_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    task = AmbigNL2QTask(
        qid="q1",
        has_intended_resolution=False,
        db="db",
        question="Question",
        gold_ambiguity_points=[],
        gold_queries=[GoldQuery(query="SELECT 1")],
        gold_intended_query_id=None,
    )
    dataset = NL2QDataset(
        name="arcs",
        split="test",
        databases=["db"],
        tasks=[task],
        db_connectors={"db": object()},
    )
    simulator = object()
    factory = Mock(return_value=simulator)
    monkeypatch.setattr(predict_pipeline.UserSimulator, "from_ambig_nl2q_task", factory)

    class Agent:
        name = "ambig_structured_sql_agent"
        task_type = "ambig"
        output_type = "ambig-structured"

        @classmethod
        async def from_config_async(cls, config: _AgentConfig) -> "Agent":
            return cls()

        async def predict_async(
            self, selected_task: AmbigNL2QTask, connector: object, user_simulator: object
        ) -> StructuredAmbigNL2QTaskOutput:
            assert user_simulator is simulator
            return StructuredAmbigNL2QTaskOutput(
                **selected_task.model_dump(),
                pred_ambiguity_points=[],
                pred_queries=[],
                pred_intended_query_id=None,
            )

    await predict_pipeline.predict_async(
        Agent,
        _AgentConfig(),
        dataset,
        verbose=False,
        user_simulator_llm="anthropic:simulator",
    )

    factory.assert_called_once_with(
        task,
        include_history=False,
        answer_with_multiple_ambig_points=False,
        llm="anthropic:simulator",
    )
