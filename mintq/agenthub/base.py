from typing import Protocol, ClassVar, Type, TypeAlias, Union, Any, Literal
import datetime
from pydantic import BaseModel, Annotated, Field
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

BaseAgentConfig: TypeAlias = BaseModel


class BaseSimpleSQLAgent(Protocol):
    name: ClassVar[str]
    config_cls: ClassVar[Type[BaseAgentConfig]]

    @classmethod
    async def from_config_async(cls, config) -> "BaseSimpleSQLAgent": ...  # type: ignore

    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector) -> SimpleNL2QTaskOutput: ...


class UserFreeTextQuestion(BaseModel):
    type: Literal["free_text"] = "free_text"
    question: str


class UserMultipleChoiceQuestion(BaseModel):
    type: Literal["multiple_choice"] = "multiple_choice"
    question: str
    options: list[str]


class UserValueQuestion(BaseModel):
    type: Literal["value"] = "value"
    question: str
    value_dtype: Literal["int", "float", "date", "bool", "str"]
    value_operator_options: list[Literal["<", ">", "<=", ">=", "==", "!="]]


class UserFreeTextAnswer(BaseModel):
    type: Literal["free_text"] = "free_text"
    answer_text: str


class UserMultipleChoiceAnswer(BaseModel):
    type: Literal["multiple_choice"] = "multiple_choice"
    answer_index: int


class UserValueAnswer(BaseModel):
    type: Literal["value"] = "value"
    operator: Literal["<", ">", "<=", ">=", "==", "!="]
    value: int | float | datetime.date | bool | str


UserQuestion: TypeAlias = Annotated[
    Union[UserFreeTextQuestion, UserMultipleChoiceQuestion, UserValueQuestion], Field(discriminator="type")
]
UserAnswer: TypeAlias = Annotated[
    Union[UserFreeTextAnswer, UserMultipleChoiceAnswer, UserValueAnswer], Field(discriminator="type")
]


class BaseUserSimulator(Protocol):
    async def ask_async(self, questions: list[UserQuestion]) -> list[UserAnswer]: ...


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
