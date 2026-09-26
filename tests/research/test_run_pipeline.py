from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from tabulaflow.research.metrics.registry import MetricProtocol
from tabulaflow.research.pipelines import run as run_pipeline
from tabulaflow.research.types import NL2QDataset, NL2QRunResult


class _AgentConfig(BaseModel):
    pass


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
    )

    assert returned is result
    predict.assert_awaited_once_with(
        agent_cls,
        agent_config,
        dataset,
        batch_size=3,
    )
    execute.assert_awaited_once_with(result, dataset, batch_size=3)
    evaluate.assert_awaited_once_with(result, dataset, metrics=metrics, batch_size=3)
