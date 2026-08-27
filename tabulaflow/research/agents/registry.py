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
    UserSimulatorProtocol,
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
    "AgentConfig",
    "SimpleSQLAgentProtocol",
    "AmbigSQLAgentProtocol",
    "DbtAgentProtocol",
    "NL2QAgent",
    "agent_registry",
    "UserSimulatorProtocol",
    "UserFreeTextQuestion",
    "UserMultipleChoiceQuestion",
    "UserValueQuestion",
    "UserFreeTextAnswer",
    "UserMultipleChoiceAnswer",
    "UserValueAnswer",
    "UserQuestion",
    "UserAnswer",
]

AgentConfig: TypeAlias = BaseModel


class SimpleSQLAgentProtocol(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[AgentConfig]]

    async def predict_async(self, task: SimpleNL2QTask, db_connector: DBConnector) -> SimpleNL2QTaskOutput: ...


class AmbigSQLAgentProtocol(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[AgentConfig]]

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: SQLConnectorProtocol, user_simulator: UserSimulatorProtocol
    ) -> SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput: ...


class DbtAgentProtocol(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[AgentConfig]]

    async def predict_async(self, task: DbtTask, db_connector: SQLConnectorProtocol) -> DbtTaskOutput: ...


NL2QAgent: TypeAlias = Union[SimpleSQLAgentProtocol, AmbigSQLAgentProtocol, DbtAgentProtocol]


agent_registry = ClassRegistry[NL2QAgent]("agent")
