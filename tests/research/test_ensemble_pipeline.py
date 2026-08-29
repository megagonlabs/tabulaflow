import datetime
from typing import Any, cast

import pytest
from pydantic import BaseModel

from tabulaflow.agents.trace import Usage
from tabulaflow.research.pipelines.ensemble import _validate_results, ensemble_async
from tabulaflow.research.types import (
    GoldQuery,
    NL2QDataset,
    NL2QRunResult,
    SimpleNL2QTask,
    SimpleNL2QTaskOutput,
)


def _output(qid: str) -> SimpleNL2QTaskOutput:
    return SimpleNL2QTaskOutput(
        qid=qid,
        db="db",
        question="Question",
        gold_query=GoldQuery(query="SELECT 1"),
        pred_query=None,
    )


def _result(qids: list[str], dataset: str = "test") -> NL2QRunResult:
    return NL2QRunResult(
        start_time=datetime.datetime(2026, 1, 1),
        end_time=datetime.datetime(2026, 1, 1),
        dataset=dataset,
        split="test",
        databases=["db"],
        subsample_size=None,
        agent="test",
        agent_config={},
        tasks=[_output(qid) for qid in qids],
    )


def test_ensemble_results_require_matching_unique_qids() -> None:
    reference = _result(["q1", "q2"])

    assert _validate_results([reference, _result(["q2", "q1"])]) is reference
    with pytest.raises(ValueError, match="At least one result"):
        _validate_results([])
    with pytest.raises(ValueError, match="duplicate QIDs"):
        _validate_results([_result(["q1", "q1"])])
    with pytest.raises(ValueError, match="same QIDs"):
        _validate_results([reference, _result(["q1"])])
    with pytest.raises(ValueError, match="same dataset and split"):
        _validate_results([reference, _result(["q1", "q2"], dataset="other")])
    with pytest.raises(ValueError, match="requires 'dbt' outputs"):
        _validate_results([reference], "dbt")


@pytest.mark.asyncio
async def test_ensemble_errors_fall_back_without_source_run_metadata() -> None:
    class Config(BaseModel):
        pass

    class FailingEnsembler:
        name = "failing"
        config = Config()

        async def ensemble_async(self, *_args: Any) -> SimpleNL2QTaskOutput:
            raise RuntimeError("failed")

    task = SimpleNL2QTask(
        qid="q1",
        db="db",
        question="Question",
        gold_query=GoldQuery(query="SELECT 1"),
    )
    dataset = NL2QDataset(name="test", split="test", tasks=[task], db_connectors={"db": object()})
    source = _result(["q1"])
    source.tasks[0].eval_metrics = {"score": 1.0}
    source.tasks[0].inference_metrics = {"latency_seconds": 1.0}
    source.tasks[0].usage = Usage.create(llm="test")

    result = await ensemble_async(cast(Any, FailingEnsembler()), [source], dataset, 1, verbose=False)

    assert result.aggregated_inference_metrics == {"fallback_count": 1}
    assert result.tasks[0] is not source.tasks[0]
    assert result.tasks[0].eval_metrics == {}
    assert result.tasks[0].inference_metrics == {}
    assert result.tasks[0].usage is None
    assert result.tasks[0].trajectory is None
