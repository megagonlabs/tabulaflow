import datetime
from enum import Enum
import os
import re
from pydantic import BaseModel, Field, model_validator, AfterValidator, ConfigDict
from pydantic.types import StringConstraints
from typing import TYPE_CHECKING, Any, Literal, Annotated, Protocol, TypeAlias, Union, get_args, overload
import pandas as pd
import logging
import math
import itertools
from tabulaflow.agents.trace import Trajectory, Usage
from tabulaflow.core import ColumnRef, ExecResult, SQLSchema

if TYPE_CHECKING:
    from tabulaflow.agents.tools.run_query import QueryExecution

logger = logging.getLogger(__name__)

NumericOrNull: TypeAlias = Union[float, int, None]


class PredQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = "PQRY"
    query: str
    parameter_names: list[str] = Field(default_factory=list)
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    exec_result: ExecResult | None = None

    @classmethod
    def from_execution(cls, execution: "QueryExecution") -> "PredQuery":
        return cls(
            query=execution.query,
            parameter_names=list(execution.parameter_values),
            parameter_values=execution.parameter_values,
            exec_result=execution.exec_result,
        )

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        if self.exec_result is not None and self.exec_result.df is not None:
            self.exec_result.df.to_csv(os.path.join(directory, f"{self.id}.csv"), index=False)

    def to_markdown(self, heading_level: int = 2) -> str:
        from tabulaflow.output.formatting import format_exec_result_markdown

        h = "#" * heading_level
        lines = [f"{h} Pred Query", "\n```sql", self.query, "```"]
        if self.exec_result is not None:
            lines.extend(["\n**Execution Result:**\n", format_exec_result_markdown(self.exec_result)])
        return "\n".join(lines)


def is_id_unique(objs: list[Any]) -> list[Any]:
    ids = [obj.id for obj in objs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"IDs of {type(objs[0]).__name__} are not unique.")
    return objs


class GoldQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = "GQRY"
    query: str | None
    """In Spider2, some gold queries are not available, so we allow it to be None"""
    parameter_names: list[str] = Field(default_factory=list)
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    """If `parameter_names` is not empty and `parameter_values` is empty, the query is parameterized."""
    exec_result: ExecResult | None = None
    required_columns: list[int] | None = None
    """Columns that must be present in the result, None means all columns must be present"""
    required_sorted: bool = False
    """True if row order matters"""
    alternative_results: list[ExecResult] = Field(default_factory=list)
    """Alternative correct results, used in spider2-snow"""
    extra_info: dict[str, Any] = Field(default_factory=dict)

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        if self.exec_result is not None and self.exec_result.df is not None:
            self.exec_result.df.to_csv(os.path.join(directory, f"{self.id}.csv"), index=False)
        for i, exec_result in enumerate(self.alternative_results):
            if exec_result.df is not None:
                exec_result.df.to_csv(os.path.join(directory, f"{self.id}_alternative_{i}.csv"), index=False)

    def to_markdown(self, heading_level: int = 2) -> str:
        from tabulaflow.output.formatting import format_exec_result_markdown

        h = "#" * heading_level
        lines = [f"{h} Gold Query"]
        if self.query:
            lines.append("\n```sql")
            lines.append(self.query)
            lines.append("```")
        if self.exec_result is not None:
            lines.append("\n**Execution Result:**\n")
            lines.append(format_exec_result_markdown(self.exec_result))
        for i, exec_result in enumerate(self.alternative_results):
            lines.append(f"\n**Alt Result {i}:**\n")
            lines.append(format_exec_result_markdown(exec_result))
        return "\n".join(lines)


class CSVSummaryRow(BaseModel):
    qid: str
    db: str
    question: str
    question_instructions: str | None = None
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
    db: str
    question: str
    question_instructions: str | None = None
    """Instructions that apply to this question only."""
    dataset_instructions: str | None = None
    """Instructions (e.g. for formatting) that apply to all questions in the dataset."""
    document: str | None = None
    gold_query: GoldQuery
    extra_info: dict[str, Any] = {}

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)


