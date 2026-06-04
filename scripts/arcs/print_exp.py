import math
import os
from typing import Any
import tabulaflow
from tabulaflow.research.types import AmbigNL2QTask, NL2QRunResult
from decimal import Decimal
from tabulate import tabulate
import time
import pickle


# OLD_CORE_EXP_DIRS = {
#     "o4-mini-medium_simple": "output/130_o4-mini-medium-simple/",
#     "o4-mini-medium_flat": "output/130_o4-mini-medium-flat/",
#     "o4-mini-low_structured": "output/131_o4-mini-low_structured/",
#     "o4-mini-medium_structured": "output/130_o4-mini-medium_structured/",
#     "o4-mini-high_structured": "output/131_o4-mini-high_structured/",
# }
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


TALBE_FMT = "github"


tabulaflow.configure()

for exp in EXPS:
    assert os.path.exists(os.path.join("output", "paper", exp, "result.json")), f"Result file not found for {exp}"
print("All result files found")

t0 = time.time()

if os.path.exists("cache/exp_results.pickle"):
    with open("cache/exp_results.pickle", "rb") as f:
        EXP_RESULTS = pickle.load(f)
else:
    EXP_RESULTS: dict[str, NL2QRunResult] = {}

    for exp in EXPS:
        with open(os.path.join("output", "paper", exp, "result.json"), "r") as f:
            EXP_RESULTS[exp] = NL2QRunResult.model_validate_json(f.read())

    with open("cache/exp_results.pickle", "wb") as f:
        pickle.dump(EXP_RESULTS, f)

print()
print(f"Loaded {len(EXP_RESULTS)} results in {time.time() - t0:.2f} seconds")
print()


def calc_average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4)


def print_table(name: str, headers: list[str], rows: list[list[Any]]):
    print(f"### {name}")
    if TALBE_FMT != "tab":
        print(tabulate(rows, headers=headers, tablefmt=TALBE_FMT))
    else:
        print("\t".join(headers))
        for row in rows:
            print("\t".join([f"{v:.4f}" if isinstance(v, (float, Decimal)) else str(v) for v in row]))
    print()
    print()


def num_aps(task: AmbigNL2QTask, finite_only: bool = False) -> int:
    return len([ap for ap in task.gold_ambiguity_points if not finite_only or ap.type == "finite"])


def print_agent_architecture_table(exp_names: list[str]):
    headers = ["Method", "EX", "EX_1AP", "EX_2AP", "EX_3+AP", "User Effort", "Latency", "Cost"]
    rows = []
    for exp_name in exp_names:
        result = EXP_RESULTS[exp_name]
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
    print_table("Agent Architecture Table", headers, rows)


def print_agent_architecture_table_finite_ap(exp_names: list[str]):
    headers = ["Method", "EX", "EX_1AP", "EX_2AP", "EX_3+AP", "User Effort", "Latency", "Cost"]
    rows = []
    for exp_name in exp_names:
        result = EXP_RESULTS[exp_name]
        ex = result.aggregated_eval_metrics["simple_ex"]["avg"]
        ex_1ap = calc_average(
            [task.eval_metrics["simple_ex"] for task in result.tasks if num_aps(task, finite_only=True) == 1]
        )
        ex_2ap = calc_average(
            [task.eval_metrics["simple_ex"] for task in result.tasks if num_aps(task, finite_only=True) == 2]
        )
        ex_3plusap = calc_average(
            [task.eval_metrics["simple_ex"] for task in result.tasks if num_aps(task, finite_only=True) >= 3]
        )
        user_effort = result.total_user_simulator_usage.output_tokens / len(result.tasks)
        latency = result.aggregated_inference_metrics["latency_seconds"]["avg"]
        cost = result.total_usage.api_cost_usd / len(result.tasks)
        rows.append([exp_name, ex, ex_1ap, ex_2ap, ex_3plusap, user_effort, latency, cost])
    print_table("Agent Architecture Table (Finite AP)", headers, rows)


def print_fine_grained_table(exp_names: list[str]):
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
        result = EXP_RESULTS[exp_name]
        if f"{exp_name}_gold-ap" in EXP_RESULTS:
            sql_ex = EXP_RESULTS[f"{exp_name}_gold-ap"].aggregated_eval_metrics["simple_ex"]["avg"]
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
    print_table("Fine-grained Table", headers, rows)


