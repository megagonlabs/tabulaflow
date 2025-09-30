from typing import Protocol, ClassVar, Type, TypeAlias, Union
from pydantic import BaseModel
from mintq.schema import (
    SimpleNL2QTask,
    AmbigNL2QTask,
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
)
from mintq.db_connector import BaseSQLDBConnector
from mintq.registry import Registry


class UserQuestion(BaseModel):
    question: str
    options: list[str] | None = None


class UserAnswer(BaseModel):
    answer_text: str | None = None
    answer_index: int | None = None


class BaseUserSimulator(Protocol):
    async def ask_async(self, questions: list[UserQuestion]) -> list[UserAnswer]: ...


BaseAgentConfig: TypeAlias = BaseModel


class BaseSimpleSQLAgent(Protocol):
    name: ClassVar[str]
    config_cls: ClassVar[Type[BaseAgentConfig]]

    @classmethod
    async def from_config_async(cls, config) -> "BaseSimpleSQLAgent": ...  # type: ignore

    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector) -> SimpleNL2QTaskOutput: ...


class BaseAmbigSQLAgent(Protocol):
    name: ClassVar[str]
    config_cls: ClassVar[Type[BaseAgentConfig]]

    @classmethod
    async def from_config_async(cls, config) -> "BaseAmbigSQLAgent": ...  # type: ignore

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput: ...


NL2QAgent: TypeAlias = Union[BaseSimpleSQLAgent, BaseAmbigSQLAgent]


agent_registry = Registry[NL2QAgent]("agent")
