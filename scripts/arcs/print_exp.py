import argparse
import os
from typing import Any
from mintq.schema import AmbigNL2QTask, NL2QRunResult
from decimal import Decimal


EXP_DIRS = {
    "structured_gpt-oss-120b": "output/87_gpt-oss-120b/",
    "structured_claude-sonnet-4-5-20250929": "output/85_claude-sonnet-4-5-20250929/",
    "structured_gemini-2.0-flash": "output/84_gemini-2.0-flash/",
    "structured_gpt-4.1-mini": "output/82_openai-responses:gpt-4.1-mini/",
    "structured_gpt-4.1": "output/82_openai-responses:gpt-4.1/",
    "90_gpt-4.1_simple": "output/90_gpt-4.1_simple/",
    "90_gpt-4.1_flat": "output/90_gpt-4.1_flat/",
    "90_gpt-4.1_structured": "output/90_gpt-4.1_structured/",
}


EXP_RESULTS = {}
for method, exp_dir in EXP_DIRS.items():
    with open(os.path.join(exp_dir, "result.json"), "r") as f:
        EXP_RESULTS[method] = NL2QRunResult.model_validate_json(f.read())


def calc_average(values: list[float]) -> float:
    return sum(values) / len(values)


def print_table(name: str, headers: list[str], rows: list[list[Any]]):
    print(f"### {name}")
    print("\t".join(headers))
    for row in rows:
        print("\t".join([f"{v:.4f}" if isinstance(v, (float, Decimal)) else str(v) for v in row]))
    print()
    print()


def num_aps(task: AmbigNL2QTask, finite_only: bool = False) -> int:
    return len([ap for ap in task.gold_ambiguity_points if not finite_only or ap.type == "finite"])


def print_main_table(exp_names: list[str]):
    headers = ["Method", "EX", "EX_1AP", "EX_2AP", "EX_3+AP", "User Effort", "Latency", "Cost"]
    rows = []
    for exp_name in exp_names:
        result = EXP_RESULTS[exp_name]
        ex = result.aggregated_eval_metrics["bird_sql_ex"]["avg"]
        ex_1ap = calc_average([task.eval_metrics["bird_sql_ex"] for task in result.tasks if num_aps(task) == 1])
        ex_2ap = calc_average([task.eval_metrics["bird_sql_ex"] for task in result.tasks if num_aps(task) == 2])
        ex_3plusap = calc_average([task.eval_metrics["bird_sql_ex"] for task in result.tasks if num_aps(task) >= 3])
        user_effort = result.total_user_simulator_usage.output_tokens / len(result.tasks)
        latency = result.aggregated_inference_metrics["latency_seconds"]["avg"]
        cost = result.total_usage.api_cost_usd / len(result.tasks)
        rows.append([exp_name, ex, ex_1ap, ex_2ap, ex_3plusap, user_effort, latency, cost])
    print_table("Main Table", headers, rows)


ambiguity_types = [
    "semantic_column",
    "semantic_table",
    "semantic_value",
    "semantic_computation",
    "syntactic_column",
    "syntactic_table",
    "syntactic_value",
    "syntactic_computation",
]


def print_result_by_ambiguity_type(exp_names: list[str]):
    headers = ["Method", *ambiguity_types]
    rows = []
    for exp_name in exp_names:
        result = EXP_RESULTS[exp_name]
        row = [method]
        for ambiguity_type in ambiguity_types:
            row.append(
                calc_average(
                    [
                        task.eval_metrics["bird_sql_ex"]
                        for task in result.tasks
                        if any(ap.ambiguity_type == ambiguity_type for ap in task.gold_ambiguity_points)
                    ]
                )
            )
        rows.append(row)
    print_table("Result by Ambiguity Type", headers, rows)


def main():
    # print_main_table(exp_results)
    print_main_table(["90_gpt-4.1_simple", "90_gpt-4.1_flat", "90_gpt-4.1_structured"])

    # print_result_by_ambiguity_type(exp_results)


if __name__ == "__main__":
    main()
