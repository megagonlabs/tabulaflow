import argparse
import asyncio
import os
import jinja2
from tqdm.asyncio import tqdm_asyncio
from pydantic import BaseModel
from pydantic_ai import Agent
import random
from typing import Any
from mintq.schema import NL2QTaskOutput, NL2QRunResult, Usage
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

    def to_readable(self) -> str:
        res = f"===== START OF ERROR TASK `{self.qid}` =====\n\n"
        res += f"Question: {self.question}\n\n"
        res += f"Gold:\n{self.gold.to_readable()}\n\n"
        res += f"Pred:\n{self.pred.to_readable() if self.pred else '(prediction failed, no prediction available)'}\n\n"
        res += f"Report:\n{self.report}\n\n"
        res += f"===== END OF ERROR TASK `{self.qid}` ====="
        return res


class ErrorReport(BaseModel):
    aggregated_report: str
    task_reports: list[ErrorTaskReport]
    usage: Usage

    def to_readable(self) -> str:
        res = f"=== START OF SUMMARY ===\n\n{self.aggregated_report}\n\n=== END OF SUMMARY ===\n\n\n"
        res += "\n\n\n".join([task.to_readable() for task in self.task_reports])
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
    # error_tasks = [task for task in result.tasks if task.eval_metrics[error_metric_name] == 0.0]
    error_tasks = [
        task
        for task in result.tasks
        if task.eval_metrics["bird_sql_ex"] == 0.0 and task.eval_metrics["simple_ex"] == 1.0
    ]
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

    error_report = await analyze_errors_async(
        result, args.llm, args.error_metric_name, args.num_samples, args.batch_size
    )
    print(f"Total cost USD: {error_report.usage.api_cost_usd:.6f}")

    with open(os.path.join(args.result_dir, "error_report.txt"), "w") as f:
        f.write(error_report.to_readable())
    print(f"Saved error report to {os.path.join(args.result_dir, 'error_report.txt')}")


if __name__ == "__main__":
    asyncio.run(main_async())
