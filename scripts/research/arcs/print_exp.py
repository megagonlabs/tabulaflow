import argparse
import math
import time
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any

from tabulate import tabulate

from tabulaflow.research.types import NL2QRunResult

EXPS = [
    "gpt-4.1_simple_1patience",
    "gpt-4.1_simple_3patience",
    "gpt-4.1_simple",
    "gpt-4.1_flat",
    "o4-mini-medium_simple_1patience",
    "o4-mini-medium_simple_3patience",
    "o4-mini-medium_simple_5patience",
    "o4-mini-medium_simple",
    "o4-mini-medium_flat",
    "gptoss-20b_structured",
    "gptoss-120b_structured",
    "qwen3-8b_structured",
    "qwen3-235b-a22b-instruct-2507_structured",
    "qwen3-coder-480b_structured",
    "deepseek-v3.1_structured",
    "deepseek-r1-0528_structured",
    "kimi-k2-thinking_structured",
    "gemini-2.5-flash_structured",
    "gemini-2.5-pro_structured",
    "gemini-3-pro-preview_structured",
    "claude-haiku-4-5_structured",
    "claude-sonnet-4-5_structured",
    "claude-opus-4-5_structured",
    "gpt-4.1-nano_structured",
    "gpt-4.1-mini_structured",
    "gpt-4.1_structured",
    "o4-mini-low_structured",
    "o4-mini-medium_structured",
    "o4-mini-high_structured",
    "gpt-5-nano-medium_structured",
    "gpt-5-mini-medium_structured",
    "gpt-5-minimal_structured",
    "gpt-5-low_structured",
    "gpt-5-medium_structured",
    "gpt-5-high_structured",
    "gptoss-20b_structured_gold-ap",
    "gptoss-120b_structured_gold-ap",
    "qwen3-8b_structured_gold-ap",
    "qwen3-235b-a22b-instruct-2507_structured_gold-ap",
    "qwen3-coder-480b_structured_gold-ap",
    "deepseek-v3.1_structured_gold-ap",
    "deepseek-r1-0528_structured_gold-ap",
    "kimi-k2-thinking_structured_gold-ap",
    "gpt-4.1-mini_structured_gold-ap",
    "gpt-4.1-nano_structured_gold-ap",
    "gpt-4.1_structured_gold-ap",
    "o4-mini-low_structured_gold-ap",
    "o4-mini-medium_structured_gold-ap",
    "o4-mini-high_structured_gold-ap",
    "gpt-5-nano-medium_structured_gold-ap",
    "gpt-5-mini-medium_structured_gold-ap",
    "gpt-5-minimal_structured_gold-ap",
    "gpt-5-low_structured_gold-ap",
    "gpt-5-medium_structured_gold-ap",
    "gpt-5-high_structured_gold-ap",
    "claude-haiku-4-5_structured_gold-ap",
    "claude-sonnet-4-5_structured_gold-ap",
    "claude-opus-4-5_structured_gold-ap",
    "gemini-2.5-flash_structured_gold-ap",
    "gemini-2.5-pro_structured_gold-ap",
    "gemini-3-pro-preview_structured_gold-ap",
    "gpt-4.1-nano_structured_taxonomy",
    "gpt-4.1_structured_taxonomy",
    "o4-mini-medium_structured_taxonomy",
    "ambrosia_gpt-4.1-nano_structured",
    "ambrosia_gpt-4.1-nano_structured_taxonomy",
    "ambrosia_gpt-4.1_structured",
    "ambrosia_gpt-4.1_structured_taxonomy",
    "ambrosia_o4-mini-medium_structured",
    "ambrosia_o4-mini-medium_structured_taxonomy",
]