def round_cost(cost: float) -> float:
    if cost < 0.001:
        return round(cost, 4)
    elif cost < 0.01:
        return round(cost, 3)
    else:
        return round(cost, 2)


def print_main_table(exp_names: list[str]):
    headers = ["Method", "Cost", "Perfect_R", "Perfect_F1", "SQL_EX", "EX", "Delta_EX"]
    rows = []
    for exp_name in exp_names:
        result = EXP_RESULTS[exp_name]
        if f"{exp_name}_gold-ap" in EXP_RESULTS:
            sql_ex = EXP_RESULTS[f"{exp_name}_gold-ap"].aggregated_eval_metrics["simple_ex"]["avg"]
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
    print_table("Fine-grained Table", headers, rows)


# def print_user_effort_table(exp_names: list[str]):
#     headers = ["Method", "Num Requests", "User Input Tokens", "User Output Tokens", "User Cost"]
#     rows = []
#     for exp_name in exp_names:
#         result = EXP_RESULTS[exp_name]
#         num_requests = result.total_user_simulator_usage.api_requests / len(result.tasks)
#         user_input_tokens = result.total_user_simulator_usage.input_tokens / len(result.tasks)
#         user_output_tokens = result.total_user_simulator_usage.output_tokens / len(result.tasks)
#         user_cost = result.total_user_simulator_usage.api_cost_usd / len(result.tasks)
#         rows.append([exp_name, num_requests, user_input_tokens, user_output_tokens, user_cost])
#     print_table("User Effort Table", headers, rows)


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
        row = [exp_name]
        for ambiguity_type in ambiguity_types:
            row.append(result.aggregated_eval_metrics[f"{ambiguity_type}_ambig_point_r"]["avg"])
        rows.append(row)
    print_table("Result by Ambiguity Type", headers, rows)


def print_error_distribution(exp_names: list[str]):
    headers = ["Method", "Invalid Output", "Not Executable", "Executable but Match None", "Match One", "Correct"]
    rows = []
    for exp_name in exp_names:
        result = EXP_RESULTS[exp_name]
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
    print_table("Error Distribution", headers, rows)


def print_arcs_ambrosia_table(exp_names: list[str]):
    headers = ["Method", "EX_ARCS", "EX_Ambrosia", "EX_ARCS_with_taxonomy", "EX_Ambrosia_with_taxonomy"]
    rows = []
    for exp_name in exp_names:
        arcs_result = EXP_RESULTS[exp_name]
        ambrosia_result = EXP_RESULTS[f"ambrosia_{exp_name}"]
        arcs_with_taxonomy_result = EXP_RESULTS[f"{exp_name}_taxonomy"]
        ambrosia_with_taxonomy_result = EXP_RESULTS[f"ambrosia_{exp_name}_taxonomy"]
        rows.append(
            [
                exp_name,
                arcs_result.aggregated_eval_metrics["simple_ex"]["avg"],
                ambrosia_result.aggregated_eval_metrics["simple_ex"]["avg"],
                arcs_with_taxonomy_result.aggregated_eval_metrics["simple_ex"]["avg"],
                ambrosia_with_taxonomy_result.aggregated_eval_metrics["simple_ex"]["avg"],
            ]
        )
    print_table("ARCS vs. Ambrosia Table", headers, rows)


def main():
    all_exps = [
        exp
        for exp in EXP_RESULTS.keys()
        if not exp.endswith("gold-ap") and not exp.startswith("ambrosia_") and not exp.endswith("_taxonomy")
    ]
    print_main_table(exp for exp in all_exps if EXP_RESULTS[exp].tasks[0].output_type == "ambig-structured")
    print_fine_grained_table([exp for exp in all_exps if EXP_RESULTS[exp].tasks[0].output_type == "ambig-structured"])
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
        ]
    )
    print_result_by_ambiguity_type([exp for exp in all_exps if EXP_RESULTS[exp].tasks[0].output_type != "ambig-flat"])
    print_error_distribution(all_exps)
    print_arcs_ambrosia_table(
        [
            "gpt-4.1-nano_structured",
            "gpt-4.1_structured",
            "o4-mini-medium_structured",
        ]
    )


if __name__ == "__main__":
    main()