class ExtraPredInfo(BaseModel):
    linked_schema: list[ColumnRef] | None = None
    raw_pred_query: PredQuery | None = None
    """If your method includes a postprocessing step, this field can store the raw predicted query before postprocessing to analyze its impact. The raw_pred_*_ex metrics evaluate these raw predictions."""
    other: dict[str, Any] = Field(default_factory=dict)


class SimpleNL2QTaskOutput(SimpleNL2QTask):
    output_type: Literal["simple"] = "simple"
    pred_query: PredQuery | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""
    extra_pred_info: ExtraPredInfo = Field(default_factory=ExtraPredInfo)

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return _task_to_summary(self, eval_metrics)


class ARCSAmbiguityType(str, Enum):
    semantic_column = "semantic_column"
    semantic_table = "semantic_table"
    semantic_value = "semantic_value"
    semantic_computation = "semantic_computation"
    syntactic_column = "syntactic_column"
    syntactic_table = "syntactic_table"
    syntactic_value = "syntactic_value"
    syntactic_computation = "syntactic_computation"


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
    parameter_name: str
    parameter_dtype: Literal["int", "float", "str"]
    parameter_sample_operators: list[Literal["<", ">", "<=", ">=", "=", "<>"]]
    parameter_sample_values: list[Any]
    intended_parameter_operator: Literal["<", ">", "<=", ">=", "=", "<>"]
    intended_parameter_value: Any | None


GoldAmbiguityPoint = Annotated[Union[GoldAmbiguityPointFinite, GoldAmbiguityPointInfinite], Field(discriminator="type")]


class AmbigNL2QTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    qid: str
    task_type: Literal["ambig"] = "ambig"
    has_intended_resolution: bool
    db: str
    question: str
    dataset_instructions: str | None = None
    """Instructions (e.g. for formatting) that apply to all questions in the dataset"""
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

    @property
    def gold_finite_ambiguity_points(self) -> list[GoldAmbiguityPointFinite]:
        return [ap for ap in self.gold_ambiguity_points if ap.type == "finite"]

    @property
    def gold_infinite_ambiguity_points(self) -> list[GoldAmbiguityPointInfinite]:
        return [ap for ap in self.gold_ambiguity_points if ap.type == "infinite"]

    @property
    def gold_num_interpretation_comb(self) -> int:
        return math.prod(len(ap.interpretations) for ap in self.gold_finite_ambiguity_points)

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

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
                ap.intended_parameter_value is not None for ap in self.gold_ambiguity_points if ap.type == "infinite"
            )
        else:
            assert self.gold_intended_query_id is None
            assert all(
                ap.intended_interpretation_idx is None for ap in self.gold_ambiguity_points if ap.type == "finite"
            )
            assert all(
                ap.intended_parameter_value is None for ap in self.gold_ambiguity_points if ap.type == "infinite"
            )
        return self

    @model_validator(mode="after")
    def validate_id_reference(self) -> "AmbigNL2QTask":
        gold_query_ids = set(gq.id for gq in self.gold_queries)
        assert self.gold_intended_query_id is None or self.gold_intended_query_id in gold_query_ids
        return self


class SimpleAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model only predicts the final disambiguated query
    """

    output_type: Literal["ambig-simple"] = "ambig-simple"
    pred_intended_query: PredQuery | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usage: Usage | None = None
    user_simulator_usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""
    extra_pred_info: ExtraPredInfo = Field(default_factory=ExtraPredInfo)

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return _task_to_summary(self, eval_metrics)


class PredAmbiguityPointFinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["finite"] = "finite"
    interpretations: list[str]
    intended_interpretation_idx: int | None = None
    rejected_by_user: bool = False


class PredAmbiguityPointInfinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["infinite"] = "infinite"
    parameter_name: str
    parameter_dtype: Literal["int", "float", "str"]
    parameter_description: str | None = None
    parameter_sample_operators: list[Literal["<", ">", "<=", ">=", "=", "<>"]]
    parameter_sample_values: list[Any] | list[list[Any]]
    intended_parameter_operator: Literal["<", ">", "<=", ">=", "=", "<>"] | None = None
    intended_parameter_value: Any | None = None
    rejected_by_user: bool = False


PredAmbiguityPoint = Annotated[Union[PredAmbiguityPointFinite, PredAmbiguityPointInfinite], Field(discriminator="type")]


class FlatAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model predicts a list of interpretations, the SQL for each interpretation, and the final disambiguated query
    (e.g. the "Disambiguate First Parse Later" paper https://arxiv.org/pdf/2502.18448)
    """

    output_type: Literal["ambig-flat"] = "ambig-flat"
    interpretations: list[str]
    parameters: list[PredAmbiguityPointInfinite]
    pred_queries: Annotated[list[PredQuery], AfterValidator(is_id_unique)]
    pred_intended_query_id: str | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usage: Usage | None = None
    user_simulator_usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""
    extra_pred_info: ExtraPredInfo = Field(default_factory=ExtraPredInfo)

    # @model_validator(mode="after")
    # def validate_interpretations(self) -> "FlatAmbigNL2QTaskOutput":
    #     assert len(self.interpretations) == len(self.pred_queries)
    #     return self

    @property
    def pred_intended_query(self) -> PredQuery | None:
        if self.pred_intended_query_id is None:
            return None
        id_to_query = {pq.id: pq for pq in self.pred_queries}
        return id_to_query[self.pred_intended_query_id]

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return _task_to_summary(self, eval_metrics)


class StructuredAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model predicts all the ambiguity points, their interpretations, the SQL for each interpretation combination, as well as the final disambiguated query
    """

    output_type: Literal["ambig-structured"] = "ambig-structured"
    pred_ambiguity_points: Annotated[list[PredAmbiguityPoint], AfterValidator(is_id_unique)]
    pred_queries: Annotated[list[PredQuery], AfterValidator(is_id_unique)]
    pred_intended_query_id: str | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usage: Usage | None = None
    user_simulator_usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""
    extra_pred_info: ExtraPredInfo = Field(default_factory=ExtraPredInfo)

    @property
    def pred_intended_query(self) -> PredQuery | None:
        if self.pred_intended_query_id is None:
            return None
        id_to_query = {pq.id: pq for pq in self.pred_queries}
        return id_to_query[self.pred_intended_query_id]

    @property
    def pred_finite_ambiguity_points(self) -> list[PredAmbiguityPointFinite]:
        return [ap for ap in self.pred_ambiguity_points if ap.type == "finite"]

    @property
    def pred_infinite_ambiguity_points(self) -> list[PredAmbiguityPointInfinite]:
        return [ap for ap in self.pred_ambiguity_points if ap.type == "infinite"]

    @property
    def pred_num_interpretation_comb(self) -> int:
        return math.prod(len(ap.interpretations) for ap in self.pred_finite_ambiguity_points)

    @model_validator(mode="after")
    def validate_pred_queries(self) -> "StructuredAmbigNL2QTaskOutput":
        # Pred query ID must match the pattern "PQRY(-[A-Z]+\.[0-9]+)*" (e.g. "PQRY-A.2-B.0")
        pattern = r"^PQRY(-[A-Z]+\.[0-9]+)*$"
        assert all(re.match(pattern, pq.id) for pq in self.pred_queries)

        if not self.pred_ambiguity_points:
            assert len(self.pred_queries) == 0 or len(self.pred_queries) == 1
            return self

        # finite_aps = sorted([ap for ap in self.pred_ambiguity_points if ap.type == "finite"], key=lambda x: x.id)
        # required_ids = [
        #     "PQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, indexes))
        #     for indexes in itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps])
        # ]
        # pred_query_ids = set(pq.id for pq in self.pred_queries)
        # for pq_id in pred_query_ids:
        #     if pq_id not in required_ids:
        #         raise ValueError(f"qid {self.qid}: Pred query {pq_id} is not required.")
        # for required_id in required_ids:
        #     if required_id not in pred_query_ids:
        #         raise ValueError(f"qid {self.qid}: Pred query {required_id} is not found.")
        # assert len(self.pred_queries) == len(required_ids) == math.prod(len(ap.interpretations) for ap in finite_aps)
        return self

    @model_validator(mode="after")
    def validate_pred_id_reference(self) -> "StructuredAmbigNL2QTaskOutput":
        pred_query_ids = set(pq.id for pq in self.pred_queries)
        assert self.pred_intended_query_id is None or self.pred_intended_query_id in pred_query_ids
        return self

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return _task_to_summary(self, eval_metrics)


class DbtGoldTable(BaseModel):
    """An expected output table for dbt evaluation."""

    table_name: str
    required_columns: list[int] = Field(default_factory=list)
    """Column indices to compare. Empty means all columns."""
    required_sorted: bool = False
    """True if row order matters."""


class DbtTask(BaseModel):
    """A dbt data-transformation task."""

    task_type: Literal["dbt"] = "dbt"
    qid: str
    db: str
    """Instance ID (e.g. ``"zuora001"``), maps to a DuckDB connector for the project's source database."""
    question: str
    """Natural-language instruction describing the transformation to build."""
    question_instructions: str | None = None
    """Instructions that apply to this question only."""
    dataset_instructions: str | None = None
    """Instructions (e.g. for formatting) that apply to all questions in the dataset."""
    project_dir: str
    """Relative path to the original dbt project directory (e.g. ``"data/Spider2/spider2-dbt/examples/zuora001"``)."""
    working_dir: str | None = None
    """Relative path to the working copy of the project, set by the pipeline before the agent runs (e.g. ``"output/exp123/working/zuora001"``)."""
    gold_db_path: str | None = None
    """Relative path to the gold ``.duckdb`` file for evaluation."""
    gold_tables: list[DbtGoldTable]
    """Tables to compare in evaluation, from the evaluation spec."""
    extra_info: dict[str, Any] = Field(default_factory=dict)

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)


