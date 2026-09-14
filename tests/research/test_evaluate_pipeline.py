import datetime
from typing import ClassVar

from tabulaflow.research.pipelines.evaluate import evaluate_async
from tabulaflow.research.types import (
    GoldQuery,
    NL2QDataset,
    NL2QRunResult,
    SimpleNL2QTask,
    SimpleNL2QTaskOutput,
)


class _ScoreMetric:
    name: ClassVar[str] = "score"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    async def compute_async(self, task: object, db_connector: object = None) -> float:
        return 1.0


def _dataset() -> NL2QDataset:
    task = SimpleNL2QTask(
        qid="q1",
        db="db",
        question="Return one.",
        gold_query=GoldQuery(query="SELECT 1"),
    )
    return NL2QDataset(name="test", split="test", tasks=[task], db_connectors={})


def _result() -> NL2QRunResult:
    task = SimpleNL2QTaskOutput(
        qid="q1",
        db="db",
        question="Return one.",
        gold_query=GoldQuery(query="SELECT 1"),
        pred_query=None,
    )
    now = datetime.datetime(2026, 1, 1)
    return NL2QRunResult(
        start_time=now,
        end_time=now,
        dataset="test",
        split="test",
        databases=["db"],
        subsample_size=None,
        agent="test",
        agent_config={},
        tasks=[task],
    )


async def test_evaluate_defaults_to_simple_average_aggregation() -> None:
    result = await evaluate_async(_result(), _dataset(), [_ScoreMetric()], batch_size=1, verbose=False)

    assert result.tasks[0].eval_metrics == {"score": 1.0}
    assert result.aggregated_eval_metrics == {"score": {"avg": 1.0}}


async def test_evaluate_accepts_empty_aggregator_list() -> None:
    result = await evaluate_async(
        _result(),
        _dataset(),
        [_ScoreMetric()],
        batch_size=1,
        metric_aggregators=[],
        verbose=False,
    )

    assert result.tasks[0].eval_metrics == {"score": 1.0}
    assert result.aggregated_eval_metrics == {}
