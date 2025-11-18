from typing import Protocol, ClassVar, TypeAlias, Union, Any
from mintq.schema import (
    NL2QRunResult,
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
)
from mintq.registry import Registry


class BaseSimpleNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(self, task: SimpleNL2QTaskOutput) -> float | None | dict[str, float | None]: ...


class BaseSimpleAmbigNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(self, task: SimpleAmbigNL2QTaskOutput) -> float | None | dict[str, float | None]: ...


class BaseFlatAmbigNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(self, task: FlatAmbigNL2QTaskOutput) -> float | None | dict[str, float | None]: ...


class BaseStructuredAmbigNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(self, task: StructuredAmbigNL2QTaskOutput) -> float | None | dict[str, float | None]: ...


class BaseMetricAggregator(Protocol):
    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]: ...


NL2QMetric: TypeAlias = Union[
    BaseSimpleNL2QMetric,
    BaseSimpleAmbigNL2QMetric,
    BaseFlatAmbigNL2QMetric,
    BaseStructuredAmbigNL2QMetric,
]

metric_registry = Registry[NL2QMetric]("metric")
