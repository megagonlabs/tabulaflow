from collections.abc import Set
import datetime
import json
import os
import re
import litellm
from pydantic import BaseModel, Field, field_serializer, model_validator, AfterValidator, ConfigDict, field_validator
from pydantic.types import StringConstraints
import pydantic_ai
from typing import Any, Literal, Annotated, Union
import pandas as pd
import logging
import math
import itertools
from mintq.config import config

logger = logging.getLogger(__name__)


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
    id: str = "TRJY"
    messages: list[Message]

    @classmethod
    def from_pydantic_ai_messages(
        cls, messages: list[pydantic_ai.messages.ModelMessage], id: str = "TRJY"
    ) -> "Trajectory":
        trajectory = cls(messages=[], id=id)
        if messages[0].kind == "request" and messages[0].instructions:
            trajectory.messages.append(SystemMessage(content=messages[0].instructions))
        for msg in messages:
            if msg.kind == "request":
                for part in msg.parts:
                    if part.part_kind == "system-prompt":
                        trajectory.messages.append(SystemMessage(content=part.content))
                    elif part.part_kind == "user-prompt":
                        if not isinstance(part.content, str):
                            raise ValueError(f"Only string is supported for user prompt, got {type(part.content)}")
                        trajectory.messages.append(UserMessage(content=part.content))
                    elif part.part_kind == "tool-return":
                        if not isinstance(part.content, str):
                            raise ValueError(f"Tool return is not a string: {part.content}")
                        trajectory.messages.append(ToolResponse(response=part.content, tool_call_id=part.tool_call_id))
                    elif part.part_kind == "retry-prompt":
                        trajectory.messages.append(
                            ToolResponse(
                                response=str(part.content), tool_call_id=part.tool_call_id, is_retry_prompt=True
                            )
                        )
                    else:
                        raise ValueError(f"Unknown message part type: {part.part_kind}")
            elif msg.kind == "response":
                new_msg = AssistantMessage(content="", tool_calls=[])
                for part in msg.parts:  # type: ignore
                    if part.part_kind == "text":  # type: ignore
                        new_msg.content += part.content
                    elif part.part_kind == "tool-call":  # type: ignore
                        arguments = part.args
                        if isinstance(arguments, str):
                            arguments = json.loads(arguments)
                        new_msg.tool_calls.append(
                            ToolCall(tool_call_id=part.tool_call_id, name=part.tool_name, arguments=arguments)
                        )
                    else:
                        raise ValueError(f"Unknown message part type: {part.part_kind}")
                trajectory.messages.append(new_msg)
            else:
                raise ValueError(f"Unknown message type: {msg.kind}")
        return cls.model_validate(trajectory.model_dump())

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


class Usage(BaseModel):
    llm: str
    api_calls: int
    input_tokens: int
    output_tokens: int
    api_cost_usd: float

    @classmethod
    def from_pydantic_ai_usage(cls, usage: pydantic_ai.usage.Usage, llm: str) -> "Usage":
        input_tokens = usage.request_tokens or 0
        output_tokens = usage.response_tokens or 0
        return cls(
            api_calls=usage.requests,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            api_cost_usd=cls.get_llm_api_cost(llm, input_tokens, output_tokens),
            llm=llm,
        )

    @staticmethod
    def get_llm_api_cost(pydantic_ai_model: str, input_tokens: int, output_tokens: int) -> float:
        try:
            litellm_model = pydantic_ai_model.replace(":", "/")
            input_cost, output_cost = litellm.cost_per_token(  # type: ignore
                model=litellm_model, prompt_tokens=input_tokens, completion_tokens=output_tokens
            )
            return input_cost + output_cost
        except Exception:
            return 0.0


class ErrorInfo(BaseModel):
    exc_type: str
    message: str


class ExecResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    df: pd.DataFrame | None
    df_is_truncated: bool = False
    """True if the df is truncated, e.g. when the result is too large"""
    error: ErrorInfo | None = None
    latency_seconds: float | None = None

    @field_serializer("df", when_used="json")
    def serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any]:
        if df is None:
            return None
        return {
            "schema": {
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            },
            "data": df.to_dict(orient="records"),
        }

    @field_validator("df", mode="before")
    @classmethod
    def deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame:
        if v is None or isinstance(v, pd.DataFrame):
            return v
        dtypes = v["schema"]["dtypes"]
        df = pd.DataFrame(v["data"], columns=list(dtypes.keys()))
        df = df.astype(dtypes)
        return df

    @model_validator(mode="after")
    def truncate_df(self) -> "ExecResult":
        if config.df_max_rows and self.df is not None and len(self.df) > config.df_max_rows:
            self.df = self.df.head(config.df_max_rows)
            self.df_is_truncated = True
            logger.warning(f"Truncated df to {config.df_max_rows} rows")
        return self

    @model_validator(mode="after")
    def validate_df_or_error(self) -> "ExecResult":
        if self.df is None and self.error is None or self.df is not None and self.error is not None:
            raise ValueError("ExecResult must have either df or error, but not both")
        return self

    def to_readable(self) -> str:
        if self.df is None:
            res = f"(query failed: {self.error})"
        else:
            df = self.df
            if len(df) > 10:
                df = pd.concat([df.head(5), df.tail(5)], ignore_index=True)
                lines = df.to_string(index=False).split("\n")
                assert len(lines) == 11
                res = "\n".join(lines[:6] + ["... TRUNCATED ..."] + lines[6:])
            else:
                res = df.to_string(index=False)
        return f"/* EXEC RESULT\n{res}\n*/"


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
        if self.exec_result is not None and self.exec_result.df is not None:
            self.exec_result.df.to_csv(os.path.join(directory, f"{self.id}.csv"), index=False)
        for i, exec_result in enumerate(self.other_exec_results):
            if exec_result.df is not None:
                exec_result.df.to_csv(os.path.join(directory, f"{self.id}_other_{i}.csv"), index=False)

    def to_readable(self) -> str:
        header = self.model_dump_json(indent=2, exclude={"query", "exec_result"})
        res = f"/*\n{header}\n*/\n{self.query}"
        res += "".join(f"\n{exec_result.to_readable()}" for exec_result in self.all_exec_results)
        return f"----- START OF GOLD QUERY `{self.id}` -----\n{res}\n----- END OF GOLD QUERY -----"


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
        if self.exec_result is not None and self.exec_result.df is not None:
            self.exec_result.df.to_csv(os.path.join(directory, f"{self.id}.csv"), index=False)

    def to_readable(self) -> str:
        header = self.model_dump_json(indent=2, exclude={"query", "exec_result"})
        res = f"/*\n{header}\n*/\n{self.query}"
        if self.exec_result is not None:
            res += f"\n{self.exec_result.to_readable()}"
        return f"----- START OF PRED QUERY `{self.id}` -----\n{res}\n----- END OF PRED QUERY -----"


def is_id_unique(objs: list[Any]) -> list[Any]:
    ids = [obj.id for obj in objs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"IDs of {type(objs[0]).__name__} are not unique.")
    return objs


class CSVSummaryRow(BaseModel):
    qid: str
    db: str
    question: str
    evidence: str | None = None
    gold_query: str | None = None
    pred_query: str | None = None
    gold_exec_result: str | None = None
    pred_exec_result: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)

    def fields(self) -> list[str]:
        return list(CSVSummaryRow.model_fields.keys())[:-1] + list(self.metrics.keys())

    def data(self) -> list[Any]:
        return list(self.model_dump().values())[:-1] + list(self.metrics.values())


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
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)


class SimpleNL2QTaskOutput(SimpleNL2QTask):
    output_type: Literal["simple"] = "simple"
    pred_query: PredQuery
    trajectory: Trajectory | list[Trajectory] | None = None
    usages: list[Usage] = Field(default_factory=list)
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return CSVSummaryRow(
            qid=self.qid,
            db=self.db,
            question=self.question,
            evidence=self.evidence,
            gold_query=self.gold_query.query,
            pred_query=self.pred_query.query,
            gold_exec_result="\n".join([exec_result.to_readable() for exec_result in self.gold_query.all_exec_results]),
            pred_exec_result=self.pred_query.exec_result.to_readable() if self.pred_query.exec_result else None,
            metrics={m: self.eval_metrics.get(m) for m in eval_metrics},
        )


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
    gold_intended_query_id: str | None
    """Ground-truth query intended by the user"""
    extra_info: dict[str, Any] = Field(default_factory=dict)

    @property
    def gold_intended_query(self) -> GoldQuery | None:
        if self.gold_intended_query_id is None:
            return None
        id_to_query = {gq.id: gq for gq in self.gold_queries}
        return id_to_query[self.gold_intended_query_id]

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

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
            assert self.gold_intended_query_id is not None
            assert all(
                ap.intended_interpretation_idx is not None for ap in self.gold_ambiguity_points if ap.type == "finite"
            )
            assert all(
                ap.indended_parameter_value is not None for ap in self.gold_ambiguity_points if ap.type == "infinite"
            )
        else:
            assert self.gold_intended_query_id is None
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
        assert self.gold_intended_query_id is None or self.gold_intended_query_id in gold_query_ids
        return self


class SimpleAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model only predicts the final disambiguated query
    """

    output_type: Literal["ambig-simple"] = "ambig-simple"
    pred_intended_query: PredQuery
    trajectory: Trajectory | list[Trajectory] | None = None
    usages: list[Usage] = Field(default_factory=list)
    user_simulator_usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return CSVSummaryRow(
            qid=self.qid,
            db=self.db,
            question=self.question,
            gold_query=self.gold_intended_query.query if self.gold_intended_query else None,
            pred_query=self.pred_intended_query.query,
            gold_exec_result=self.gold_intended_query.exec_result.to_readable()
            if self.gold_intended_query and self.gold_intended_query.exec_result
            else None,
            pred_exec_result=self.pred_intended_query.exec_result.to_readable()
            if self.pred_intended_query.exec_result
            else None,
            metrics={m: self.eval_metrics.get(m) for m in eval_metrics},
        )


class FlatAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model predicts a list of interpretations, the SQL for each interpretation, and the final disambiguated query
    (e.g. the "Disambiguate First Parse Later" paper https://arxiv.org/pdf/2502.18448)
    """

    output_type: Literal["ambig-flat"] = "ambig-flat"
    interpretations: list[str]
    pred_queries: Annotated[list[PredQuery], AfterValidator(is_id_unique)]
    pred_intended_query_id: str | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usages: list[Usage] = Field(default_factory=list)
    user_simulator_usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""

    @model_validator(mode="after")
    def validate_interpretations(self) -> "FlatAmbigNL2QTaskOutput":
        assert len(self.interpretations) == len(self.pred_queries)
        return self

    @property
    def pred_intended_query(self) -> PredQuery | None:
        if self.pred_intended_query_id is None:
            return None
        id_to_query = {pq.id: pq for pq in self.pred_queries}
        return id_to_query[self.pred_intended_query_id]

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return CSVSummaryRow(
            qid=self.qid,
            db=self.db,
            question=self.question,
            gold_query=self.gold_intended_query.query if self.gold_intended_query else None,
            pred_query=self.pred_intended_query.query if self.pred_intended_query else None,
            gold_exec_result=self.gold_intended_query.exec_result.to_readable()
            if self.gold_intended_query and self.gold_intended_query.exec_result
            else None,
            pred_exec_result=self.pred_intended_query.exec_result.to_readable()
            if self.pred_intended_query and self.pred_intended_query.exec_result
            else None,
            metrics={m: self.eval_metrics.get(m) for m in eval_metrics},
        )


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
    pred_intended_query_id: str | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usages: list[Usage] = Field(default_factory=list)
    user_simulator_usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""

    @property
    def pred_intended_query(self) -> PredQuery | None:
        if self.pred_intended_query_id is None:
            return None
        id_to_query = {pq.id: pq for pq in self.pred_queries}
        return id_to_query[self.pred_intended_query_id]

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

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return CSVSummaryRow(
            qid=self.qid,
            db=self.db,
            question=self.question,
            gold_query=self.gold_intended_query.query if self.gold_intended_query else None,
            pred_query=self.pred_intended_query.query if self.pred_intended_query else None,
            gold_exec_result=self.gold_intended_query.exec_result.to_readable()
            if self.gold_intended_query and self.gold_intended_query.exec_result
            else None,
            pred_exec_result=self.pred_intended_query.exec_result.to_readable()
            if self.pred_intended_query and self.pred_intended_query.exec_result
            else None,
            metrics={m: self.eval_metrics.get(m) for m in eval_metrics},
        )


