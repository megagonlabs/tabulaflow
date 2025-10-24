import argparse
import os
from typing import Any
from mintq.schema import NL2QRunResult
from decimal import Decimal


exp_dirs = {
    "structured_gpt-oss-120b": "output/87_gpt-oss-120b/",
    "structured_claude-sonnet-4-5-20250929": "output/85_claude-sonnet-4-5-20250929/",
    "structured_gemini-2.0-flash": "output/84_gemini-2.0-flash/",
    "structured_gpt-4.1-mini": "output/82_openai-responses:gpt-4.1-mini/",
    "structured_gpt-4.1": "output/82_openai-responses:gpt-4.1/",
}


def calc_average(values: list[float]) -> float:
    return sum(values) / len(values)


def print_table(name: str, headers: list[str], rows: list[list[Any]]):
    print(f"### {name}")
    print("\t".join(headers))
    for row in rows:
        print("\t".join([f"{v:.4f}" if isinstance(v, (float, Decimal)) else str(v) for v in row]))
    print()
    print()


def print_main_table():
    headers = ["Method", "EX", "EX_1AP", "EX_2AP", "EX_3+AP", "User Effort", "Latency", "Cost"]
    rows = []
    for method, exp_dir in exp_dirs.items():
        with open(os.path.join(exp_dir, "result.json"), "r") as f:
            result = NL2QRunResult.model_validate_json(f.read())

        ex = result.aggregated_eval_metrics["bird_sql_ex"]["avg"]
        ex_1ap = calc_average(
            [task.eval_metrics["bird_sql_ex"] for task in result.tasks if len(task.gold_ambiguity_points) == 1]
        )
        ex_2ap = calc_average(
            [task.eval_metrics["bird_sql_ex"] for task in result.tasks if len(task.gold_ambiguity_points) == 2]
        )
        ex_3plusap = calc_average(
            [task.eval_metrics["bird_sql_ex"] for task in result.tasks if len(task.gold_ambiguity_points) >= 3]
        )
        user_effort = result.total_user_simulator_usage.output_tokens / len(result.tasks)
        latency = result.aggregated_inference_metrics["latency_seconds"]["avg"]
        cost = result.total_usage.api_cost_usd / len(result.tasks)
        rows.append([method, ex, ex_1ap, ex_2ap, ex_3plusap, user_effort, latency, cost])
    print_table("Main Table", headers, rows)


def main():
    print_main_table()


if __name__ == "__main__":
    main()
