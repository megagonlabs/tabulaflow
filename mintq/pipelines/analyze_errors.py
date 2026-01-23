import argparse
import asyncio
import os
from tqdm.asyncio import tqdm_asyncio
from pydantic import BaseModel
from mintq.schema import NL2QTaskOutput, NL2QRunResult, Usage, SimpleNL2QTaskOutput
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


class TaskErrorAnalysis(BaseModel):
    task_output: NL2QTaskOutput
    llm_analysis: str
    analysis_usage: Usage

    def to_markdown(self) -> str:
        res = self.task_output.to_markdown()
        if self.llm_analysis:
            res += f"\n\n## LLM Analysis\n\n{self.llm_analysis}"
        return res


class ErrorAnalysis(BaseModel):
    """Aggregated error analysis report."""

    task_analyses: list[TaskErrorAnalysis]
    analysis_summary: str
    total_analysis_usage: Usage

    def to_markdown(self) -> str:
        res = f"# Error Analysis Summary\n\n{self.analysis_summary}"
        res += f"\n\n<br>\n<br>\n\n# All Task Analyses ({len(self.task_analyses)})\n\n"
        res += "\n\n".join([task.to_markdown() for task in self.task_analyses])
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


async def analyze_task_async(task: NL2QTaskOutput, llm: str = "openai-responses:gpt-5") -> TaskErrorAnalysis:
    """Analyze a single error task and generate a report."""
    # gold_str = task.gold_query.to_markdown()
    # pred_str = task.pred_query.to_markdown() if task.pred_query else "(prediction failed)"
    # propmt = jinja2.Template(ANALYZE_TASK_PROMPT).render(gold_str=gold_str, pred_str=pred_str)
    # result = await Agent(llm).run(propmt)
    # report = result.output
    # usage = Usage.from_pydantic_ai_usage(result.usage(), llm)
    report = ""
    usage = Usage.create(llm)

    return TaskErrorAnalysis(task_output=task, llm_analysis=report, analysis_usage=usage)


async def analyze_errors_async(
    result: NL2QRunResult,
    llm: str = "openai-responses:gpt-5",
    error_metric_name: str = "simple_ex",
    num_samples: int = 100,
    batch_size: int = 50,
    verbose: bool = True,
) -> ErrorAnalysis:
    error_tasks = [task for task in result.tasks if task.eval_metrics[error_metric_name] == 0.0]

    if not error_tasks:
        if verbose:
            print("No error tasks found.")
        return ErrorAnalysis(
            task_analyses=[], analysis_summary="No error tasks found.", total_analysis_usage=Usage.create(llm)
        )
    # error_tasks = random.Random(42).sample(error_tasks, min(num_samples, len(error_tasks)))
    task_analyses: list[TaskErrorAnalysis] = []
    for i in range(0, len(error_tasks), batch_size):
        j = min(i + batch_size, len(error_tasks))
        batch = error_tasks[i:j]
        batch_analyses = await tqdm_asyncio.gather(
            *[analyze_task_async(task, llm) for task in batch], disable=not verbose
        )
        task_analyses += batch_analyses
        if verbose:
            print(f"{j}/{len(error_tasks)} error tasks analyzed.")
    # prompt = jinja2.Template(SUMMARY_PROMPT).render(task_analyses=task_analyses)
    # result = await Agent(llm).run(prompt)
    # analysis_summary = result.output

    # total_usage = Usage.from_pydantic_ai_usage(result.usage(), llm)
    # for task_analysis in task_analyses:
    #     total_usage += task_analysis.analysis_usage
    total_usage = Usage.create(llm)
    analysis_summary = ""

    return ErrorAnalysis(
        task_analyses=task_analyses, analysis_summary=analysis_summary, total_analysis_usage=total_usage
    )


# =============================================================================
# Postprocessing Impact Analysis
# =============================================================================


class TaskPostprocessingAnalysis(BaseModel):
    task_output: NL2QTaskOutput

    def to_markdown(self) -> str:
        res = self.task_output.to_markdown()
        raw_pred_query = self.task_output.extra_pred_info.raw_pred_query

        res = res.split("\n## Evaluation Metrics")[0]
        res += "\n\n## Raw Predicted Query (Before Postprocessing)\n\n"
        if raw_pred_query is not None:
            res += raw_pred_query.to_markdown()
        else:
            res += "N/A"
        return res