def load_results(results_dir: Path) -> dict[str, NL2QRunResult]:
    paths = {exp: results_dir / exp / "result.json" for exp in EXPS}
    missing = [path for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Result file not found: {missing[0]}")

    print("All result files found")
    started_at = time.perf_counter()
    results = {exp: NL2QRunResult.model_validate_json(path.read_text()) for exp, path in paths.items()}
    print()
    print(f"Loaded {len(results)} results in {time.perf_counter() - started_at:.2f} seconds")
    print()
    return results


def print_table(name: str, headers: list[str], rows: list[list[Any]], table_format: str) -> None:
    print(f"### {name}")
    if table_format != "tab":
        print(tabulate(rows, headers=headers, tablefmt=table_format))
    else:
        print("\t".join(headers))
        for row in rows:
            print("\t".join([f"{v:.4f}" if isinstance(v, (float, Decimal)) else str(v) for v in row]))
    print()
    print()


def print_agent_architecture_table(
    exp_names: Iterable[str], exp_results: dict[str, NL2QRunResult], table_format: str
) -> None:
    headers = ["Method", "EX", "EX_1AP", "EX_2AP", "EX_3+AP", "User Effort", "Latency", "Cost"]
    rows = []
    for exp_name in exp_names:
        result = exp_results[exp_name]
        rows.append(
            [
                exp_name,
                result.aggregated_eval_metrics["simple_ex"]["avg"],
                result.aggregated_eval_metrics["simple_ex_by_ambig_point_num"]["1AP"]["avg"],
                result.aggregated_eval_metrics["simple_ex_by_ambig_point_num"]["2AP"]["avg"],
                result.aggregated_eval_metrics["simple_ex_by_ambig_point_num"]["3+AP"]["avg"],
                result.aggregated_inference_metrics["user_effort"]["avg"],
                result.aggregated_inference_metrics["latency_seconds"]["avg"],
                round_cost(result.total_usage.api_cost_usd / len(result.tasks)),
            ]
        )
    print_table("Agent Architecture Table", headers, rows, table_format)


def print_fine_grained_table(
    exp_names: Iterable[str], exp_results: dict[str, NL2QRunResult], table_format: str
) -> None:
    headers = [
        "Method",
        "EX",
        "Perfect_R",
        "Perfect_F1",
        "Cost",
        "Latency",
        "AP_P",
        "AP_R",
        "AP_F1",
        "Intp_P",
        "Intp_R",
        "Intp_F1",
        "SQL_EX",
    ]
    rows = []
    for exp_name in exp_names:
        result = exp_results[exp_name]
        if f"{exp_name}_gold-ap" in exp_results:
            sql_ex = exp_results[f"{exp_name}_gold-ap"].aggregated_eval_metrics["simple_ex"]["avg"]
        else:
            sql_ex = math.nan
        rows.append(
            [
                exp_name,
                result.aggregated_eval_metrics["simple_ex"]["avg"],
                result.aggregated_eval_metrics["perfect_disambiguation_r"]["avg"],
                result.aggregated_eval_metrics["perfect_disambiguation_f1"]["avg"],
                round_cost(result.total_usage.api_cost_usd / len(result.tasks)),
                result.aggregated_inference_metrics["latency_seconds"]["avg"],
                result.aggregated_eval_metrics["ambig_point_p"]["avg"],
                result.aggregated_eval_metrics["ambig_point_r"]["avg"],
                result.aggregated_eval_metrics["ambig_point_f1"]["avg"],
                result.aggregated_eval_metrics["interpretation_p"]["avg"],
                result.aggregated_eval_metrics["interpretation_r"]["avg"],
                result.aggregated_eval_metrics["interpretation_f1"]["avg"],
                sql_ex,
            ]
        )
    print_table("Fine-grained Table", headers, rows, table_format)


def round_cost(cost: float) -> float:
    if cost < 0.001:
        return round(cost, 4)
    elif cost < 0.01:
        return round(cost, 3)
    else:
        return round(cost, 2)


def print_main_table(exp_names: Iterable[str], exp_results: dict[str, NL2QRunResult], table_format: str) -> None:
    headers = ["Method", "Cost", "Perfect_R", "Perfect_F1", "SQL_EX", "EX", "Delta_EX"]
    rows = []
    for exp_name in exp_names:
        result = exp_results[exp_name]
        if f"{exp_name}_gold-ap" in exp_results:
            sql_ex = exp_results[f"{exp_name}_gold-ap"].aggregated_eval_metrics["simple_ex"]["avg"]
        else:
            sql_ex = math.nan
        rows.append(
            [
                exp_name,
                round_cost(result.total_usage.api_cost_usd / len(result.tasks)),
                result.aggregated_eval_metrics["perfect_disambiguation_r"]["avg"],
                result.aggregated_eval_metrics["perfect_disambiguation_f1"]["avg"],
                sql_ex,
                result.aggregated_eval_metrics["simple_ex"]["avg"],
                result.aggregated_eval_metrics["simple_ex"]["avg"] - sql_ex,
            ]
        )
    print_table("Fine-grained Table", headers, rows, table_format)


AMBIGUITY_TYPES = [
    "semantic_column",
    "semantic_table",
    "semantic_value",
    "semantic_computation",
    "syntactic_column",
    "syntactic_table",
    "syntactic_value",
    "syntactic_computation",
]


def print_result_by_ambiguity_type(
    exp_names: Iterable[str], exp_results: dict[str, NL2QRunResult], table_format: str
) -> None:
    headers = ["Method", *AMBIGUITY_TYPES]
    rows = []
    for exp_name in exp_names:
        result = exp_results[exp_name]
        row = [exp_name]
        for ambiguity_type in AMBIGUITY_TYPES:
            row.append(result.aggregated_eval_metrics[f"{ambiguity_type}_ambig_point_r"]["avg"])
        rows.append(row)
    print_table("Result by Ambiguity Type", headers, rows, table_format)


def print_error_distribution(
    exp_names: Iterable[str], exp_results: dict[str, NL2QRunResult], table_format: str
) -> None:
    headers = ["Method", "Invalid Output", "Not Executable", "Executable but Match None", "Match One", "Correct"]
    rows = []
    for exp_name in exp_names:
        result = exp_results[exp_name]
        invalid_output = 0
        not_executable = 0
        executable_but_match_none = 0
        match_one = 0
        correct = 0
        for task in result.tasks:
            if task.eval_metrics["pred_success"] == 0.0:
                invalid_output += 1
            elif task.eval_metrics["executable"] == 0.0:
                not_executable += 1
            elif task.eval_metrics["found_one"] == 0.0:
                executable_but_match_none += 1
            elif task.eval_metrics["simple_ex"] == 0.0:
                match_one += 1
            else:
                correct += 1
        rows.append(
            [
                exp_name,
                round(invalid_output / len(result.tasks), 4),
                round(not_executable / len(result.tasks), 4),
                round(executable_but_match_none / len(result.tasks), 4),
                round(match_one / len(result.tasks), 4),
                round(correct / len(result.tasks), 4),
            ]
        )
    print_table("Error Distribution", headers, rows, table_format)


def print_arcs_ambrosia_table(
    exp_names: Iterable[str], exp_results: dict[str, NL2QRunResult], table_format: str
) -> None:
    headers = ["Method", "EX_ARCS", "EX_Ambrosia", "EX_ARCS_with_taxonomy", "EX_Ambrosia_with_taxonomy"]
    rows = []
    for exp_name in exp_names:
        arcs_result = exp_results[exp_name]
        ambrosia_result = exp_results[f"ambrosia_{exp_name}"]
        arcs_with_taxonomy_result = exp_results[f"{exp_name}_taxonomy"]
        ambrosia_with_taxonomy_result = exp_results[f"ambrosia_{exp_name}_taxonomy"]
        rows.append(
            [
                exp_name,
                arcs_result.aggregated_eval_metrics["simple_ex"]["avg"],
                ambrosia_result.aggregated_eval_metrics["simple_ex"]["avg"],
                arcs_with_taxonomy_result.aggregated_eval_metrics["simple_ex"]["avg"],
                ambrosia_with_taxonomy_result.aggregated_eval_metrics["simple_ex"]["avg"],
            ]
        )
    print_table("ARCS vs. Ambrosia Table", headers, rows, table_format)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path("output/paper"))
    parser.add_argument("--table-format", default="github")
    args = parser.parse_args()

    exp_results = load_results(args.results_dir)
    all_exps = [
        exp
        for exp in exp_results
        if not exp.endswith("gold-ap") and not exp.startswith("ambrosia_") and not exp.endswith("_taxonomy")
    ]
    structured_exps = [exp for exp in all_exps if exp_results[exp].tasks[0].output_type == "ambig-structured"]
    print_main_table(structured_exps, exp_results, args.table_format)
    print_fine_grained_table(structured_exps, exp_results, args.table_format)
    print_agent_architecture_table(
        [
            "gpt-4.1_simple_1patience",
            "gpt-4.1_simple_3patience",
            "gpt-4.1_simple",
            "gpt-4.1_flat",
            "gpt-4.1_structured",
            "o4-mini-medium_simple_1patience",
            "o4-mini-medium_simple_3patience",
            "o4-mini-medium_simple_5patience",
            "o4-mini-medium_simple",
            "o4-mini-medium_flat",
            "o4-mini-medium_structured",
        ],
        exp_results,
        args.table_format,
    )
    print_result_by_ambiguity_type(
        [exp for exp in all_exps if exp_results[exp].tasks[0].output_type != "ambig-flat"],
        exp_results,
        args.table_format,
    )
    print_error_distribution(all_exps, exp_results, args.table_format)
    print_arcs_ambrosia_table(
        [
            "gpt-4.1-nano_structured",
            "gpt-4.1_structured",
            "o4-mini-medium_structured",
        ],
        exp_results,
        args.table_format,
    )


if __name__ == "__main__":
    main()
