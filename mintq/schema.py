import datetime
import json
import os
from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    model_validator,
    AfterValidator,
    ConfigDict,
)
from pydantic.types import StringConstraints
from typing import Any, Literal, Annotated, Union
import pandas as pd
import math
import itertools


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
    output_type: Literal["simple"] = "simple"
    metrics: dict[str, float | int]
    pred_query: str
    pred_exec_result: list[dict[str, Any]] | None = None
    trajectory: Trajectory


ARCSAmbiguityType = Literal[
    "semantic_column",
    "semantic_table",
    "semantic_value",
    "semantic_computation",
    "syntactic_column",
    "syntactic_table",
    "syntactic_value",
    "syntactic_computation",
]


def is_id_unique(objs: list[Any]) -> list[Any]:
    ids = [obj.id for obj in objs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"IDs of {type(objs[0]).__name__} are not unique.")
    return objs


class GoldAmbiguityPointFinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["finite"] = "finite"
    ambiguity_type: ARCSAmbiguityType
    interpretations: list[str]
    intended_interpretation_idx: int | None

    @model_validator(mode="after")
    def validate_intended_interpretation_idx(self):
        if self.intended_interpretation_idx is not None:
            if self.intended_interpretation_idx < 0 or self.intended_interpretation_idx >= len(self.interpretations):
                raise ValueError(
                    f'phrase "{self.phrase}": intended_interpretation_idx {self.intended_interpretation_idx} is out of range.'
                )
        return self


class GoldAmbiguityPointInfinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["infinite"] = "infinite"
    ambiguity_type: ARCSAmbiguityType
    parent_ambiguity_point_id: str | None = None
    parameter_name: str
    parameter_operator: Literal["<", ">", "<=", ">="]
    parameter_sample_values: list[Any] | list[list[Any]]
    """list[list[Any]] only allowed when `parent_ambiguity_point_id` is not None"""
    indended_parameter_value: Any | None


GoldAmbiguityPoint = Annotated[Union[GoldAmbiguityPointFinite, GoldAmbiguityPointInfinite], Field(discriminator="type")]


class ExecResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    df: pd.DataFrame
    latency_seconds: float

    @field_serializer("df", when_used="json")
    def save_df(self, df: pd.DataFrame) -> None:
        return None

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        schema = {"dtypes": {col: str(dtype) for col, dtype in self.df.dtypes.items()}}
        with open(os.path.join(directory, "df_schema.json"), "w") as f:
            json.dump(schema, f, indent=2)

        self.df.to_csv(os.path.join(directory, "df_data.csv"), index=False)


class GoldQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Annotated[str, StringConstraints(pattern=r"^GQRY(-[A-Z]+\.[0-9]+)*$")]
    """Example: GQRY-A.2-B.0"""
    query: str
    parameter_names: list[str] = Field(default_factory=list)
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    """If `parameter_names` is not empty and `parameter_values` is empty, the query is parameterized."""
    exec_result: ExecResult | None = None
    required_columns: list[int] | None = None
    required_sorted: bool = False
    extra_info: dict[str, Any] = Field(default_factory=dict)

    @property
    def resolution_mapping(self) -> dict[str, int]:
        return {part.split(".")[0]: int(part.split(".")[1]) for part in self.id.split("-")[1:]}

    def to_directory(self, directory: str) -> None:
        self.exec_result.to_directory(directory)
        with open(os.path.join(directory, "query.sql"), "w") as f:
            f.write(self.query)

    def to_readable_sql(self) -> str:
        header = self.model_dump_json(indent=2, exclude=["query"])
        return f"/*\n{header}\n*/\n{self.query}"


