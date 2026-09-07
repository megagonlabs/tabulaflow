"""Extension contracts and registry for research metrics."""

from typing import Protocol, ClassVar, Any
from tabulaflow.research.types import NL2QRunResult, NL2QTaskOutput, NumericOrNull
from tabulaflow.data import DataConnector
from tabulaflow.core.registry import ClassRegistry


class MetricProtocol(Protocol):
    """Task-level evaluation metric registered by name."""

    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(
        self, task: NL2QTaskOutput, db_connector: DataConnector | None = None
    ) -> NumericOrNull | dict[str, NumericOrNull]: ...


class MetricAggregatorProtocol(Protocol):
    """Aggregation policy over the task outputs in one run."""

    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]: ...


metric_registry = ClassRegistry[MetricProtocol]("metric")

__all__ = ["MetricAggregatorProtocol", "MetricProtocol", "metric_registry"]
