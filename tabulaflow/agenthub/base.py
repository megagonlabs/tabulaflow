from typing import Protocol, ClassVar, TypeAlias, Union
from pydantic import BaseModel
from tabulaflow.schema import (
    SimpleNL2QTask,
    AmbigNL2QTask,
    DbtTask,
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
    DbtTaskOutput,
    BaseUserSimulator,
    UserFreeTextQuestion,
    UserMultipleChoiceQuestion,
    UserValueQuestion,
    UserFreeTextAnswer,
    UserMultipleChoiceAnswer,
    UserValueAnswer,
    UserQuestion,
    UserAnswer,
)
from tabulaflow.db_connector import BaseSQLDBConnector, NL2QDBConnector
from tabulaflow.registry import Registry

__all__ = [
    "BaseAgentConfig",
    "BaseSimpleSQLAgent",
    "BaseAmbigSQLAgent",
    "BaseDbtAgent",
    "NL2QAgent",
    "agent_registry",
    "BaseUserSimulator",
    "UserFreeTextQuestion",
    "UserMultipleChoiceQuestion",
    "UserValueQuestion",
    "UserFreeTextAnswer",
    "UserMultipleChoiceAnswer",
    "UserValueAnswer",
    "UserQuestion",
    "UserAnswer",
]

BaseAgentConfig: TypeAlias = BaseModel


class BaseSimpleSQLAgent(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[BaseAgentConfig]]

    async def predict_async(self, task: SimpleNL2QTask, db_connector: NL2QDBConnector) -> SimpleNL2QTaskOutput: ...


class BaseAmbigSQLAgent(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[BaseAgentConfig]]

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput: ...


class BaseDbtAgent(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[BaseAgentConfig]]

    async def predict_async(self, task: DbtTask, db_connector: BaseSQLDBConnector) -> DbtTaskOutput: ...


NL2QAgent: TypeAlias = Union[BaseSimpleSQLAgent, BaseAmbigSQLAgent, BaseDbtAgent]


agent_registry = Registry[NL2QAgent]("agent")
