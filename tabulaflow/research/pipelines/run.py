from pathlib import Path
from typing import Any

from pydantic import BaseModel

from tabulaflow.research.metrics.registry import MetricProtocol
from tabulaflow.research.pipelines.evaluate import evaluate_async
from tabulaflow.research.pipelines.execute import execute_async
from tabulaflow.research.pipelines.predict import predict_async
from tabulaflow.research.types import NL2QDataset, NL2QRunResult


async def run_experiment_async(
    agent_cls: type[Any],
    agent_config: BaseModel,
    dataset: NL2QDataset,
    metrics: list[MetricProtocol],
    *,
    batch_size: int,
    working_dir: str | Path = "output/test/",
) -> NL2QRunResult:
    """Predict, execute, and evaluate one experiment.

    The caller owns the dataset connectors and decides whether and where to
    persist the returned result.

    Args:
        agent_cls: Registered agent implementation.
        agent_config: Configuration passed to each agent instance.
        dataset: Loaded tasks and their database connectors.
        metrics: Task-level metrics to compute after query execution.
        batch_size: Maximum tasks processed concurrently.
        working_dir: Working directory used by project-based tasks.

    Returns:
        The predicted, executed, and evaluated run result.
    """
    result = await predict_async(
        agent_cls,
        agent_config,
        dataset,
        batch_size=batch_size,
        output_dir=str(working_dir),
    )
    await execute_async(result, dataset, batch_size=batch_size)
    await evaluate_async(result, dataset, metrics=metrics, batch_size=batch_size)
    return result