class DbtTaskOutput(DbtTask):
    """Output of a dbt agent."""

    output_type: Literal["dbt"] = "dbt"
    pred_db_path: str | None = None
    """Relative path to the predicted DuckDB file produced by the agent (e.g. ``"output/exp123/working/zuora001/zuora.duckdb"``)."""
    pred_db_schema: SQLSchema | None = None
    """Schema of the predicted database after ``dbt run``, including any tables/views created by the agent."""
    pred_model_files: dict[str, str] = Field(default_factory=dict)
    """Maps path relative to ``working_dir`` (e.g. ``"models/my_model.sql"``) to file content."""
    dbt_run_success: bool | None = None
    dbt_run_log: str | None = None
    trajectory: Trajectory | list[Trajectory] | None = None
    usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation."""
    extra_pred_info: ExtraPredInfo = Field(default_factory=ExtraPredInfo)
    """Not used for dbt tasks. Present for compatibility with the NL2QTaskOutput union."""

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return _task_to_summary(self, eval_metrics)


NL2QTask = Annotated[Union[SimpleNL2QTask, AmbigNL2QTask, DbtTask], Field(discriminator="task_type")]
NL2QTaskOutput = Annotated[
    Union[
        SimpleNL2QTaskOutput,
        SimpleAmbigNL2QTaskOutput,
        FlatAmbigNL2QTaskOutput,
        StructuredAmbigNL2QTaskOutput,
        DbtTaskOutput,
    ],
    Field(discriminator="output_type"),
]


def _get_query_fields(task: NL2QTask | NL2QTaskOutput, t: TypeAlias) -> list[str]:
    res = []
    for key, value in type(task).model_fields.items():
        if value.annotation == t or t in get_args(value.annotation):
            res.append(key)
    return res


def _save_trajectories(trajectory: Trajectory | list[Trajectory], directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    trajectories = trajectory if isinstance(trajectory, list) else [trajectory]
    ids = [tr.id for tr in trajectories]
    if len(ids) != len(set(ids)):
        logger.warning(f"Trajectory IDs are not unique: {ids}, some trajectories will be overwritten")
    for tr in trajectories:
        with open(os.path.join(directory, f"{tr.id}.md"), "w") as f:
            f.write(tr.to_markdown())


def _task_to_directory(task: NL2QTask | NL2QTaskOutput, directory: str) -> None:
    if isinstance(task, (DbtTask, DbtTaskOutput)):
        return _dbt_task_to_directory(task, directory)

    os.makedirs(directory, exist_ok=True)
    for prefix in ["gold", "pred"]:
        for field in _get_query_fields(task, GoldQuery if prefix == "gold" else PredQuery):
            queries = getattr(task, field)
            if not isinstance(queries, list):
                queries = [queries]
            for q in queries:
                if q is not None:
                    q.to_directory(os.path.join(directory, f"{prefix}_csv"))
    with open(os.path.join(directory, "task_readable.md"), "w") as f:
        f.write(task.to_markdown())
    trajectory = getattr(task, "trajectory", None)
    if trajectory is not None:
        _save_trajectories(trajectory, os.path.join(directory, "trajectory"))


def _task_to_markdown(task: NL2QTask | NL2QTaskOutput, heading_level: int = 1) -> str:
    """Convert task to a concise, human-readable markdown format.

    Args:
        task: The task to convert.
        heading_level: The base heading level (1 for #, 2 for ##, 3 for ###, etc.)
    """
    if isinstance(task, (DbtTask, DbtTaskOutput)):
        return _dbt_task_to_markdown(task, heading_level)

    h1 = "#" * heading_level
    h2 = "#" * (heading_level + 1)
    lines = [f"{h1} Task: {task.qid}", ""]

    # Basic info
    lines.append(f"**Database:** {task.db}  ")
    lines.append("")

    # Question
    lines.append(f"{h2} Question")
    lines.append(task.question)

    # Question instructions
    question_instructions = getattr(task, "question_instructions", None)
    if question_instructions:
        lines.append(f"\n**Question Instructions:** {question_instructions}")

    # Document
    document = getattr(task, "document", None)
    if document:
        lines.append(f"\n{h2} Document")
        lines.append(f"````\n{document}\n````")

    def _quote(s: str) -> str:
        return f'"{s}"' if " " in s else s

    def _format_column_name(col: ColumnRef) -> str:
        res = f"{_quote(col.table_name)}.{_quote(col.column_name)}"
        if col.schema_name:
            res = f"{_quote(col.schema_name)}.{res}"
        return res

    if isinstance(
        task, (SimpleNL2QTaskOutput, SimpleAmbigNL2QTaskOutput, FlatAmbigNL2QTaskOutput, StructuredAmbigNL2QTaskOutput)
    ):
        # Linked schema
        linked_schema = task.extra_pred_info.linked_schema
        if linked_schema:
            lines.append(f"\n{h2} Linked Schema")
            lines.append(f"\n```\n{', '.join([_format_column_name(col) for col in linked_schema])}\n```")

        # Raw pred query
        raw_pred_query = task.extra_pred_info.raw_pred_query
        if raw_pred_query:
            lines.append(
                "\n\n"
                + raw_pred_query.to_markdown(heading_level=heading_level + 1).replace(
                    "# Pred Query", "# Raw Pred Query"
                )
            )

        # Pred queries
        pred_query = task.pred_intended_query if task.task_type == "ambig" else task.pred_query
        if pred_query is not None:
            lines.append("\n\n" + pred_query.to_markdown(heading_level=heading_level + 1))
        else:
            lines.append(f"\n\n{h2} Pred Query\n\nN/A")

    # Gold queries
    gold_query = task.gold_intended_query if task.task_type == "ambig" else task.gold_query
    if gold_query is not None:
        lines.append("\n\n" + gold_query.to_markdown(heading_level=heading_level + 1))
    else:
        lines.append(f"\n\n{h2} Gold Query\n\nN/A")

    # Metrics
    eval_metrics = getattr(task, "eval_metrics", None)
    if eval_metrics:
        lines.append(f"\n{h2} Evaluation Metrics")
        for key, value in eval_metrics.items():
            lines.append(f"- **{key}:** {value}")

    inference_metrics = getattr(task, "inference_metrics", None)
    if inference_metrics:
        lines.append(f"\n{h2} Inference Metrics")
        for key, value in inference_metrics.items():
            lines.append(f"- **{key}:** {value}")

    # Usage
    usage = getattr(task, "usage", None)
    if usage:
        lines.append(f"\n{h2} Usage")
        lines.append(f"- **API Requests:** {usage.api_requests}")
        lines.append(f"- **Input Tokens:** {usage.input_tokens}")
        lines.append(f"- **Output Tokens:** {usage.output_tokens}")
        lines.append(f"- **Cost:** ${round(float(usage.api_cost_usd), 4)}")

    return "\n".join(lines)


def _task_to_summary(task: NL2QTask | NL2QTaskOutput, eval_metrics: list[str] = []) -> CSVSummaryRow:
    if isinstance(task, (DbtTask, DbtTaskOutput)):
        return _dbt_task_to_summary(task, eval_metrics)

    gold_query_field = "gold_query" if task.task_type == "simple" else "gold_intended_query"
    gold_query = getattr(task, gold_query_field, None)
    pred_query_field = "pred_query" if task.task_type == "simple" else "pred_intended_query"
    pred_query = getattr(task, pred_query_field, None)
    return CSVSummaryRow(
        qid=task.qid,
        db=task.db,
        question=task.question,
        question_instructions=getattr(task, "question_instructions", None),
        gold_query=gold_query.query if gold_query else None,
        pred_query=pred_query.query if pred_query else None,
        gold_exec_result=gold_query.exec_result.to_markdown() if gold_query and gold_query.exec_result else None,
        pred_exec_result=pred_query.exec_result.to_markdown() if pred_query and pred_query.exec_result else None,
        metrics={m: getattr(task, "eval_metrics", {}).get(m) for m in eval_metrics},
    )


def _dbt_task_to_directory(task: DbtTask | DbtTaskOutput, directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "task_readable.md"), "w") as f:
        f.write(task.to_markdown())
    trajectory = getattr(task, "trajectory", None)
    if trajectory is not None:
        _save_trajectories(trajectory, os.path.join(directory, "trajectory"))
    pred_model_files: dict[str, str] = getattr(task, "pred_model_files", {})
    if pred_model_files:
        models_dir = os.path.join(directory, "pred_models")
        os.makedirs(models_dir, exist_ok=True)
        for rel_path, content in pred_model_files.items():
            out_path = os.path.join(models_dir, rel_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w") as f:
                f.write(content)


def _dbt_task_to_markdown(task: DbtTask | DbtTaskOutput, heading_level: int = 1) -> str:
    h1 = "#" * heading_level
    h2 = "#" * (heading_level + 1)
    lines = [f"{h1} Task: {task.qid}", ""]

    lines.append(f"**Project:** {task.db}  ")
    lines.append(f"**Project Dir:** `{task.project_dir}`  ")
    working_dir = getattr(task, "working_dir", None)
    if working_dir:
        lines.append(f"**Working Dir:** `{working_dir}`  ")
    lines.append("")

    lines.append(f"{h2} Instruction")
    lines.append(task.question)

    # Gold tables
    if task.gold_tables:
        lines.append(f"\n{h2} Gold Tables")
        for gt in task.gold_tables:
            cols = ", ".join(str(c) for c in gt.required_columns) if gt.required_columns else "all"
            lines.append(f"- **{gt.table_name}** (cols: {cols}, sorted: {gt.required_sorted})")

    if task.gold_db_path:
        lines.append(f"\n**Gold DB:** `{task.gold_db_path}`")

    # Predicted model files (output only)
    pred_model_files: dict[str, str] = getattr(task, "pred_model_files", {})
    if pred_model_files:
        lines.append(f"\n{h2} Predicted Model Files")
        for rel_path, content in pred_model_files.items():
            lines.append(f"\n**`{rel_path}`**\n")
            lines.append(f"```sql\n{content}\n```")

    # dbt run status
    dbt_run_success = getattr(task, "dbt_run_success", None)
    if dbt_run_success is not None:
        lines.append(f"\n{h2} dbt run")
        lines.append(f"**Success:** {dbt_run_success}")
        dbt_run_log = getattr(task, "dbt_run_log", None)
        if dbt_run_log:
            lines.append(f"\n```\n{dbt_run_log}\n```")

    # Eval metrics
    eval_metrics = getattr(task, "eval_metrics", None)
    if eval_metrics:
        lines.append(f"\n{h2} Evaluation Metrics")
        for key, value in eval_metrics.items():
            lines.append(f"- **{key}:** {value}")

    # Inference metrics
    inference_metrics = getattr(task, "inference_metrics", None)
    if inference_metrics:
        lines.append(f"\n{h2} Inference Metrics")
        for key, value in inference_metrics.items():
            lines.append(f"- **{key}:** {value}")

    # Usage
    usage = getattr(task, "usage", None)
    if usage:
        lines.append(f"\n{h2} Usage")
        lines.append(f"- **API Requests:** {usage.api_requests}")
        lines.append(f"- **Input Tokens:** {usage.input_tokens}")
        lines.append(f"- **Output Tokens:** {usage.output_tokens}")
        lines.append(f"- **Cost:** ${round(float(usage.api_cost_usd), 4)}")

    return "\n".join(lines)


def _dbt_task_to_summary(task: DbtTask | DbtTaskOutput, eval_metrics: list[str] = []) -> CSVSummaryRow:
    return CSVSummaryRow(
        qid=task.qid,
        db=task.db,
        question=task.question,
        metrics={m: getattr(task, "eval_metrics", {}).get(m) for m in eval_metrics},
    )


class NL2QDataset(BaseModel):
    name: str
    split: str
    databases: list[str] | None = None  # None means all databases
    subsample_size: int | None = None
    dataset_extra_kwargs: dict[str, Any] = Field(default_factory=dict)
    tasks: list[NL2QTask]
    db_connectors: dict[str, Any]

    @model_validator(mode="after")
    def validate_qid_uniqueness(self) -> "NL2QDataset":
        qids = [task.qid for task in self.tasks]
        if len(qids) != len(set(qids)):
            raise ValueError(f"QIDs are not unique: {qids}")
        return self


class NL2QRunResult(BaseModel):
    start_time: datetime.datetime
    end_time: datetime.datetime
    dataset: str
    split: str
    databases: list[str] | None  # None means all databases
    subsample_size: int | None
    dataset_extra_kwargs: dict[str, Any] = Field(default_factory=dict)
    agent: str
    agent_config: dict[str, Any]
    total_usage: Usage | None = None
    """Total usage of the agent, does not include user simulator usage"""
    total_user_simulator_usage: Usage | None = None
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


# ---------------------------------------------------------------------------
# User interaction types
# ---------------------------------------------------------------------------


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
    answer_free_text: str


class UserMultipleChoiceAnswer(BaseModel):
    answer_index: int


class UserValueAnswer(BaseModel):
    operator: Literal["<", ">", "<=", ">=", "=", "<>"]
    value: int | float | str


UserQuestion: TypeAlias = Annotated[
    Union[UserFreeTextQuestion, UserMultipleChoiceQuestion, UserValueQuestion], Field(discriminator="type")
]
UserAnswer: TypeAlias = Union[UserFreeTextAnswer, UserMultipleChoiceAnswer, UserValueAnswer]


class UserSimulatorProtocol(Protocol):
    @overload
    async def ask_async(self, question: UserFreeTextQuestion) -> UserFreeTextAnswer | None: ...
    @overload
    async def ask_async(self, question: UserMultipleChoiceQuestion) -> UserMultipleChoiceAnswer | None: ...
    @overload
    async def ask_async(self, question: UserValueQuestion) -> UserValueAnswer | None: ...

    async def ask_async(self, question: UserQuestion) -> UserAnswer | None: ...

    def usage(self) -> Usage: ...

    def trajectory(self) -> Trajectory: ...

    def user_effort(self) -> float: ...