NL2QTask = Annotated[Union[SimpleNL2QTask, AmbigNL2QTask], Field(discriminator="task_type")]
NL2QTaskOutput = Annotated[
    Union[SimpleNL2QTaskOutput, SimpleAmbigNL2QTaskOutput, FlatAmbigNL2QTaskOutput, StructuredAmbigNL2QTaskOutput],
    Field(discriminator="output_type"),
]


def _get_query_fields(task: NL2QTask | NL2QTaskOutput, types: list[type[Any]]) -> list[str]:
    res = []
    for key, value in type(task).model_fields.items():
        if value.annotation in types:
            res.append(key)
    return res


def _save_trajectories(trajectory: Trajectory | list[Trajectory], directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    trajectories = trajectory if isinstance(trajectory, list) else [trajectory]
    ids = [tr.id for tr in trajectories]
    if len(ids) != len(set(ids)):
        logger.warning(f"Trajectory IDs are not unique: {ids}, some trajectories will be overwritten")
    for tr in trajectories:
        with open(os.path.join(directory, f"{tr.id}.xml"), "w") as f:
            f.write(tr.to_readable())


def _task_to_directory(task: NL2QTask | NL2QTaskOutput, directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    for prefix, t in [("gold", GoldQuery), ("pred", PredQuery)]:
        for field in _get_query_fields(task, [t, list[t]]):
            queries = getattr(task, field)
            if not isinstance(queries, list):
                queries = [queries]
            for q in queries:
                q.to_directory(os.path.join(directory, f"{prefix}_csv"))
    with open(os.path.join(directory, "task_readable.sql"), "w") as f:
        f.write(task.to_readable())
    if getattr(task, "trajectory", None) is not None:
        _save_trajectories(task.trajectory, os.path.join(directory, "trajectory"))


def _task_to_readable(task: NL2QTask | NL2QTaskOutput) -> str:
    query_fields = _get_query_fields(task, [GoldQuery, list[GoldQuery], PredQuery, list[PredQuery]])
    header = task.model_dump_json(indent=2, exclude=set(["evidence", "trajectory"] + query_fields))
    res = f"/*\n{header}\n*/"
    if getattr(task, "evidence", None) is not None:
        res += f"\n\n\n----- START OF EVIDENCE -----\n/*\n{task.evidence}\n*/\n----- END OF EVIDENCE -----"
    for field in query_fields:
        queries = getattr(task, field)
        if not isinstance(queries, list):
            queries = [queries]
        for q in queries:
            res += f"\n\n\n{q.to_readable()}"
    return res


class NL2QDataset(BaseModel):
    name: str
    split: str
    databases: list[str] | None = None  # None means all databases
    subsample_size: int | None = None
    tasks: list[NL2QTask]
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
    aggregated_inference_metrics: dict[str, Any] = Field(default_factory=dict)
    aggregated_eval_metrics: dict[str, Any] = Field(default_factory=dict)
    tasks: list[NL2QTaskOutput]

    def to_directory(self, directory: str, eval_metrics_in_summary: list[str] = []) -> None:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "result.json"), "w") as f:
            f.write(self.model_dump_json(indent=2))

        self.to_csv(os.path.join(directory, "result_summary.csv"), eval_metrics_in_summary)

        for task in self.tasks:
            task.to_directory(os.path.join(directory, "readable", task.qid))

    def to_csv(self, path: str, eval_metrics: list[str] = []) -> None:
        summaries = [task.to_summary(eval_metrics) for task in self.tasks]
        df = pd.DataFrame([summary.data() for summary in summaries], columns=summaries[0].fields())
        df.to_csv(path, index=False)


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
    name_description: str | None = None
    """Used for describing the merged table name in the compressed schema (e.g. "YYYYMMDD from 20200101 to 20200102")"""
    original_names: list[str] | None = None
    """Used for recording the original table names in the compressed schema (e.g. "20200101, 20200102")"""
    schema_name: str | None = None
    description: str | None = None
    is_view: bool
    columns: list[SQLColumnSchema]
    primary_key: list[str]
    num_rows: int
    foreign_keys: list[ForeignKeySchema]


class SQLSchema(BaseModel):
    name: str
    tables: list[SQLTableSchema]


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
