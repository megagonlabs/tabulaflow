import argparse
import asyncio
import os
import jinja2
from tqdm.asyncio import tqdm_asyncio
from pydantic import BaseModel
from pydantic_ai import Agent
import random
from typing import Any
from mintq.schema import NL2QTaskOutput, NL2QRunResult, PredQuery, Usage, SimpleNL2QTaskOutput
from mintq.metrics import NL2QMetric


async def compute_metrics_async(task: NL2QTaskOutput, metrics: list[NL2QMetric]) -> NL2QTaskOutput:
    results = await asyncio.gather(*[m.compute_async(task) for m in metrics])  # type: ignore
    task.eval_metrics = {}
    for m, r in zip(metrics, results):
        if isinstance(r, dict):
            task.eval_metrics.update(r)
        else:
            task.eval_metrics[m.name] = r
    return task


class ErrorTaskReport(BaseModel):
    qid: str
    question: str
    db: str
    question_instructions: str | None
    gold: Any
    pred: Any | None
    report: str
    usage: Usage
    eval_metrics: dict[str, Any]

    def to_markdown(self) -> str:
        res = f"### `{self.qid}`\n\n"
        res += f"**Question:** {self.question}\n\n"
        res += f"**Gold:**\n```sql\n{self.gold.query}\n```\n\n"
        if self.gold.exec_result:
            res += f"**Gold Exec Result:**\n```\n{self.gold.exec_result.to_readable()}\n```\n\n"
        pred_query = self.pred.query if self.pred else "(prediction failed, no prediction available)"
        res += f"**Pred:**\n```sql\n{pred_query}\n```\n\n"
        if self.pred and self.pred.exec_result:
            res += f"**Pred Exec Result:**\n```\n{self.pred.exec_result.to_readable()}\n```\n\n"
        res += f"**Report:** {self.report}\n"
        return res


class ErrorReport(BaseModel):
    aggregated_report: str
    task_reports: list[ErrorTaskReport]
    usage: Usage

    def to_markdown(self) -> str:
        res = f"# Error Analysis Summary\n\n{self.aggregated_report}\n\n"
        res += f"## Error Tasks ({len(self.task_reports)})\n\n"
        res += "\n".join([task.to_markdown() for task in self.task_reports])
        return res


ANALYZE_TASK_PROMPT = """
You are responsible for analyzing the errors in the following task.
- The output should a 1-3 sentence concise report on the sources of the error.

=== START OF PREDICTION ===
{{pred_str}}
=== END OF PREDICTION ===

=== START OF GROUND TRUTH ===
{{gold_str}}
=== END OF GROUND TRUTH ===
""".strip()


SUMMARY_PROMPT = """
You are responsible for summarizing the following error reports.
- The output should include all major error categories.

=== START OF ERROR TASK REPORTS ===
{% for task_report in task_reports %}
QID: {{ task_report.qid }}
{{ task_report.report }}
{% endfor %}
=== END OF ERROR TASK REPORTS ===
""".strip()


async def analyze_task_async(task: NL2QTaskOutput, llm: str = "openai-responses:gpt-5") -> ErrorTaskReport:
    if task.output_type == "simple":
        gold_str = task.gold_query.to_readable()
        pred_str = task.pred_query.to_readable() if task.pred_query else "(prediction failed, no prediction available)"
        propmt = jinja2.Template(ANALYZE_TASK_PROMPT).render(gold_str=gold_str, pred_str=pred_str)
        result = await Agent(llm).run(propmt)
        report = result.output
        usage = Usage.from_pydantic_ai_usage(result.usage(), llm)
        return ErrorTaskReport(
            qid=task.qid,
            question=task.question,
            db=task.db,
            question_instructions=getattr(task, "question_instructions", None),
            gold=task.gold_query,
            pred=task.pred_query,
            report=report,
            eval_metrics=task.eval_metrics,
            usage=usage,
        )
    else:
        raise NotImplementedError(f"Error analysis for {task.output_type} tasks is not implemented.")


async def analyze_errors_async(
    result: NL2QRunResult,
    llm: str = "openai-responses:gpt-5",
    error_metric_name: str = "simple_ex",
    num_samples: int = 100,
    batch_size: int = 50,
    verbose: bool = True,
) -> ErrorReport:
    error_tasks = [task for task in result.tasks if task.eval_metrics[error_metric_name] == 0.0]

    if not error_tasks:
        if verbose:
            print("No error tasks found.")
        return ErrorReport(task_reports=[], aggregated_report="No error tasks found.", usage=Usage.create(llm))
    error_tasks = random.Random(42).sample(error_tasks, min(num_samples, len(error_tasks)))
    task_reports = []
    for i in range(0, len(error_tasks), batch_size):
        j = min(i + batch_size, len(error_tasks))
        batch = error_tasks[i:j]
        batch_reports = await tqdm_asyncio.gather(
            *[analyze_task_async(task, llm) for task in batch], disable=not verbose
        )
        task_reports += batch_reports
        if verbose:
            print(f"{j}/{len(error_tasks)} error tasks analyzed.")
    prompt = jinja2.Template(SUMMARY_PROMPT).render(task_reports=task_reports)
    aggregated_report = await Agent(llm).run(prompt)

    usage = Usage.from_pydantic_ai_usage(aggregated_report.usage(), llm)
    for task_report in task_reports:
        usage += task_report.usage
    return ErrorReport(task_reports=task_reports, aggregated_report=aggregated_report.output, usage=usage)


