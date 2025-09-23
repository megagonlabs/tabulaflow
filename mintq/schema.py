import datetime
import json
import os
import re
from pydantic import BaseModel, Field, field_serializer, model_validator, AfterValidator, ConfigDict, field_validator
from pydantic.types import StringConstraints
from typing import Any, Literal, Annotated, Union, Sequence
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

    def to_readable(self) -> str:
        res = []
        for msg in self.messages:
            if msg.role == "system":
                res.append(f'<message role="system">\n{msg.content}\n</message>')
            elif msg.role == "user":
                res.append(f'<message role="user">\n{msg.content}\n</message>')
            elif msg.role == "assistant":
                s = '<message role="assistant">\n'
                if msg.content:
                    try:
                        content = json.loads(msg.content)
                        content = json.dumps(content, indent=2)
                    except Exception:
                        content = msg.content
                    s += f"{content}\n"
                for tool_call in msg.tool_calls:
                    s += f'<function name="{tool_call.name}">\n'
                    for key, value in tool_call.arguments.items():
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value, indent=2)
                        else:
                            value = str(value)
                        s += f'<arg name="{key}">'
                        s += f"\n{value}\n" if "\n" in value else value
                        s += "</arg>\n"
                    s += "</function>\n"
                s += "</message>"
                res.append(s)
            elif msg.role == "tool":
                res.append(f'<message role="tool">\n{msg.response}\n</message>')
        return "<trajectory>\n" + "\n\n\n".join(res) + "\n</trajectory>"




class ExecResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    df: pd.DataFrame
    latency_seconds: float | None = None

    @field_serializer("df", when_used="json")
    def serialize_df(self, df: pd.DataFrame) -> str:
        return {
            "schema": {
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            },
            "data": df.to_dict(orient="records"),
        }

    @field_validator("df", mode="before")
    @classmethod
    def deserialize_df(cls, df_dict: dict[str, Any]) -> pd.DataFrame:
        return pd.DataFrame(df_dict["data"], dtype=df_dict["schema"]["dtypes"])

    def to_readable(self) -> str:
        df = self.df
        if len(df) > 10:
            df = pd.concat([df.head(5), df.tail(5)], ignore_index=True)
            lines = df.to_string(index=False).split("\n")
            assert len(lines) == 11
            return "\n".join(lines[:6] + ["... TRUNCATED ..."] + lines[6:])
        return df.to_string(index=False)  # type: ignore


class GoldQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = "GQRY"
    query: str | None
    """In Spider2, some gold queries are not available, so we allow it to be None"""
    parameter_names: list[str] = Field(default_factory=list)
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    """If `parameter_names` is not empty and `parameter_values` is empty, the query is parameterized."""
    exec_result: ExecResult | None = None
    other_exec_results: list[ExecResult] = Field(default_factory=list)
    """Some queries have multiple exec results (usually caused by argmax with ties), which is common in Spider2"""
    required_columns: list[int] | None = None
    required_sorted: bool = False
    extra_info: dict[str, Any] = Field(default_factory=dict)

    @property
    def all_exec_results(self) -> list[ExecResult]:
        return ([self.exec_result] if self.exec_result is not None else []) + self.other_exec_results

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        if self.exec_result is not None:
            self.exec_result.df.to_csv(os.path.join(directory, f"{self.id}.csv"), index=False)
        for i, exec_result in enumerate(self.other_exec_results):
            exec_result.df.to_csv(os.path.join(directory, f"{self.id}_other_{i}.csv"), index=False)

    def to_readable(self) -> str:
        header = self.model_dump_json(indent=2, exclude={"query"})
        res = f"/*\n{header}\n*/\n{self.query}"
        res += "".join(f"\n/*\n{exec_result.to_readable()}\n*/" for exec_result in self.all_exec_results)
        return res


class PredQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = "PQRY"
    query: str
    parameter_names: list[str] = Field(default_factory=list)
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    """If `parameter_names` is not empty and `parameter_values` is empty, the query is parameterized."""
    exec_result: ExecResult | None = None

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        if self.exec_result is not None:
            self.exec_result.df.to_directory(os.path.join(directory, f"{self.id}.csv"), index=False)

    def to_readable(self) -> str:
        header = self.model_dump_json(indent=2, exclude={"query"})
        res = f"/*\n{header}\n*/\n{self.query}"
        if self.exec_result is not None:
            res += f"\n/*\n{self.exec_result.to_readable()}\n*/"
        return res


def is_id_unique(objs: list[Any]) -> list[Any]:
    ids = [obj.id for obj in objs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"IDs of {type(objs[0]).__name__} are not unique.")
    return objs


class SimpleNL2QTask(BaseModel):
    task_type: Literal["simple"] = "simple"
    qid: str
    language: str
    db: str
    question: str
    evidence: str | None = None
    gold_query: GoldQuery
    extra_info: dict[str, Any] = {}

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        self.gold_query.to_directory(os.path.join(directory, "gold_csv"))
        with open(os.path.join(directory, "task_readable.sql"), "w") as f:
            f.write(self.to_readable() + "\n")

    def to_readable(self) -> str:
        header = self.model_dump_json(indent=2, exclude={"evidence", "gold_query"})
        res = f"/*\n{header}\n*/"
        if self.evidence is not None:
            res += f"\n\n\n/* === START OF EVIDENCE === */\n/*{self.evidence}\n*/\n/* === END OF EVIDENCE === */"
        res += (
            f"\n\n\n/* === START OF GOLD QUERY === */\n{self.gold_query.to_readable()}\n/* === END OF GOLD QUERY === */"
        )
        return res


