import argparse
import asyncio
import os
import copy
import json
import time
from typing import Literal
from pydantic import BaseModel, Field
import jinja2
from pydantic_ai import Agent
import mintq
from mintq.schema import NL2QRunResult, Usage, NL2QTaskOutput
from mintq.pipelines.utils import bool_flag


class ErrorCategory(BaseModel):
    name: str
    description: str
    qids: list[str] = Field(default_factory=list)


CLASSIFICATION_PROMPT = """
You are responsible for classifying the task characteristics and prediction errors in the following task.
- The output should include be a list of categories that apply to the task.
  - If there are no applicable categories, return an empty list.
  - There can be multiple categories that apply to one task.
- For each category, identify whether it applies based on the relevant information.
  - Some categories may be determined from the question, the prediction, the gold query, or a combination of these elements.

<categories>
{{categories}}
</categories>

<task_and_output>
{{task_and_output}}
</task_and_output>
""".strip()


DEFAULT_CATEGORIES: list[ErrorCategory] = [
    #     ErrorCategory(
    #         name="task_has_AND_ambiguity_interpreted_as_LOGICAL_AND",
    #         description="""
    # The task question contains the word "and" that can be interpreted as either a logical AND or a UNION, and the gold query follows the logical AND interpretation.
    # Applicable regardless of prediction and evaluation metrics.
    # Example:
    #     Question: "students with ML and NLP papers", the gold query selects students with both ML and NLP papers.
    # """.strip(),
    #     ),
    #     ErrorCategory(
    #         name="task_has_AND_ambiguity_interpreted_as_UNION",
    #         description="""
    # The task question contains the word "and" that can be interpreted as either a logical AND or a UNION, and the gold query follows the UNION interpretation.
    # Applicable regardless of prediction and evaluation metrics.
    # Example:
    #     Question: "students with ML and NLP papers", the gold query selects students with either ML or NLP papers.
    # """.strip(),
    #     ),
    #     ErrorCategory(
    #         name="task_has_percentage_not_specified_not_multiply_by_100",
    #         description="""
    # The task question asks for a percentage value (excluding rates) **without specifying to multiply by 100**, the resulting value in the gold query is not multiplied by 100.
    # Applicable regardless of prediction and evaluation metrics.
    # """.strip(),
    #     ),
    #     ErrorCategory(
    #         name="task_has_percentage_not_specified_multiplied_by_100",
    #         description="""
    # The task question asks for a percentage value (excluding rates) **without specifying to multiply by 100**, the resulting value in the gold query is multiplied by 100.
    # Applicable regardless of prediction and evaluation metrics.
    # """.strip(),
    #     ),
    #     ErrorCategory(
    #         name="task_has_percentage_specified",
    #         description="""
    # The task question asks for a percentage value (excluding rates) and specifies to multiply by 100.
    # Applicable regardless of prediction and evaluation metrics.
    # """.strip(),
    #     ),
    # ErrorCategory(
    #     name="gold_query_columns_follow_question_mention_order",
    #     description="The SELECT columns in the gold query appear in the same order as they are mentioned in the question. Applicable regardless of prediction and evaluation metrics.",
    # ),
    # ErrorCategory(
    #     name="gold_query_columns_do_not_follow_question_mention_order",
    #     description="The SELECT columns in the gold query do not appear in the same order as they are mentioned in the question. Applicable regardless of prediction and evaluation metrics.",
    # ),
    # ErrorCategory(
    #     name="error_due_to_numeric_precision",
    #     description="The displayed predicted query execution results in the `## Pred Query` section are exactly the same as the gold query results (same shape and values). Only applicable if simple_ex = 1.0 and one other _ex metric is 0.0.",
    # ),
    # ErrorCategory(
    #     name="pred_query_uses_incorrect_syntax_or_function",
    #     description="""
    # The predicted query uses a syntax or a function that is not supported by corresponding DBMS or dialect, leading to different execution results from the gold query.
    # Only applicable if simple_ex = 0.0.
    # """.strip(),
    # ),
    # ErrorCategory(
    #     name="error_due_to_task_ambiguity",
    #     description="""
    # The error is due to task ambiguity. Both prediction and gold query are valid interpretations of the question.
    # Only applicable if simple_ex = 0.0.
    # """.strip(),
    # ),
    # ErrorCategory(
    #     name="error_due_to_incorrect_gold_query",
    #     description="""
    # The gold query is incorrect. The predicted query aligns better with the question than the gold query.
    # Only applicable if simple_ex = 0.0.
    # """.strip(),
    # ),
    # ErrorCategory(
    #     name="pred_is_correct",
    #     description="""
    # The predicted query is correct (spider2_ex = 1.0).
    # """.strip(),
    # ),
    # ErrorCategory(
    #     name="error_is_trivial_to_fix",
    #     description="""
    # The error is trivial to fix. The gold results can be easily obtained if a obvious mistake is fixed. Only applicable if spider2_ex = 0.0.
    # """.strip(),
    # ),
    # ErrorCategory(
    #     name="error_is_easy_to_fix",
    #     description="""
    # The error is easy to fix. There is something clearly wrong with the prediction. Only applicable if spider2_ex = 0.0.
    # """.strip(),
    # ),
    # ErrorCategory(
    #     name="error_is_hard_to_fix",
    #     description="""
    # The error is not easy to fix. The difference between the prediction and the gold query is not obvious. Only applicable if spider2_ex = 0.0.
    # """.strip(),
    # ),
]