class PostprocessingTaskDetail(BaseModel):
    qid: str
    db: str
    question: str
    question_instructions: str | None
    before_query: str | None
    before_exec_result: str | None
    after_query: str | None
    after_exec_result: str | None
    gold_query: str | None
    gold_exec_result: str | None


class PostprocessingImpactReport(BaseModel):
    """Report on how postprocessing affected execution correctness (EX) scores."""

    total_tasks: int
    improved: list[PostprocessingTaskDetail]  # EX: 0 → 1 (postprocessing fixed a failing task)
    regressed_not_executable: list[PostprocessingTaskDetail]  # postprocessing made query non-executable
    regressed_columns_added: list[PostprocessingTaskDetail]  # postprocessing added extra columns
    regressed_other: list[PostprocessingTaskDetail]  # other regression causes
    potential_improvable: list[PostprocessingTaskDetail]  # tasks that could be improved by postprocessing

    def to_markdown(self) -> str:
        n_improved = len(self.improved)
        n_regressed = len(self.regressed_not_executable) + len(self.regressed_columns_added) + len(self.regressed_other)
        total = self.total_tasks

        def pct(count: int) -> str:
            return f"{count / total * 100:.1f}%" if total > 0 else "0.0%"

        res = "# Postprocessing Impact Summary\n\n"
        res += f"- Total tasks: {self.total_tasks}\n"
        res += f"- Net impact: {n_improved - n_regressed:+d} ({pct(n_improved - n_regressed)})\n"
        res += f"- Improved (0→1): {n_improved} ({pct(n_improved)})\n"
        res += f"- Regressed (1→0): {n_regressed} ({pct(n_regressed)})\n"
        res += f"- Potential improvable: {len(self.potential_improvable)} ({pct(len(self.potential_improvable))})\n"
        res += "\n"
        res += "## Regression Breakdown\n\n"
        res += f"- Became not executable: {len(self.regressed_not_executable)} ({pct(len(self.regressed_not_executable))})\n"
        res += (
            f"- Extra columns added: {len(self.regressed_columns_added)} ({pct(len(self.regressed_columns_added))})\n"
        )
        res += f"- Other causes: {len(self.regressed_other)} ({pct(len(self.regressed_other))})\n"

        def render_task_list(title: str, tasks: list[PostprocessingTaskDetail]) -> str:
            if not tasks:
                return ""
            section = f"\n## {title}\n\n"
            for task in tasks:
                section += f"### `{task.qid}`\n\n"
                section += f"**Question:** {task.question}\n\n"
                section += f"**Question Instructions:** {task.question_instructions}\n\n"
                section += f"**DB:** {task.db}\n\n"
                section += "**Gold Query:**\n```sql\n" + (task.gold_query or "N/A") + "\n```\n\n"
                if task.gold_exec_result:
                    section += "**Gold Exec Result:**\n```\n" + task.gold_exec_result + "\n```\n\n"
                section += "**Before Postprocessing:**\n```sql\n" + (task.before_query or "N/A") + "\n```\n\n"
                if task.before_exec_result:
                    section += "**Before Exec Result:**\n```\n" + task.before_exec_result + "\n```\n\n"
                section += "**After Postprocessing:**\n```sql\n" + (task.after_query or "N/A") + "\n```\n\n"
                if task.after_exec_result:
                    section += "**After Exec Result:**\n```\n" + task.after_exec_result + "\n```\n\n"
            return section

        res += render_task_list(f"Improved Tasks ({n_improved})", self.improved)
        res += render_task_list(
            f"Regressed: Not Executable ({len(self.regressed_not_executable)})", self.regressed_not_executable
        )
        res += render_task_list(
            f"Regressed: Extra Columns Added ({len(self.regressed_columns_added)})", self.regressed_columns_added
        )
        res += render_task_list(f"Regressed: Other ({len(self.regressed_other)})", self.regressed_other)
        res += render_task_list(f"Potential Improvable ({len(self.potential_improvable)})", self.potential_improvable)

        return res


