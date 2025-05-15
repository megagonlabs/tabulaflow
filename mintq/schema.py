from abc import ABC
from pydantic import BaseModel, Field
from typing import Optional, Dict, Union, List, Any, Literal, Annotated


class SystemMessage(BaseModel):
    role: Literal["system"] = "system"
    content: str


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str


class ToolCall(BaseModel):
    tool_call_id: str
    name: str
    arguments: Dict[str, Any]


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str
    tool_calls: List[ToolCall]


class ToolResponse(BaseModel):
    role: Literal["tool"] = "tool"
    tool_call_id: str
    response: str


Message = Annotated[
    Union[AssistantMessage, ToolResponse, UserMessage, SystemMessage],
    Field(discriminator="role"),
]


class Trajectory(BaseModel):
    messages: List[Message]


class BaseNL2QTask(BaseModel, ABC):
    qid: str
    language: str
    db: str
    question: str
    evidence: str | None = None
    metrics: Dict[str, Union[float, int]] = {}
    extra_info: Dict[str, Any] = {}


class SingleOutputNL2QTask(BaseNL2QTask):
    gold_queries: List[str] = []
    gold_exec_results: List[List[dict]] = []
    pred_query: str | None = None
    trajectory: Trajectory | None = None


class MultiOutputNL2QTask(BaseNL2QTask):
    gold_queries: List[str] = []
    gold_exec_results: List[List[dict]] = []
    pred_queries: List[str] = []
    trajectories: List[Trajectory] = []


NL2QTask = Union[SingleOutputNL2QTask, MultiOutputNL2QTask]


class NL2QDataset(BaseModel):
    name: str
    split_id: str
    tasks: list[NL2QTask]
    db_connectors: dict[str, Any]


class BaseDBSchema(BaseModel, ABC):
    pass


class SQLColumnSchema(BaseModel):
    name: str
    dtype: str
    examples: List[Any]


class SQLTableSchema(BaseModel):
    name: str
    schema_name: str | None = None
    columns: List[SQLColumnSchema]
    primary_key: List[str]
    num_rows: int


class ForeignKeySchema(BaseModel):
    schema_name: str | None = None
    table: str
    columns: List[str]
    foreign_schema_name: str | None = None
    foreign_table: str
    foreign_columns: List[str]


class SQLSchema(BaseDBSchema):
    name: str
    tables: List[SQLTableSchema]
    foreign_keys: List[ForeignKeySchema]


class ERDiagramRelation(BaseModel):
    from_schema: str | None = None
    from_table: str
    from_column: str
    to_schema: str | None = None
    to_table: str
    to_column: str


class ERDiagram(BaseModel):
    db_schema: SQLSchema
    relations: List[ERDiagramRelation]
