import argparse
import asyncio
import os
import copy
import json
from typing import Literal
from pydantic import BaseModel, Field
import jinja2
from pydantic_ai import Agent
from mintq.schema import NL2QRunResult, Usage, NL2QTaskOutput


class ErrorCategory(BaseModel):
    name: str
    description: str
    qids: list[str] = Field(default_factory=list)


CLASSIFICATION_PROMPT = """
You are responsible for classifying the task characteristics and prediction errors in the following task.
- The output should include be a list of categories that apply to the task.
  - If there are no applicable categories, return an empty list.
- For each category, identify whether it applies based on the relevant information.
  - Some categories may be determined from the question, the prediction, the gold query, or a combination of these elements.

<categories>
{{categories}}
</categories>

<task_and_output>
{{task_and_output}}
</task_and_output>
""".strip()


DEFAULT_CATEGORIES = [
    ErrorCategory(
        name="task_has_AND_ambiguity_interpreted_as_LOGICAL_AND",
        description="""
The task question contains the word "and" that can be interpreted as either a logical AND or a UNION, and the gold query follows the logical AND interpretation.
Applicable regardless of prediction and evaluation metrics.
Example:
    Question: "students with ML and NLP papers", the gold query selects students with both ML and NLP papers.
""".strip(),
    ),
    ErrorCategory(
        name="task_has_AND_ambiguity_interpreted_as_UNION",
        description="""
The task question contains the word "and" that can be interpreted as either a logical AND or a UNION, and the gold query follows the UNION interpretation.
Applicable regardless of prediction and evaluation metrics.
Example:
    Question: "students with ML and NLP papers", the gold query selects students with either ML or NLP papers.
""".strip(),
    ),
    ErrorCategory(
        name="pred_query_uses_non_sqlite_syntax",
        description="""
The predicted query uses a SQL syntax or a function that is not supported by SQLite, leading to different execution results from the gold query.
Only applicable if bird_sql_ex = 0.0.
""".strip(),
    ),
    ErrorCategory(
        name="error_due_to_task_ambiguity",
        description="""
The error is due to task ambiguity. Both prediction and gold query are valid interpretations of the question.
Only applicable if bird_sql_ex = 0.0.
""".strip(),
    ),
]


class LLMErrorClassifier:
    def __init__(self, llm: str = "openai-responses:gpt-5-mini", categories: list[ErrorCategory] = DEFAULT_CATEGORIES):
        self.llm = llm
        self.categories = categories
        self._usage = Usage.create(llm)

    def usage(self) -> Usage:
        return self._usage

    async def _classify_task_async(self, task: NL2QTaskOutput) -> list[str]:
        prompt = jinja2.Template(CLASSIFICATION_PROMPT).render(
            task_and_output=task.to_markdown(),
            categories=json.dumps([{"name": c.name, "description": c.description} for c in self.categories], indent=2),
        )

        output_type = Literal[tuple(c.name for c in self.categories)]
        agent = Agent[None, list[output_type]](model=self.llm, output_type=list[output_type])
        result = await agent.run(prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
        return result.output

    async def classify_async(self, result: NL2QRunResult) -> list[ErrorCategory]:
        all_results = await asyncio.gather(*[self._classify_task_async(task) for task in result.tasks])
        categories = {category.name: copy.deepcopy(category) for category in self.categories}
        for task, task_categories in zip(result.tasks, all_results):
            for cate in task_categories:
                if cate not in categories:
                    continue
                categories[cate].qids.append(task.qid)
        return list(categories.values())


class Analyzer:
    def __init__(self, classifier_llm: str = "openai-responses:gpt-5-mini"):
        self.classifier_llm = classifier_llm
        self._usage = Usage.create(classifier_llm)

    def usage(self) -> Usage:
        return self._usage

    async def _error_categories_section(self, result: NL2QRunResult) -> str:
        llm_classifier = LLMErrorClassifier(llm=self.classifier_llm)
        categories = await llm_classifier.classify_async(result)
        self._usage += llm_classifier.usage()
        res = "## Error Categories"
        for category in categories:
            res += f"\n\n### {category.name}\n\n"
            res += f"{category.description}\n\n"
            if len(category.qids) > 0:
                res += "\n".join(f" [[{qid}]](./readable/{qid}/task_readable.md)" for qid in category.qids)
            else:
                res += "(No tasks in this category)"
        return res

    def _error_section(self, result: NL2QRunResult) -> str:
        res = "## Error Tasks"
        res += "\n\nTasks where simple_ex = 0.0:"
        error_tasks = [task for task in result.tasks if task.eval_metrics["simple_ex"] == 0.0]
        res += "\n\n" + "\n".join(f" [[{task.qid}]](./readable/{task.qid}/task_readable.md)" for task in error_tasks)
        return res

    def _schema_linking_section(self, result: NL2QRunResult) -> str:
        res = "## Schema Linking"
        res += "\n\nTasks where perfect_linked_schema_r = 0.0:"
        error_tasks = [task for task in result.tasks if task.eval_metrics["perfect_linked_schema_r"] == 0.0]
        res += "\n\n" + "\n".join(f" [[{task.qid}]](./readable/{task.qid}/task_readable.md)" for task in error_tasks)
        return res

    def _postprocess_impact_section(self, result: NL2QRunResult) -> str:
        qids: dict[str, list[str]] = {"Improved": [], "Regressed": [], "Potential Improvable": []}
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
        for key, qs in qids.items():
            res += f"\n\n### {key}\n\n"
            res += f"{descriptions[key]}:"
            res += "\n\n" + "\n".join(f" [[{q}]](./readable/{q}/task_readable.md)" for q in qs)
        return res

    def _num_tool_calls_section(self, result: NL2QRunResult) -> str:
        res = "## Tool Calls"
        res += "\n\n### Top 10 tasks with most run_query calls"
        num_calls = []
        for task in result.tasks:
            if "tools" in task.inference_metrics:
                num_calls.append((task.qid, task.inference_metrics["tools"]["run_query"]["num_calls"]))
        num_calls.sort(key=lambda x: x[1], reverse=True)
        for q, n in num_calls[:10]:
            res += f"\n\n[[{q}]](./readable/{q}/task_readable.md) - {n} run_query calls"
        return res

    async def analyze_async(self, result: NL2QRunResult) -> str:
        """Analyze the run result and return a markdown string containing the error analysis report."""
        sections = [
            await self._error_categories_section(result),
            self._error_section(result),
            self._num_tool_calls_section(result),
        ]
        if any(task.extra_pred_info.linked_schema is not None for task in result.tasks):
            sections.append(self._schema_linking_section(result))
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
    parser.add_argument("--classifier_llm", default="openai-responses:gpt-5-mini")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--error_metric_name", default="simple_ex")
    args = parser.parse_args()
    print(args)
    print()

    with open(os.path.join(args.result_dir, "result.json"), "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    if not all(task.output_type == "simple" for task in result.tasks):
        raise ValueError("Only simple tasks are supported for now.")

    analyzer = Analyzer(classifier_llm=args.classifier_llm)
    error_analysis = await analyzer.analyze_async(result)
    with open(os.path.join(args.result_dir, "analysis.md"), "w") as f:
        f.write(error_analysis)
    print(f"Total cost USD: {analyzer.usage().api_cost_usd:.6f}")
    print(f"Saved error report to {os.path.join(args.result_dir, 'analysis.md')}")


if __name__ == "__main__":
    asyncio.run(main_async())