class AmbigNL2QTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    qid: str
    task_type: Literal["ambig"] = "ambig"
    has_intended_resolution: bool
    language: str
    db: str
    question: str
    gold_ambiguity_points: Annotated[list[GoldAmbiguityPoint], AfterValidator(is_id_unique)]
    gold_queries: Annotated[list[GoldQuery], AfterValidator(is_id_unique)]
    gold_intended_gold_query_id: str | None
    """Ground-truth query intended by the user"""
    extra_info: dict[str, Any] = Field(default_factory=dict)

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        for gq in self.gold_queries:
            gq.to_directory(os.path.join(directory, gq.id))
        with open(os.path.join(directory, "task.json"), "w") as f:
            f.write(self.model_dump_json(indent=2))
        with open(os.path.join(directory, "task_readable.sql"), "w") as f:
            f.write(self.to_readable_sql() + "\n")

    def to_readable_sql(self) -> str:
        header = self.model_dump_json(indent=2, exclude=["gold_queries"])
        return f"/*\n{header}\n*/" + "".join(f"\n\n\n{gq.to_readable_sql()}" for gq in self.gold_queries)

    @classmethod
    def from_directory(cls, directory: str) -> "AmbigNL2QTask":
        with open(os.path.join(directory, "task.json"), "r") as f:
            data = json.load(f)
        for gq in data["gold_queries"]:
            with open(os.path.join(directory, gq["id"], "df_schema.json"), "r") as f:
                schema = json.load(f)
            df = pd.read_csv(os.path.join(directory, gq["id"], "df_data.csv"), dtype=schema["dtypes"])
            gq["exec_result"]["df"] = df
        return cls.model_validate(data)

    @model_validator(mode="after")
    def validate_gold_queries(self):
        finite_aps = sorted([ap for ap in self.gold_ambiguity_points if ap.type == "finite"], key=lambda x: x.id)
        required_ids = [
            "GQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, indexes))
            for indexes in itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps])
        ]
        gold_query_ids = set(gq.id for gq in self.gold_queries)
        for gq_id in gold_query_ids:
            if gq_id not in required_ids:
                raise ValueError(
                    f"qid {self.qid}: Gold query {gq_id} is not required. Only {required_ids} are required."
                )
        for required_id in required_ids:
            if required_id not in gold_query_ids:
                raise ValueError(
                    f"qid {self.qid}: Gold query {required_id} is not found. Only {gold_query_ids} are found."
                )
        assert len(self.gold_queries) == len(required_ids) == math.prod(len(ap.interpretations) for ap in finite_aps)
        return self

    @model_validator(mode="after")
    def validate_has_intended_resolution(self):
        if self.has_intended_resolution:
            assert self.gold_intended_gold_query_id is not None
            assert all(
                ap.intended_interpretation_idx is not None for ap in self.gold_ambiguity_points if ap.type == "finite"
            )
            assert all(
                ap.indended_parameter_value is not None for ap in self.gold_ambiguity_points if ap.type == "infinite"
            )
        else:
            assert self.gold_intended_gold_query_id is None
            assert all(
                ap.intended_interpretation_idx is None for ap in self.gold_ambiguity_points if ap.type == "finite"
            )
            assert all(
                ap.indended_parameter_value is None for ap in self.gold_ambiguity_points if ap.type == "infinite"
            )
        return self

    @model_validator(mode="after")
    def validate_id_reference(self):
        ap_ids = set(ap.id for ap in self.gold_ambiguity_points)
        assert all(
            ap.parent_ambiguity_point_id is None or ap.parent_ambiguity_point_id in ap_ids
            for ap in self.gold_ambiguity_points
            if ap.type == "infinite"
        )
        gold_query_ids = set(gq.id for gq in self.gold_queries)
        assert self.gold_intended_gold_query_id is None or self.gold_intended_gold_query_id in gold_query_ids
        return self


class PredQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Annotated[str, StringConstraints(pattern=r"^PQRY(-[A-Z]+\.[0-9]+)*$")]
    """Example: PQRY-A.2-B.0"""
    query: str
    parameter_names: list[str] = Field(default_factory=list)
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    """If `parameter_names` is not empty and `parameter_values` is empty, the query is parameterized."""
    exec_result: ExecResult | None = None


class SimpleAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model only predicts the final disambiguated query
    """

    output_type: Literal["ambig-simple"] = "ambig-simple"
    pred_intended_query: PredQuery
    metrics: dict[str, float | int]


class FlatAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model predicts a list of interpretations, the SQL for each interpretation, and the final disambiguated query
    (e.g. the "Disambiguate First Parse Later" paper https://arxiv.org/pdf/2502.18448)
    """

    output_type: Literal["ambig-flat"] = "ambig-flat"
    pred_queries: Annotated[list[PredQuery], AfterValidator(is_id_unique)]
    pred_intended_query_id: str
    metrics: dict[str, float | int]


class PredAmbiguityPointFinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["finite"] = "finite"
    interpretations: list[str] | None
    intended_interpretation_idx: int | None


class PredAmbiguityPointInfinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["infinite"] = "infinite"
    parent_ambiguity_point_id: str | None
    parameter_name: str
    parameter_operator: Literal["<", ">", "<=", ">="]
    parameter_sample_values: list[Any] | list[list[Any]]
    intended_parameter_value: Any | None


PredAmbiguityPoint = Annotated[Union[PredAmbiguityPointFinite, PredAmbiguityPointInfinite], Field(discriminator="type")]


class StructuredAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model predicts all the ambiguity points, their interpretations, the SQL for each interpretation combination, as well as the final disambiguated query
    """

    output_type: Literal["ambig-structured"] = "ambig-structured"
    pred_ambiguity_points: Annotated[list[PredAmbiguityPoint], AfterValidator(is_id_unique)]
    pred_queries: Annotated[list[PredQuery], AfterValidator(is_id_unique)]
    pred_intended_query_id: str
    metrics: dict[str, float | int]

    @model_validator(mode="after")
    def validate_pred_queries(self):
        finite_aps = sorted([ap for ap in self.pred_ambiguity_points if ap.type == "finite"], key=lambda x: x.id)
        required_ids = [
            "PQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, indexes))
            for indexes in itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps])
        ]
        pred_query_ids = set(pq.id for pq in self.pred_queries)
        for pq_id in pred_query_ids:
            if pq_id not in required_ids:
                raise ValueError(f"qid {self.qid}: Pred query {pq_id} is not required.")
        for required_id in required_ids:
            if required_id not in pred_query_ids:
                raise ValueError(f"qid {self.qid}: Pred query {required_id} is not found.")
        assert len(self.pred_queries) == len(required_ids) == math.prod(len(ap.interpretations) for ap in finite_aps)
        return self


NL2QTask = Annotated[Union[SimpleNL2QTask, AmbigNL2QTask], Field(discriminator="task_type")]
NL2QTaskOutput = Annotated[
    Union[SimpleNL2QTaskOutput, SimpleAmbigNL2QTaskOutput, FlatAmbigNL2QTaskOutput, StructuredAmbigNL2QTaskOutput],
    Field(discriminator="output_type"),
]


class NL2QDataset(BaseModel):
    name: str
    split_id: str
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
    task_outputs: list[NL2QTaskOutput]


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
    description: str | None
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
