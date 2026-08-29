"""Human-readable reports and persisted outputs for research results."""

import logging
import os
from collections.abc import Sequence
from typing import Any, Literal, get_args

import pandas as pd

from tabulaflow.agents.trace import Trajectory
from tabulaflow.core import ColumnRef
from tabulaflow.output.formatting import format_exec_result_markdown
from tabulaflow.research.types import (
    CSVSummaryRow,
    DbtTask,
    DbtTaskOutput,
    FlatAmbigNL2QTaskOutput,
    GoldQuery,
    NL2QRunResult,
    NL2QTask,
    NL2QTaskOutput,
    PredQuery,
    SimpleAmbigNL2QTaskOutput,
    SimpleNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
)

logger = logging.getLogger(__name__)


def dict_to_df(
    data: dict[str, dict[str, Any]],
    column_level: Literal["outer", "inner"] = "outer",
    add_total_column: bool = True,
    add_total_row: bool = True,
    total_column_only: bool = False,
) -> pd.DataFrame:
    """Convert a nested result mapping to a table with optional totals."""
    if not data:
        return pd.DataFrame()
    outer_keys = list(data)
    inner_keys = list(data[outer_keys[0]])
    if not all(set(inner_keys) == set(data[outer]) for outer in outer_keys):
        raise ValueError("All inner keys must be the same.")
    if column_level == "inner":
        transposed = {inner: {outer: data[outer][inner] for outer in outer_keys} for inner in inner_keys}
        return dict_to_df(transposed, "outer", add_total_column, add_total_row, total_column_only)
    df = pd.DataFrame(
        [[data[column][row] for column in outer_keys] for row in inner_keys],
        columns=outer_keys,
        index=inner_keys,
    )
    if add_total_row:
        df.loc["Total"] = df.sum(axis=0)
    if add_total_column:
        df.loc[:, "Total"] = df.sum(axis=1)
    return df.loc[:, ["Total"]] if total_column_only and add_total_column else df


def query_to_directory(query: PredQuery | GoldQuery, directory: str) -> None:
    """Write a query's tabular execution results to ``directory``."""
    os.makedirs(directory, exist_ok=True)
    if query.exec_result is not None and query.exec_result.df is not None:
        query.exec_result.df.to_csv(os.path.join(directory, f"{query.id}.csv"), index=False)
    if isinstance(query, GoldQuery):
        for i, exec_result in enumerate(query.alternative_results):
            if exec_result.df is not None:
                exec_result.df.to_csv(os.path.join(directory, f"{query.id}_alternative_{i}.csv"), index=False)


def pred_query_to_markdown(query: PredQuery, heading_level: int = 2) -> str:
    """Render a predicted query and its execution result as Markdown."""
    heading = "#" * heading_level
    lines = [f"{heading} Pred Query", "\n```sql", query.query, "```"]
    if query.exec_result is not None:
        lines.extend(["\n**Execution Result:**\n", format_exec_result_markdown(query.exec_result)])
    return "\n".join(lines)


def gold_query_to_markdown(query: GoldQuery, heading_level: int = 2) -> str:
    """Render a gold query and its accepted execution results as Markdown."""
    heading = "#" * heading_level
    lines = [f"{heading} Gold Query"]
    if query.query:
        lines.extend(["\n```sql", query.query, "```"])
    if query.exec_result is not None:
        lines.extend(["\n**Execution Result:**\n", format_exec_result_markdown(query.exec_result)])
    for i, exec_result in enumerate(query.alternative_results):
        lines.extend([f"\n**Alt Result {i}:**\n", format_exec_result_markdown(exec_result)])
    return "\n".join(lines)


def _get_query_fields(task: NL2QTask | NL2QTaskOutput, query_type: type[GoldQuery] | type[PredQuery]) -> list[str]:
    fields = []
    for key, value in type(task).model_fields.items():
        if value.annotation == query_type or query_type in get_args(value.annotation):
            fields.append(key)
    return fields


def _save_trajectories(trajectory: Trajectory | list[Trajectory], directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    trajectories = trajectory if isinstance(trajectory, list) else [trajectory]
    ids = [tr.id for tr in trajectories]
    if len(ids) != len(set(ids)):
        logger.warning(f"Trajectory IDs are not unique: {ids}, some trajectories will be overwritten")
    for tr in trajectories:
        with open(os.path.join(directory, f"{tr.id}.md"), "w") as f:
            f.write(tr.to_markdown())


def task_to_directory(task: NL2QTask | NL2QTaskOutput, directory: str) -> None:
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


def task_to_markdown(task: NL2QTask | NL2QTaskOutput, heading_level: int = 1) -> str:
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


def task_to_summary(task: NL2QTask | NL2QTaskOutput, eval_metrics: Sequence[str] = ()) -> CSVSummaryRow:
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


def _dbt_task_to_summary(task: DbtTask | DbtTaskOutput, eval_metrics: Sequence[str] = ()) -> CSVSummaryRow:
    return CSVSummaryRow(
        qid=task.qid,
        db=task.db,
        question=task.question,
        metrics={m: getattr(task, "eval_metrics", {}).get(m) for m in eval_metrics},
    )


def run_result_to_directory(
    result: NL2QRunResult, directory: str, eval_metrics_in_summary: Sequence[str] | None = None
) -> None:
    """Persist a run result, summary CSV, and readable task reports."""
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "result.json"), "w") as file:
        file.write(result.model_dump_json(indent=2))
    run_result_to_csv(result, os.path.join(directory, "result_summary.csv"), eval_metrics_in_summary)
    for task in result.tasks:
        task_to_directory(task, os.path.join(directory, "readable", task.qid))


def run_result_to_csv(result: NL2QRunResult, path: str, eval_metrics: Sequence[str] | None = None) -> None:
    """Write one summary row per task in a run result."""
    metric_names = list(eval_metrics or ())
    summaries = [task_to_summary(task, metric_names) for task in result.tasks]
    columns = summaries[0].fields() if summaries else list(CSVSummaryRow.model_fields)[:-1] + metric_names
    df = pd.DataFrame([summary.data() for summary in summaries], columns=columns)
    df.to_csv(path, index=False)
