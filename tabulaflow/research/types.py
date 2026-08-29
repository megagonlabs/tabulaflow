"""Data models for research queries, tasks, datasets, and experiment results."""

import datetime
import itertools
import math
import re
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Annotated, Protocol, TypeAlias, Union, overload

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator
from pydantic.types import StringConstraints

from tabulaflow.agents.trace import Trajectory, Usage
from tabulaflow.core import ColumnRef, ExecResult, SQLSchema

if TYPE_CHECKING:
    from tabulaflow.agents.tools.run_query import QueryExecution

NumericOrNull: TypeAlias = Union[float, int, None]


class PredQuery(BaseModel):
    """A query predicted by a research agent, optionally with its execution result."""

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
        from tabulaflow.research.reporting import query_to_directory

        query_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 2) -> str:
        from tabulaflow.research.reporting import pred_query_to_markdown

        return pred_query_to_markdown(self, heading_level)


def is_id_unique(objs: list[Any]) -> list[Any]:
    ids = [obj.id for obj in objs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"IDs of {type(objs[0]).__name__} are not unique.")
    return objs


class GoldQuery(BaseModel):
    """A reference query and accepted result variants for benchmark evaluation."""

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
        from tabulaflow.research.reporting import query_to_directory

        query_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 2) -> str:
        from tabulaflow.research.reporting import gold_query_to_markdown

        return gold_query_to_markdown(self, heading_level)


class CSVSummaryRow(BaseModel):
    """One flattened task row in an experiment summary CSV."""

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
    """An unambiguous natural-language-to-query benchmark task."""

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
    extra_info: dict[str, Any] = Field(default_factory=dict)

    def to_directory(self, directory: str) -> None:
        from tabulaflow.research.reporting import task_to_directory

        task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        from tabulaflow.research.reporting import task_to_markdown

        return task_to_markdown(self, heading_level)


class ExtraPredInfo(BaseModel):
    """Optional intermediate artifacts produced while predicting a query."""

    linked_schema: list[ColumnRef] | None = None
    raw_pred_query: PredQuery | None = None
    """If your method includes a postprocessing step, this field can store the raw predicted query before postprocessing to analyze its impact. The raw_pred_*_ex metrics evaluate these raw predictions."""
    other: dict[str, Any] = Field(default_factory=dict)


class SimpleNL2QTaskOutput(SimpleNL2QTask):
    """Prediction and run metadata for a simple task."""

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
        from tabulaflow.research.reporting import task_to_directory

        task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        from tabulaflow.research.reporting import task_to_markdown

        return task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: Sequence[str] = ()) -> CSVSummaryRow:
        from tabulaflow.research.reporting import task_to_summary

        return task_to_summary(self, eval_metrics)


class ARCSAmbiguityType(str, Enum):
    """ARCS ambiguity taxonomy labels."""

    semantic_column = "semantic_column"
    semantic_table = "semantic_table"
    semantic_value = "semantic_value"
    semantic_computation = "semantic_computation"
    syntactic_column = "syntactic_column"
    syntactic_table = "syntactic_table"
    syntactic_value = "syntactic_value"
    syntactic_computation = "syntactic_computation"


class GoldAmbiguityPointFinite(BaseModel):
    """A finite ambiguity with an enumerated set of interpretations."""

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
    """An open-ended ambiguity represented by a typed query parameter."""

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
    """A benchmark task with explicit ambiguity points and resolution queries."""

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
        from tabulaflow.research.reporting import task_to_directory

        task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        from tabulaflow.research.reporting import task_to_markdown

        return task_to_markdown(self, heading_level)

    @model_validator(mode="after")
    def validate_gold_queries(self) -> "AmbigNL2QTask":
        # Gold query ID must match the pattern "GQRY(-[A-Z]+\.[0-9]+)*" (e.g. "GQRY-A.2-B.0")
        pattern = r"^GQRY(-[A-Z]+\.[0-9]+)*$"
        if not all(re.match(pattern, gq.id) for gq in self.gold_queries):
            raise ValueError(f"qid {self.qid}: invalid gold query id")

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
        return self

    @model_validator(mode="after")
    def validate_has_intended_resolution(self) -> "AmbigNL2QTask":
        if self.has_intended_resolution:
            if self.gold_intended_query_id is None:
                raise ValueError("gold_intended_query_id is required when has_intended_resolution is true")
            if not all(
                ap.intended_interpretation_idx is not None for ap in self.gold_ambiguity_points if ap.type == "finite"
            ):
                raise ValueError("finite ambiguity points require an intended interpretation")
            if not all(
                ap.intended_parameter_value is not None for ap in self.gold_ambiguity_points if ap.type == "infinite"
            ):
                raise ValueError("infinite ambiguity points require an intended parameter value")
        else:
            if self.gold_intended_query_id is not None:
                raise ValueError("gold_intended_query_id requires has_intended_resolution")
            if not all(
                ap.intended_interpretation_idx is None for ap in self.gold_ambiguity_points if ap.type == "finite"
            ):
                raise ValueError("finite ambiguity points cannot have an intended interpretation")
            if not all(
                ap.intended_parameter_value is None for ap in self.gold_ambiguity_points if ap.type == "infinite"
            ):
                raise ValueError("infinite ambiguity points cannot have an intended parameter value")
        return self

    @model_validator(mode="after")
    def validate_id_reference(self) -> "AmbigNL2QTask":
        gold_query_ids = set(gq.id for gq in self.gold_queries)
        if self.gold_intended_query_id is not None and self.gold_intended_query_id not in gold_query_ids:
            raise ValueError(f"gold query {self.gold_intended_query_id!r} does not exist")
        return self