async def analyze_postprocess_impact_async(
    result: NL2QRunResult,
    pre_metric: str = "raw_pred_bird_sql_ex",
    post_metric: str = "bird_sql_ex",
    target_metric: str = "simple_ex",
) -> PostprocessingImpactReport:
    """
    Analyze how postprocessing affected execution correctness (EX) scores.

    Args:
        result: The run result containing task outputs with eval metrics.
        pre_metric: Metric name for EX before postprocessing.
        post_metric: Metric name for EX after postprocessing.

    Returns:
        A structured report of postprocessing impact.
    """
    if not all(task.output_type == "simple" for task in result.tasks):
        raise ValueError("Only simple tasks are supported for now.")

    tasks_by_qid = {task.qid: task for task in result.tasks}

    def make_detail(task: NL2QTaskOutput) -> PostprocessingTaskDetail:
        if task.output_type != "simple":
            raise ValueError(f"Only simple tasks are supported for now. Got {task.output_type}.")

        raw_pred_query = PredQuery.model_validate(task.extra_info["raw_pred_query"])
        return PostprocessingTaskDetail(
            qid=task.qid,
            db=task.db,
            question=task.question,
            question_instructions=task.question_instructions,
            before_query=raw_pred_query.query,
            before_exec_result=raw_pred_query.exec_result.to_readable() if raw_pred_query.exec_result else None,
            after_query=task.pred_query.query if task.pred_query else None,
            after_exec_result=task.pred_query.exec_result.to_readable() if task.pred_query and task.pred_query.exec_result else None,
            gold_query=task.gold_query.query if task.gold_query else None,
            gold_exec_result=task.gold_query.exec_result.to_readable() if task.gold_query and task.gold_query.exec_result else None,
        )

    improved: list[PostprocessingTaskDetail] = [
        make_detail(task)
        for task in result.tasks
        if task.eval_metrics[pre_metric] == 0.0 and task.eval_metrics[post_metric] == 1.0
    ]

    regressed_qids = [
        task.qid
        for task in result.tasks
        if task.eval_metrics[pre_metric] == 1.0 and task.eval_metrics[post_metric] == 0.0
    ]
    potential_improvable = [
        make_detail(task)
        for task in result.tasks
        if task.eval_metrics[pre_metric] == task.eval_metrics[post_metric] == 0.0
        and task.eval_metrics[target_metric] == 1.0
    ]

    # Analyze regression causes
    became_not_executable: list[PostprocessingTaskDetail] = []
    columns_added: list[PostprocessingTaskDetail] = []
    other: list[PostprocessingTaskDetail] = []

    for qid in regressed_qids:
        task: SimpleNL2QTaskOutput = tasks_by_qid[qid]  # type: ignore
        raw_pred_query = PredQuery.model_validate(task.extra_info["raw_pred_query"])
        detail = make_detail(task)

        if task.pred_query is None or task.pred_query.exec_result.df is None:  # type: ignore
            became_not_executable.append(detail)
            continue

        num_columns_before = len(raw_pred_query.exec_result.df.columns)  # type: ignore
        num_columns_after = len(task.pred_query.exec_result.df.columns)  # type: ignore
        if num_columns_after > num_columns_before:
            columns_added.append(detail)
            continue

        other.append(detail)

    return PostprocessingImpactReport(
        total_tasks=len(result.tasks),
        improved=improved,
        regressed_not_executable=became_not_executable,
        regressed_columns_added=columns_added,
        regressed_other=other,
        potential_improvable=potential_improvable,
    )


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--batch_size", type=int, default=50)
    parser.add_argument("--num_samples", type=int, default=100)
    parser.add_argument("--llm", default="openai-responses:gpt-5")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--error_metric_name", default="simple_ex")
    args = parser.parse_args()
    print(args)
    print()

    with open(os.path.join(args.result_dir, "result.json"), "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    if not all(task.output_type == "simple" for task in result.tasks):
        raise ValueError("Only simple tasks are supported for now.")

    if any("raw_pred_query" in task.extra_info for task in result.tasks):
        print()
        print("Analyzing postprocess impact...")
        postprocess_impact_report = await analyze_postprocess_impact_async(result)
        with open(os.path.join(args.result_dir, "postprocess_impact_report.md"), "w") as f:
            f.write(postprocess_impact_report.to_markdown())
        print(f"Saved postprocess impact report to {os.path.join(args.result_dir, 'postprocess_impact_report.md')}")

    print()
    print("Analyzing errors...")
    error_report = await analyze_errors_async(
        result, args.llm, args.error_metric_name, args.num_samples, args.batch_size
    )
    with open(os.path.join(args.result_dir, "error_report.md"), "w") as f:
        f.write(error_report.to_markdown())
    print(f"Total cost USD: {error_report.usage.api_cost_usd:.6f}")
    print(f"Saved error report to {os.path.join(args.result_dir, 'error_report.md')}")


if __name__ == "__main__":
    asyncio.run(main_async())
