from abc import ABC
import datetime
from pydantic import BaseModel, Field
from typing import Any, Literal, Annotated, Union


class SystemMessage(BaseModel):
    role: Literal["system"] = "system"
    content: str


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str


class ToolCall(BaseModel):
    tool_call_id: str
    name: str
    arguments: dict[str, Any]


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str
    tool_calls: list[ToolCall]


class ToolResponse(BaseModel):
    role: Literal["tool"] = "tool"
    tool_call_id: str
    response: str


Message = Annotated[
    Union[AssistantMessage, ToolResponse, UserMessage, SystemMessage],
    Field(discriminator="role"),
]


class Trajectory(BaseModel):
    messages: list[Message]


class BaseNL2QTask(BaseModel, ABC):
    qid: str
    language: str
    db: str
    question: str
    evidence: str | None = None
    metrics: dict[str, float | int] = {}
    extra_info: dict[str, Any] = {}


class SingleOutputNL2QTask(BaseNL2QTask):
    task_type: Literal["single_output"] = "single_output"
    gold_queries: list[str] = []
    gold_exec_results: list[list[dict]] = []
    pred_query: str | None = None
    trajectory: Trajectory | None = None


class MultiOutputNL2QTask(BaseNL2QTask):
    task_type: Literal["multi_output"] = "multi_output"
    gold_queries: list[str] = []
    gold_exec_results: list[list[dict]] = []
    pred_queries: list[str] = []
    trajectories: list[Trajectory] = []


NL2QTask = Annotated[Union[SingleOutputNL2QTask, MultiOutputNL2QTask], Field(discriminator="task_type")]


class NL2QDataset(BaseModel):
    name: str
    split_id: str
    databases: list[str] | None  # None means all databases
    tasks: list[NL2QTask]
    db_connectors: dict[str, Any]


class NL2QRunResult(BaseModel):
    start_time: datetime.datetime
    end_time: datetime.datetime
    dataset: str
    split_id: str
    databases: list[str] | None  # None means all databases
    model: str
    model_args: dict[str, Any]
    aggregated_metrics: dict[str, float | int]
    tasks: list[NL2QTask]


class BaseDBSchema(BaseModel, ABC):
    pass


class SQLColumnSchema(BaseModel):
    name: str
    dtype: str
    examples: list[Any]


class SQLTableSchema(BaseModel):
    name: str
    schema_name: str | None = None
    columns: list[SQLColumnSchema]
    primary_key: list[str]
    num_rows: int


class ForeignKeySchema(BaseModel):
    schema_name: str | None = None
    table: str
    columns: list[str]
    foreign_schema_name: str | None = None
    foreign_table: str
    foreign_columns: list[str]


class SQLSchema(BaseDBSchema):
    name: str
    tables: list[SQLTableSchema]
    foreign_keys: list[ForeignKeySchema]


class ERDiagramRelation(BaseModel):
    from_schema: str | None = None
    from_table: str
    from_column: str
    to_schema: str | None = None
    to_table: str
    to_column: str


class ERDiagram(BaseModel):
    db_schema: SQLSchema
    relations: list[ERDiagramRelation]