class SimpleAmbigNL2QTaskOutput(AmbigNL2QTask):
    """An ambiguity-aware prediction containing only the resolved final query."""

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
        from tabulaflow.research.reporting import task_to_directory

        task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        from tabulaflow.research.reporting import task_to_markdown

        return task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: Sequence[str] = ()) -> CSVSummaryRow:
        from tabulaflow.research.reporting import task_to_summary

        return task_to_summary(self, eval_metrics)


class PredAmbiguityPointFinite(BaseModel):
    """A predicted finite ambiguity and its candidate interpretations."""

    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["finite"] = "finite"
    interpretations: list[str]
    intended_interpretation_idx: int | None = None
    rejected_by_user: bool = False


class PredAmbiguityPointInfinite(BaseModel):
    """A predicted open-ended ambiguity represented by a typed parameter."""

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
    """Flat interpretations, their queries, and the resolved final query."""

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

    @property
    def pred_intended_query(self) -> PredQuery | None:
        if self.pred_intended_query_id is None:
            return None
        id_to_query = {pq.id: pq for pq in self.pred_queries}
        return id_to_query[self.pred_intended_query_id]

    def to_directory(self, directory: str) -> None:
        from tabulaflow.research.reporting import task_to_directory

        task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        from tabulaflow.research.reporting import task_to_markdown

        return task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: Sequence[str] = ()) -> CSVSummaryRow:
        from tabulaflow.research.reporting import task_to_summary

        return task_to_summary(self, eval_metrics)


class StructuredAmbigNL2QTaskOutput(AmbigNL2QTask):
    """Predicted ambiguity structure, interpretation queries, and final resolution."""

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
        if not all(re.match(pattern, pq.id) for pq in self.pred_queries):
            raise ValueError(f"qid {self.qid}: invalid predicted query id")

        if not self.pred_ambiguity_points and len(self.pred_queries) > 1:
            raise ValueError("at most one predicted query is allowed without predicted ambiguity points")
        if not self.pred_ambiguity_points:
            return self
        return self

    @model_validator(mode="after")
    def validate_pred_id_reference(self) -> "StructuredAmbigNL2QTaskOutput":
        pred_query_ids = set(pq.id for pq in self.pred_queries)
        if self.pred_intended_query_id is not None and self.pred_intended_query_id not in pred_query_ids:
            raise ValueError(f"predicted query {self.pred_intended_query_id!r} does not exist")
        return self

    def to_directory(self, directory: str) -> None:
        from tabulaflow.research.reporting import task_to_directory

        task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        from tabulaflow.research.reporting import task_to_markdown

        return task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: Sequence[str] = ()) -> CSVSummaryRow:
        from tabulaflow.research.reporting import task_to_summary

        return task_to_summary(self, eval_metrics)


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
        from tabulaflow.research.reporting import task_to_directory

        task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        from tabulaflow.research.reporting import task_to_markdown

        return task_to_markdown(self, heading_level)


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
        from tabulaflow.research.reporting import task_to_directory

        task_to_directory(self, directory)

    def to_markdown(self, heading_level: int = 1) -> str:
        from tabulaflow.research.reporting import task_to_markdown

        return task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: Sequence[str] = ()) -> CSVSummaryRow:
        from tabulaflow.research.reporting import task_to_summary

        return task_to_summary(self, eval_metrics)


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


class NL2QDataset(BaseModel):
    """A benchmark split with tasks and connectors keyed by database name."""

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
    """Configuration, outputs, usage, and aggregate metrics for one experiment run."""

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

    def to_directory(self, directory: str, eval_metrics_in_summary: Sequence[str] = ()) -> None:
        from tabulaflow.research.reporting import run_result_to_directory

        run_result_to_directory(self, directory, eval_metrics_in_summary)

    def to_csv(self, path: str, eval_metrics: Sequence[str] = ()) -> None:
        from tabulaflow.research.reporting import run_result_to_csv

        run_result_to_csv(self, path, eval_metrics)


# ---------------------------------------------------------------------------
# User interaction types
# ---------------------------------------------------------------------------


class UserFreeTextQuestion(BaseModel):
    """A clarification question answered with free text."""

    type: Literal["free_text"] = "free_text"
    question: str


class UserMultipleChoiceQuestion(BaseModel):
    """A clarification question answered by selecting one option."""

    type: Literal["multiple_choice"] = "multiple_choice"
    question: str
    options: list[str]


class UserValueQuestion(BaseModel):
    """A clarification question answered with a typed comparison value."""

    type: Literal["value"] = "value"
    question: str
    value_dtype: Literal["int", "float", "str"]
    value_operator_options: list[Literal["<", ">", "<=", ">=", "=", "<>"]]


class UserFreeTextAnswer(BaseModel):
    """Free-text clarification answer."""

    answer_free_text: str


class UserMultipleChoiceAnswer(BaseModel):
    """Selected option index for a multiple-choice clarification."""

    answer_index: int


class UserValueAnswer(BaseModel):
    """Comparison operator and value supplied for a clarification."""

    operator: Literal["<", ">", "<=", ">=", "=", "<>"]
    value: int | float | str


UserQuestion: TypeAlias = Annotated[
    Union[UserFreeTextQuestion, UserMultipleChoiceQuestion, UserValueQuestion], Field(discriminator="type")
]
UserAnswer: TypeAlias = Union[UserFreeTextAnswer, UserMultipleChoiceAnswer, UserValueAnswer]


class UserSimulatorProtocol(Protocol):
    """Interface used by ambiguity-aware agents to request clarifications."""

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
