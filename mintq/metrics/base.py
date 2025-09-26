from typing import Protocol, ClassVar, TypeAlias, Union
from mintq.schema import (
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
)


class BaseSimpleNL2QMetric(Protocol):
    name: str

    async def compute_async(self, task: SimpleNL2QTaskOutput) -> float: ...


class BaseSimpleAmbigNL2QMetric(Protocol):
    name: ClassVar[str]

    async def compute_async(self, task: SimpleAmbigNL2QTaskOutput) -> float: ...


class BaseFlatAmbigNL2QMetric(Protocol):
    name: ClassVar[str]

    async def compute_async(self, task: FlatAmbigNL2QTaskOutput) -> float: ...


class BaseStructuredAmbigNL2QMetric(Protocol):
    name: ClassVar[str]

    async def compute_async(self, task: StructuredAmbigNL2QTaskOutput) -> float: ...


NL2QMetric: TypeAlias = Union[
    BaseSimpleNL2QMetric,
    BaseSimpleAmbigNL2QMetric,
    BaseFlatAmbigNL2QMetric,
    BaseStructuredAmbigNL2QMetric,
]
