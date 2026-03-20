from typing import Protocol, ClassVar, TypeAlias, Union, Any
from mintq.schema import (
    NL2QRunResult,
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
    DbtTaskOutput,
    NumericOrNull,
)
from mintq.db_connector import NL2QDBConnector
from mintq.registry import Registry


class BaseSimpleNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(
        self, task: SimpleNL2QTaskOutput, db_connector: NL2QDBConnector
    ) -> NumericOrNull | dict[str, NumericOrNull]: ...


class BaseSimpleAmbigNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(
        self, task: SimpleAmbigNL2QTaskOutput, db_connector: NL2QDBConnector
    ) -> NumericOrNull | dict[str, NumericOrNull]: ...


class BaseFlatAmbigNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(
        self, task: FlatAmbigNL2QTaskOutput, db_connector: NL2QDBConnector
    ) -> NumericOrNull | dict[str, NumericOrNull]: ...


class BaseStructuredAmbigNL2QMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(
        self, task: StructuredAmbigNL2QTaskOutput, db_connector: NL2QDBConnector
    ) -> NumericOrNull | dict[str, NumericOrNull]: ...


class BaseDbtMetric(Protocol):
    name: ClassVar[str]
    compatible_output_types: ClassVar[list[str]]

    async def compute_async(
        self, task: DbtTaskOutput
    ) -> NumericOrNull | dict[str, NumericOrNull]: ...


class BaseMetricAggregator(Protocol):
    def aggregate(self, result: NL2QRunResult) -> dict[str, Any]: ...


NL2QMetric: TypeAlias = Union[
    BaseSimpleNL2QMetric,
    BaseSimpleAmbigNL2QMetric,
    BaseFlatAmbigNL2QMetric,
    BaseStructuredAmbigNL2QMetric,
    BaseDbtMetric,
]

metric_registry = Registry[NL2QMetric]("metric")
