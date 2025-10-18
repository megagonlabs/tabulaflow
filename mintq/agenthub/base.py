from typing import Protocol, ClassVar, Type, TypeAlias, Union, Literal, Annotated, overload
from pydantic import BaseModel, Field
from mintq.schema import (
    SimpleNL2QTask,
    AmbigNL2QTask,
    SimpleNL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
    Usage,
    Trajectory,
)
from mintq.db_connector import BaseSQLDBConnector
from mintq.registry import Registry

BaseAgentConfig: TypeAlias = BaseModel


class BaseSimpleSQLAgent(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[BaseAgentConfig]]

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
    value_dtype: Literal["int", "float", "str"]
    value_operator_options: list[Literal["<", ">", "<=", ">=", "=", "<>"]]


class UserFreeTextAnswer(BaseModel):
    answer_text: str


class UserMultipleChoiceAnswer(BaseModel):
    answer_index: int


class UserValueAnswer(BaseModel):
    type: Literal["value"] = "value"
    operator: Literal["<", ">", "<=", ">=", "=", "<>"]
    value: int | float | str


UserQuestion: TypeAlias = Annotated[
    Union[UserFreeTextQuestion, UserMultipleChoiceQuestion, UserValueQuestion], Field(discriminator="type")
]
UserAnswer: TypeAlias = Union[UserFreeTextAnswer, UserMultipleChoiceAnswer, UserValueAnswer]


class BaseUserSimulator(Protocol):
    @overload
    async def ask_async(self, question: UserFreeTextQuestion) -> UserFreeTextAnswer: ...
    @overload
    async def ask_async(self, question: UserMultipleChoiceQuestion) -> UserMultipleChoiceAnswer: ...
    @overload
    async def ask_async(self, question: UserValueQuestion) -> UserValueAnswer: ...

    async def ask_async(self, question: UserQuestion) -> UserAnswer: ...

    def usage(self) -> Usage: ...

    def trajectory(self) -> Trajectory: ...


class BaseAmbigSQLAgent(Protocol):
    name: ClassVar[str]
    task_type: ClassVar[str]
    output_type: ClassVar[str]
    config_cls: ClassVar[type[BaseAgentConfig]]

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput: ...


NL2QAgent: TypeAlias = Union[BaseSimpleSQLAgent, BaseAmbigSQLAgent]


agent_registry = Registry[NL2QAgent]("agent")
