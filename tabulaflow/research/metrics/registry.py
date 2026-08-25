from typing import Protocol, ClassVar, Any
from tabulaflow.research.types import NL2QRunResult, NL2QTaskOutput, NumericOrNull
from tabulaflow.data import DBConnector
from tabulaflow.core.registry import ClassRegistry


class NL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(
        self, task: NL2QTaskOutput, db_connector: DBConnector | None = None
    ) -> NumericOrNull | dict[str, NumericOrNull]: ...


class MetricAggregator(Protocol):
    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]: ...


metric_registry = ClassRegistry[NL2QMetric]("metric")