class PostprocessingAnalysis(BaseModel):
    """Analysis on how postprocessing affected execution correctness (EX) scores."""

    task_analyses: list[TaskPostprocessingAnalysis]
    improved_qids: list[str]
    regressed_qids: list[str]
    regressed_not_executable_qids: list[str]
    regressed_columns_added_qids: list[str]
    regressed_other_qids: list[str]
    potential_improvable_qids: list[str]

    def to_markdown(self) -> str:
        n_improved = len(self.improved_qids)
        n_regressed = (
            len(self.regressed_not_executable_qids)
            + len(self.regressed_columns_added_qids)
            + len(self.regressed_other_qids)
        )
        total = len(self.task_analyses)

        def pct(count: int) -> str:
            return f"{count / total * 100:.1f}%" if total > 0 else "0.0%"

        res = "# Postprocessing Impact Summary\n\n"
        res += f"- Total tasks: {total}\n"
        res += f"- Net impact: {n_improved - n_regressed:+d} ({pct(n_improved - n_regressed)})\n"
        res += f"- Improved (0→1): {n_improved} ({pct(n_improved)})\n"
        res += f"- Regressed (1→0): {n_regressed} ({pct(n_regressed)})\n"
        res += f"  - Became not executable: {len(self.regressed_not_executable_qids)} ({pct(len(self.regressed_not_executable_qids))})\n"
        res += f"  - Extra columns added: {len(self.regressed_columns_added_qids)} ({pct(len(self.regressed_columns_added_qids))})\n"
        res += f"  - Other causes: {len(self.regressed_other_qids)} ({pct(len(self.regressed_other_qids))})\n"
        res += f"- Potential improvable: {len(self.potential_improvable_qids)} ({pct(len(self.potential_improvable_qids))})"

        res += f"\n\n<br>\n<br>\n\n# All Task Analyses ({len(self.task_analyses)})\n\n"
        res += "\n\n".join([task.to_markdown() for task in self.task_analyses])
        return res


async def analyze_postprocess_impact_async(
    result: NL2QRunResult,
    pre_metric: str = "raw_pred_bird_sql_ex",
    post_metric: str = "bird_sql_ex",
    target_metric: str = "simple_ex",
) -> PostprocessingAnalysis:
    """
    Analyze how postprocessing affected execution correctness (EX) scores.

    Args:
        result: The run result containing task outputs with eval metrics.
        pre_metric: Metric name for EX before postprocessing.
        post_metric: Metric name for EX after postprocessing.
        target_metric: Metric name for target correctness (used for potential improvable).

    Returns:
        A structured report of postprocessing impact.
    """
    if not all(task.output_type == "simple" for task in result.tasks):
        raise ValueError("Only simple tasks are supported for now.")

    tasks_by_qid = {task.qid: task for task in result.tasks}

    # Build task analyses for all tasks
    task_analyses = [TaskPostprocessingAnalysis(task_output=task) for task in result.tasks]

    improved_qids = [
        task.qid
        for task in result.tasks
        if task.eval_metrics[pre_metric] == 0.0 and task.eval_metrics[post_metric] == 1.0
    ]

    regressed_qids = [
        task.qid
        for task in result.tasks
        if task.eval_metrics[pre_metric] == 1.0 and task.eval_metrics[post_metric] == 0.0
    ]

    potential_improvable_qids = [
        task.qid
        for task in result.tasks
        if task.eval_metrics[pre_metric] == task.eval_metrics[post_metric] == 0.0
        and task.eval_metrics[target_metric] == 1.0
    ]

    # Analyze regression causes
    regressed_not_executable_qids: list[str] = []
    regressed_columns_added_qids: list[str] = []
    regressed_other_qids: list[str] = []

    for qid in regressed_qids:
        task: SimpleNL2QTaskOutput = tasks_by_qid[qid]  # type: ignore
        raw_pred_query = task.extra_pred_info.raw_pred_query

        if task.pred_query is None or task.pred_query.exec_result.df is None:  # type: ignore
            regressed_not_executable_qids.append(qid)
            continue

        num_columns_before = len(raw_pred_query.exec_result.df.columns)  # type: ignore
        num_columns_after = len(task.pred_query.exec_result.df.columns)  # type: ignore
        if num_columns_after > num_columns_before:
            regressed_columns_added_qids.append(qid)
            continue

        regressed_other_qids.append(qid)

    return PostprocessingAnalysis(
        task_analyses=task_analyses,
        improved_qids=improved_qids,
        regressed_qids=regressed_qids,
        regressed_not_executable_qids=regressed_not_executable_qids,
        regressed_columns_added_qids=regressed_columns_added_qids,
        regressed_other_qids=regressed_other_qids,
        potential_improvable_qids=potential_improvable_qids,
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

    if any(task.extra_pred_info.raw_pred_query is not None for task in result.tasks):
        print()
        print("Analyzing postprocess impact...")
        postprocess_analysis = await analyze_postprocess_impact_async(result)
        with open(os.path.join(args.result_dir, "postprocess_impact_report.md"), "w") as f:
            f.write(postprocess_analysis.to_markdown())
        print(f"Saved postprocess impact report to {os.path.join(args.result_dir, 'postprocess_impact_report.md')}")

    print()
    print("Analyzing errors...")
    error_analysis = await analyze_errors_async(
        result, args.llm, args.error_metric_name, args.num_samples, args.batch_size
    )
    with open(os.path.join(args.result_dir, "error_report.md"), "w") as f:
        f.write(error_analysis.to_markdown())
    print(f"Total cost USD: {error_analysis.total_analysis_usage.api_cost_usd:.6f}")
    print(f"Saved error report to {os.path.join(args.result_dir, 'error_report.md')}")


if __name__ == "__main__":
    asyncio.run(main_async())
