import argparse
import asyncio
import os
from tqdm.asyncio import tqdm_asyncio
from pydantic import BaseModel
from mintq.schema import NL2QTaskOutput, NL2QRunResult, Usage, SimpleNL2QTaskOutput


class Analyzer:
    def __init__(self, llm: str = "openai-responses:gpt-5"):
        self._usage = Usage.create(llm)

    def usage(self) -> Usage:
        return self._usage

    def _error_section(self, result: NL2QRunResult) -> str:
        res = "## Error Tasks"
        res += "\n\n### simple_ex = 0.0"
        error_tasks = [task for task in result.tasks if task.eval_metrics["simple_ex"] == 0.0]
        res += "\n\n" + "\n".join(f" [[{task.qid}]](./readable/{task.qid}/task_readable.md)" for task in error_tasks)
        return res

    def _postprocess_impact_section(self, result: NL2QRunResult) -> str:
        qids = {"Improved": [], "Regressed": [], "Potential Improvable": []}
        for task in result.tasks:
            if task.eval_metrics["raw_pred_bird_sql_ex"] == 0.0 and task.eval_metrics["bird_sql_ex"] == 1.0:
                qids["Improved"].append(task.qid)
            elif task.eval_metrics["raw_pred_bird_sql_ex"] == 1.0 and task.eval_metrics["bird_sql_ex"] == 0.0:
                qids["Regressed"].append(task.qid)
            elif task.eval_metrics["raw_pred_bird_sql_ex"] == task.eval_metrics["bird_sql_ex"] == 0.0 and (
                task.eval_metrics["raw_pred_simple_ex"] == 1.0 or task.eval_metrics["simple_ex"] == 1.0
            ):
                qids["Potential Improvable"].append(task.qid)

        descriptions = {
            "Improved": "Tasks where bird_sql_ex improved from 0.0 to 1.0",
            "Regressed": "Tasks where bird_sql_ex regressed from 1.0 to 0.0",
            "Potential Improvable": "Tasks where bird_sql_ex remains 0.0, but raw_pred_simple_ex or simple_ex is 1.0",
        }

        res = "## Postprocessing Impact"
        for key, qids in qids.items():
            res += f"\n\n### {key}\n\n"
            res += f"{descriptions[key]}:"
            res += "\n\n" + "\n".join(f" [[{qid}]](./readable/{qid}/task_readable.md)" for qid in qids)
        return res

    async def analyze_async(self, result: NL2QRunResult) -> str:
        """Analyze the run result and return a markdown string containing the error analysis report."""
        sections = [
            self._error_section(result),
        ]
        if any(task.extra_pred_info.raw_pred_query is not None for task in result.tasks):
            sections.append(self._postprocess_impact_section(result))
        res = "\n\n".join(sections)
        return res


# ANALYZE_TASK_PROMPT = """
# You are responsible for analyzing the errors in the following task.
# - The output should a 1-3 sentence concise report on the sources of the error.

# === START OF PREDICTION ===
# {{pred_str}}
# === END OF PREDICTION ===

# === START OF GROUND TRUTH ===
# {{gold_str}}
# === END OF GROUND TRUTH ===
# """.strip()


# SUMMARY_PROMPT = """
# You are responsible for summarizing the following error reports.
# - The output should include all major error categories.

# === START OF ERROR TASK REPORTS ===
# {% for task_report in task_reports %}
# QID: {{ task_report.qid }}
# {{ task_report.report }}
# {% endfor %}
# === END OF ERROR TASK REPORTS ===
# """.strip()


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

    analyzer = Analyzer(args.llm)
    error_analysis = await analyzer.analyze_async(result)
    with open(os.path.join(args.result_dir, "error_report.md"), "w") as f:
        f.write(error_analysis)
    print(f"Total cost USD: {analyzer.usage().api_cost_usd:.6f}")
    print(f"Saved error report to {os.path.join(args.result_dir, 'error_report.md')}")


if __name__ == "__main__":
    asyncio.run(main_async())
