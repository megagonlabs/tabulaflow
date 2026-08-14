from typing import Protocol, ClassVar, Any
from tabulaflow.core import NumericOrNull
from tabulaflow.research.types import NL2QRunResult, NL2QTaskOutput
from tabulaflow.data import DataConnector
from tabulaflow.core.registry import ClassRegistry


class BaseNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(
        self, task: NL2QTaskOutput, db_connector: DataConnector | None = None
    ) -> NumericOrNull | dict[str, NumericOrNull]: ...


class BaseMetricAggregator(Protocol):
    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]: ...


NL2QMetric = BaseNL2QMetric

metric_registry = ClassRegistry[NL2QMetric]("metric")