class SimpleNL2QTaskOutput(SimpleNL2QTask):
    output_type: Literal["simple"] = "simple"
    pred_query: PredQuery
    trajectory: Trajectory
    metrics: dict[str, Any]

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        self.gold_query.to_directory(os.path.join(directory, "gold_csv"))
        self.pred_query.to_directory(os.path.join(directory, "pred_csv"))
        with open(os.path.join(directory, "result_readable.sql"), "w") as f:
            f.write(self.to_readable() + "\n")
        with open(os.path.join(directory, "trajectory.xml"), "w") as f:
            f.write(self.trajectory.to_readable())

    def to_readable(self) -> str:
        header = self.model_dump_json(indent=2, exclude={"evidence", "gold_query", "pred_query", "trajectory"})
        res = f"/*\n{header}\n*/"
        if self.evidence is not None:
            res += f"\n\n\n/* === START OF EVIDENCE === */\n/*{self.evidence}\n*/\n/* === END OF EVIDENCE === */"
        res += (
            f"\n\n\n/* === START OF GOLD QUERY === */\n{self.gold_query.to_readable()}\n/* === END OF GOLD QUERY === */"
        )
        res += (
            f"\n\n\n/* === START OF PRED QUERY === */\n{self.pred_query.to_readable()}\n/* === END OF PRED QUERY === */"
        )
        return res


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


class GoldAmbiguityPointFinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["finite"] = "finite"
    ambiguity_type: ARCSAmbiguityType
    interpretations: list[str]
    intended_interpretation_idx: int | None

    @model_validator(mode="after")
    def validate_intended_interpretation_idx(self) -> "GoldAmbiguityPointFinite":
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


def read_df(directory: str) -> pd.DataFrame:
    with open(os.path.join(directory, "df_schema.json"), "r") as f:
        schema = json.load(f)
    df = pd.read_csv(os.path.join(directory, "df_data.csv"), dtype=schema["dtypes"])
    return df


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
            gq.to_directory(os.path.join(directory, "gold_csv"))
        with open(os.path.join(directory, "task_readable.sql"), "w") as f:
            f.write(self.to_readable() + "\n")

    def to_readable(self) -> str:
        header = self.model_dump_json(indent=2, exclude={"gold_queries"})
        return f"/*\n{header}\n*/" + "".join(f"\n\n\n{gq.to_readable()}" for gq in self.gold_queries)

    @model_validator(mode="after")
    def validate_gold_queries(self) -> "AmbigNL2QTask":
        # Gold query ID must match the pattern "GQRY(-[A-Z]+\.[0-9]+)*" (e.g. "GQRY-A.2-B.0")
        pattern = r"^GQRY(-[A-Z]+\.[0-9]+)*$"
        assert all(re.match(pattern, gq.id) for gq in self.gold_queries)

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
    def validate_has_intended_resolution(self) -> "AmbigNL2QTask":
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
    def validate_id_reference(self) -> "AmbigNL2QTask":
        ap_ids = set(ap.id for ap in self.gold_ambiguity_points)
        assert all(
            ap.parent_ambiguity_point_id is None or ap.parent_ambiguity_point_id in ap_ids
            for ap in self.gold_ambiguity_points
            if ap.type == "infinite"
        )
        gold_query_ids = set(gq.id for gq in self.gold_queries)
        assert self.gold_intended_gold_query_id is None or self.gold_intended_gold_query_id in gold_query_ids
        return self


class SimpleAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model only predicts the final disambiguated query
    """

    output_type: Literal["ambig-simple"] = "ambig-simple"
    pred_intended_query: PredQuery
    metrics: dict[str, Any]


class FlatAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model predicts a list of interpretations, the SQL for each interpretation, and the final disambiguated query
    (e.g. the "Disambiguate First Parse Later" paper https://arxiv.org/pdf/2502.18448)
    """

    output_type: Literal["ambig-flat"] = "ambig-flat"
    pred_queries: Annotated[list[PredQuery], AfterValidator(is_id_unique)]
    pred_intended_query_id: str
    metrics: dict[str, Any]


class PredAmbiguityPointFinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["finite"] = "finite"
    interpretations: list[str]
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
    metrics: dict[str, Any]

    @model_validator(mode="after")
    def validate_pred_queries(self) -> "StructuredAmbigNL2QTaskOutput":
        # Pred query ID must match the pattern "PQRY(-[A-Z]+\.[0-9]+)*" (e.g. "PQRY-A.2-B.0")
        pattern = r"^PQRY(-[A-Z]+\.[0-9]+)*$"
        assert all(re.match(pattern, pq.id) for pq in self.pred_queries)

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
    split: str
    databases: list[str] | None  # None means all databases
    subsample_size: int | None
    tasks: Sequence[NL2QTask]
    db_connectors: dict[str, Any]


class NL2QRunResult(BaseModel):
    start_time: datetime.datetime
    end_time: datetime.datetime
    dataset: str
    split: str
    databases: list[str] | None  # None means all databases
    subsample_size: int | None
    agent: str
    agent_args: dict[str, Any]
    aggregated_metrics: dict[str, Any]
    tasks: list[NL2QTaskOutput]

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "result.json"), "w") as f:
            f.write(self.model_dump_json(indent=2))

        for task in self.tasks:
            task.to_directory(os.path.join(directory, "readable", task.qid))


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
