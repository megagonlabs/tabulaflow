from typing import Protocol, ClassVar, Any, Type, TypeAlias, Union, TypeVar, Generic
from mintq.schema import (
    SimpleNL2QTask,
    AmbigNL2QTask,
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
)
from mintq.db_connector import BaseAsyncDBConnector, BaseAsyncSQLDBConnector


class BaseUserSimulator(Protocol):
    async def ask_async(self, question: str) -> str: ...


class BaseAgentConfig(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


class BaseSimpleSQLAgent(Protocol):
    name: ClassVar[str]
    config_cls: ClassVar[Type[BaseAgentConfig]]

    @classmethod
    async def from_config_async(cls, config) -> "BaseSimpleSQLAgent": ...  # type: ignore

    async def predict_async(
        self, task: SimpleNL2QTask, db_connector: BaseAsyncSQLDBConnector
    ) -> SimpleNL2QTaskOutput: ...


class BaseAmbigSQLAgent(Protocol):
    name: ClassVar[str]
    config_cls: ClassVar[Type[BaseAgentConfig]]

    @classmethod
    async def from_config_async(cls, config) -> "BaseAmbigSQLAgent": ...  # type: ignore

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseAsyncSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput: ...


NL2QAgent: TypeAlias = Union[BaseSimpleSQLAgent, BaseAmbigSQLAgent]
