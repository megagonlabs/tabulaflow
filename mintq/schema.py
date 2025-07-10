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
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ToolResponse(BaseModel):
    role: Literal["tool"] = "tool"
    tool_call_id: str
    response: str
    is_retry_prompt: bool = False


Message = Annotated[
    Union[AssistantMessage, ToolResponse, UserMessage, SystemMessage],
    Field(discriminator="role"),
]


class Trajectory(BaseModel):
    messages: list[Message]


class SimpleNL2QTask(BaseModel):
    task_type: Literal["simple"] = "simple"
    qid: str
    language: str
    db: str
    question: str
    evidence: str | None = None
    extra_info: dict[str, Any] = {}
    gold_queries: list[str] = Field(default_factory=list)
    gold_exec_results: list[list[dict[str, Any]]] = Field(default_factory=list)


class SimpleNL2QTaskOutput(SimpleNL2QTask):
    metrics: dict[str, float | int]
    pred_query: str
    trajectory: Trajectory


class MultiNL2QTask(BaseModel):
    task_type: Literal["multi"] = "multi"
    qid: str
    language: str
    db: str
    question: str
    evidence: str | None = None
    extra_info: dict[str, Any] = {}
    gold_queries: list[str] = Field(default_factory=list)
    gold_exec_results: list[list[dict[str, Any]]] = Field(default_factory=list)


class MultiNL2QTaskOutput(MultiNL2QTask):
    metrics: dict[str, float | int]
    pred_queries: list[str]
    trajectories: list[Trajectory]


NL2QTask = Annotated[Union[SimpleNL2QTask, MultiNL2QTask], Field(discriminator="task_type")]
NL2QTaskOutput = Annotated[Union[SimpleNL2QTaskOutput, MultiNL2QTaskOutput], Field(discriminator="task_type")]


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
    tasks: list[NL2QTaskOutput]


class BaseDBSchema(BaseModel):
    pass


class ForeignKeySchema(BaseModel):
    columns: list[str]
    foreign_schema_name: str | None = None
    foreign_table: str
    foreign_columns: list[str]


class SQLColumnSchema(BaseModel):
    name: str
    dtype: str
    description: str | None = None
    nullable: bool
    null_ratio: float
    num_unique: int | None  # Only for text or integer columns
    unique_ratio: float | None  # Only for text or integer columns
    examples: list[Any]
    primary_key_type: Literal["single", "composite"] | None = None
    foreign_keys: list[ForeignKeySchema] = Field(default_factory=list)  # Includes composite foreign keys


class SQLTableSchema(BaseModel):
    name: str
    schema_name: str | None = None
    description: str | None = None
    is_view: bool
    columns: list[SQLColumnSchema]
    primary_key: list[str]
    num_rows: int
    foreign_keys: list[ForeignKeySchema]


class SQLSchema(BaseDBSchema):
    name: str
    tables: list[SQLTableSchema]


class HColumnGroup(BaseModel):
    name: str
    description: str | None
    column_names: list[str]
    dtype: str
    nullable: bool
    null_ratio: float
    num_unique: int | None
    unique_ratio: float | None
    examples: list[Any]
    primary_key_type: Literal["single", "composite"] | None = None
    foreign_keys: list[ForeignKeySchema] = Field(
        default_factory=list
    )  # in hschemas, the column names in fk become column group names


class HTableSection(BaseModel):
    name: str
    description: str | None
    column_groups: list[HColumnGroup]


class HTableGroup(BaseModel):
    name: str
    table_names: list[str]
    schema_name: str | None = None
    primary_key: list[str]
    foreign_keys: list[ForeignKeySchema]
    sections: list[HTableSection]


class HSQLSchema(BaseModel):
    name: str
    table_groups: list[HTableGroup]


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