##### Remove #####
MASK_PREDICTION = False
##################


class LLMErrorClassifier:
    def __init__(
        self,
        llm: str = "openai-responses:gpt-5-mini",
        categories: list[ErrorCategory] = DEFAULT_CATEGORIES,
        mask_prediction: bool = MASK_PREDICTION,
    ):
        self.llm = llm
        self.categories = categories
        self.mask_prediction = mask_prediction
        self._usage = Usage.create(llm)

    def usage(self) -> Usage:
        return self._usage

    async def _classify_task_async(self, task: NL2QTaskOutput) -> list[str]:
        if not self.categories:
            return []

        if self.mask_prediction:
            if task.output_type != "simple":
                raise ValueError("Only simple tasks are supported when mask_prediction is True for now.")
            task = copy.deepcopy(task)
            task.pred_query = None
            task.extra_pred_info.raw_pred_query = None
            task.extra_pred_info.linked_schema = None
            task.inference_metrics = {}
            task.eval_metrics = {}

        prompt = jinja2.Template(CLASSIFICATION_PROMPT).render(
            task_and_output=task.to_markdown(),
            categories=json.dumps([{"name": c.name, "description": c.description} for c in self.categories], indent=2),
        )

        output_type = list[Literal[tuple(c.name for c in self.categories)]]  # type: ignore
        agent = Agent[None, output_type](  # type: ignore
            model=self.llm,
            output_type=output_type,
            model_settings={
                "openai_reasoning_effort": "medium",
                "openai_reasoning_summary": "detailed",
            },
        )
        result = await agent.run(prompt)
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
        return list(set(result.output))

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
    def __init__(self, classifier_llm: str = "openai-responses:gpt-5-mini", do_error_classification: bool = True):
        self.classifier_llm = classifier_llm
        self.do_error_classification = do_error_classification
        self._usage = Usage.create(classifier_llm)

    def usage(self) -> Usage:
        return self._usage

    async def _error_categories_section(self, result: NL2QRunResult) -> str:
        llm_classifier = LLMErrorClassifier(llm=self.classifier_llm)
        categories = await llm_classifier.classify_async(result)
        self._usage += llm_classifier.usage()
        qid_to_db = {task.qid: task.db for task in result.tasks}
        res = "## Error Categories"

        for category in categories:
            res += f"\n\n### {category.name}\n\n"
            res += f"{category.description}\n\n"
            if len(category.qids) > 0:
                res += "\n".join(
                    f" [[{qid} ({qid_to_db[qid]})]](./readable/{qid}/task_readable.md)" for qid in category.qids
                )
            else:
                res += "(No tasks in this category)"

        # # Add not-classified error qids subsection
        # error_qids = [task.qid for task in result.tasks if task.eval_metrics["simple_ex"] == 0.0]
        # classified_qids = {qid for category in categories for qid in category.qids}
        # not_classified_qids = [qid for qid in error_qids if qid not in classified_qids]

        # res += "\n\n### not_classified\n\n"
        # res += "Error tasks (simple_ex = 0.0) that were not classified into any of the above categories.\n\n"
        # if len(not_classified_qids) > 0:
        #     res += "\n".join(f" [[{qid} ({qid_to_db[qid]})]](./readable/{qid}/task_readable.md)" for qid in not_classified_qids)
        # else:
        #     res += "(No tasks in this category)"
        return res

    def _error_section(self, result: NL2QRunResult) -> str:
        res = "## Error Tasks"
        res += "\n\n### Query Syntax Error Tasks (executable = 0.0):"
        error_tasks = [task for task in result.tasks if task.eval_metrics["executable"] == 0.0]
        res += "\n\n" + "\n".join(
            f" [[{task.qid} ({task.db})]](./readable/{task.qid}/task_readable.md)" for task in error_tasks
        )
        res += "\n\n### Query Semantic Error Tasks (executable = 1.0 but simple_ex = 0.0):"
        error_tasks = [
            task
            for task in result.tasks
            if task.eval_metrics["executable"] == 1.0 and task.eval_metrics["simple_ex"] == 0.0
        ]
        res += "\n\n" + "\n".join(
            f" [[{task.qid} ({task.db})]](./readable/{task.qid}/task_readable.md)" for task in error_tasks
        )
        return res

    def _schema_linking_section(self, result: NL2QRunResult) -> str:
        res = "## Schema Linking"
        res += "\n\n### Tasks where perfect_linked_schema_r = 0.0:"
        error_tasks = [task for task in result.tasks if task.eval_metrics["perfect_linked_schema_r"] == 0.0]
        res += "\n\n" + "\n".join(
            f" [[{task.qid} ({task.db})]](./readable/{task.qid}/task_readable.md)" for task in error_tasks
        )
        return res

    def _postprocess_impact_section(self, result: NL2QRunResult) -> str:
        qid_to_db = {task.qid: task.db for task in result.tasks}
        qids: dict[str, list[str]] = {
            "Improved": [],
            "Regressed": [],
            "Potential Improvable (bird_sql_ex_soft)": [],
            "Potential Improvable (simple_ex)": [],
        }
        for task in result.tasks:
            if task.eval_metrics["raw_pred_bird_sql_ex"] == 0.0 and task.eval_metrics["bird_sql_ex"] == 1.0:
                qids["Improved"].append(task.qid)
            elif task.eval_metrics["raw_pred_bird_sql_ex"] == 1.0 and task.eval_metrics["bird_sql_ex"] == 0.0:
                qids["Regressed"].append(task.qid)
            elif task.eval_metrics["raw_pred_bird_sql_ex"] == task.eval_metrics["bird_sql_ex"] == 0.0 and (
                task.eval_metrics["bird_sql_ex_soft"] == 1.0
            ):
                qids["Potential Improvable (bird_sql_ex_soft)"].append(task.qid)
            elif task.eval_metrics["bird_sql_ex_soft"] == 0.0 and (
                task.eval_metrics["raw_pred_simple_ex"] == 1.0 or task.eval_metrics["simple_ex"] == 1.0
            ):
                qids["Potential Improvable (simple_ex)"].append(task.qid)

        descriptions = {
            "Improved": "Tasks where bird_sql_ex improved from 0.0 to 1.0",
            "Regressed": "Tasks where bird_sql_ex regressed from 1.0 to 0.0",
            "Potential Improvable (bird_sql_ex_soft)": "Tasks where bird_sql_ex remains 0.0, but bird_sql_ex_soft is 1.0",
            "Potential Improvable (simple_ex)": "Tasks where bird_sql_ex_soft remains 0.0, but simple_ex is 1.0",
        }

        res = "## Postprocessing Impact"
        for key, qs in qids.items():
            res += f"\n\n### {key}\n\n"
            res += f"{descriptions[key]}:"
            res += "\n\n" + "\n".join(f" [[{q} ({qid_to_db[q]})]](./readable/{q}/task_readable.md)" for q in qs)
        return res

    def _num_tool_calls_section(self, result: NL2QRunResult) -> str:
        qid_to_db = {task.qid: task.db for task in result.tasks}
        res = "## Tool Calls"
        res += "\n\n### Top 10 tasks with most run_query calls"
        num_calls = []
        for task in result.tasks:
            if "tools" in task.inference_metrics:
                num_calls.append((task.qid, task.inference_metrics["tools"]["run_query"]["num_calls"]))
        num_calls.sort(key=lambda x: x[1], reverse=True)
        for q, n in num_calls[:10]:
            res += f"\n\n[[{q} ({qid_to_db[q]})]](./readable/{q}/task_readable.md) - {n} run_query calls"
        return res

    async def analyze_async(self, result: NL2QRunResult) -> str:
        """Analyze the run result and return a markdown string containing the error analysis report."""
        sections = []
        if self.do_error_classification:
            sections.append(await self._error_categories_section(result))
        sections.append(self._error_section(result))
        sections.append(self._num_tool_calls_section(result))
        if any(task.extra_pred_info.linked_schema is not None for task in result.tasks):
            sections.append(self._schema_linking_section(result))
        if any(task.extra_pred_info.raw_pred_query is not None for task in result.tasks):
            sections.append(self._postprocess_impact_section(result))

        res = "\n\n".join(sections)
        return res


