from typing import Protocol, ClassVar, TypeAlias, Union
from pydantic import BaseModel
from tabulaflow.research.types import (
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
from tabulaflow.data import SQLConnectorProtocol, DBConnector
from tabulaflow.core.registry import ClassRegistry

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

    async def predict_async(self, task: SimpleNL2QTask, db_connector: DBConnector) -> SimpleNL2QTaskOutput: ...


class BaseAmbigSQLAgent(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[BaseAgentConfig]]

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: SQLConnectorProtocol, user_simulator: BaseUserSimulator
    ) -> SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput: ...


class BaseDbtAgent(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[BaseAgentConfig]]

    async def predict_async(self, task: DbtTask, db_connector: SQLConnectorProtocol) -> DbtTaskOutput: ...


NL2QAgent: TypeAlias = Union[BaseSimpleSQLAgent, BaseAmbigSQLAgent, BaseDbtAgent]


agent_registry = ClassRegistry[NL2QAgent]("agent")
