from typing import Protocol, ClassVar, Any
from tabulaflow.schema import (
    NL2QRunResult,
    NL2QTaskOutput,
    NumericOrNull,
)
from tabulaflow.core.db_connector import NL2QDBConnector
from tabulaflow.core.registry import Registry


class BaseNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(
        self, task: NL2QTaskOutput, db_connector: NL2QDBConnector | None = None
    ) -> NumericOrNull | dict[str, NumericOrNull]: ...


class BaseMetricAggregator(Protocol):
    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]: ...


NL2QMetric = BaseNL2QMetric

metric_registry = Registry[NL2QMetric]("metric")