class DbtAnalyzer:
    """Analyzer for dbt task results."""

    def __init__(self) -> None:
        pass

    def _task_link(self, task: NL2QTaskOutput) -> str:
        return f"[[{task.qid} ({task.db})]](./readable/{task.qid}/task_readable.md)"

    def _error_section(self, result: NL2QRunResult) -> str:
        res = "## Error Tasks"

        res += "\n\n### dbt run Failed:"
        failed = [task for task in result.tasks if not getattr(task, "dbt_run_success", True)]
        if failed:
            res += "\n\n" + "\n".join(f" {self._task_link(task)}" for task in failed)
        else:
            res += "\n\n(none)"

        res += "\n\n### dbt run Succeeded but spider2_duckdb_match = 0.0:"
        wrong = [
            task
            for task in result.tasks
            if getattr(task, "dbt_run_success", False)
            and task.eval_metrics.get("spider2_duckdb_match") == 0.0
        ]
        if wrong:
            res += "\n\n" + "\n".join(f" {self._task_link(task)}" for task in wrong)
        else:
            res += "\n\n(none)"

        return res

    def _num_tool_calls_section(self, result: NL2QRunResult) -> str:
        res = "## Tool Calls"
        tool_names = ["file_editor", "run_dbt", "get_table_schema"]
        for tool_name in tool_names:
            num_calls: list[tuple[str, int]] = []
            for task in result.tasks:
                tools = task.inference_metrics.get("tools", {})
                if tool_name in tools:
                    num_calls.append((task.qid, tools[tool_name].get("num_calls", 0)
                                      + tools[tool_name].get("num_view", 0)
                                      + tools[tool_name].get("num_write_file", 0)
                                      + tools[tool_name].get("num_str_replace", 0)))
            if not num_calls:
                continue
            num_calls.sort(key=lambda x: x[1], reverse=True)
            qid_to_db = {task.qid: task.db for task in result.tasks}
            res += f"\n\n### Top 10 tasks with most {tool_name} calls"
            for q, n in num_calls[:10]:
                res += f"\n\n[[{q} ({qid_to_db[q]})]](./readable/{q}/task_readable.md) - {n} calls"
        return res

    async def analyze_async(self, result: NL2QRunResult) -> str:
        """Analyze dbt run results and return a markdown report."""
        sections = [
            self._error_section(result),
            self._num_tool_calls_section(result),
        ]
        return "\n\n".join(sections)


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--classifier_llm", default="openai-responses:gpt-5")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--error_metric_name", default="simple_ex")
    parser.add_argument("--do_error_classification", type=bool_flag, default=True)
    args = parser.parse_args()
    print(args)
    print()

    mintq.configure()

    with open(os.path.join(args.result_dir, "result.json"), "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    output_types = set(task.output_type for task in result.tasks)

    if output_types == {"dbt"}:
        dbt_analyzer = DbtAnalyzer()
        t0 = time.time()
        error_analysis = await dbt_analyzer.analyze_async(result)
        print(f"Analysis finished in {time.time() - t0:.2f} seconds")
    else:
        analyzer = Analyzer(
            classifier_llm=args.classifier_llm, do_error_classification=args.do_error_classification
        )
        t0 = time.time()
        error_analysis = await analyzer.analyze_async(result)
        print(f"Analysis finished in {time.time() - t0:.2f} seconds")
        print(f"Total cost USD: {analyzer.usage().api_cost_usd:.6f}")

    with open(os.path.join(args.result_dir, "analysis.md"), "w") as f:
        f.write(error_analysis)
    print(f"Saved error report to {os.path.join(args.result_dir, 'analysis.md')}")


if __name__ == "__main__":
    asyncio.run(main_async())
