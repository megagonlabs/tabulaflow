import argparse
import os
from typing import Any
from decimal import Decimal
from tabulate import tabulate
from mintq.schema import AmbigNL2QTask, NL2QRunResult


EXP_DIRS = {
    # "structured_gpt-oss-120b": "output/87_gpt-oss-120b/",
    # "structured_claude-sonnet-4-5-20250929": "output/85_claude-sonnet-4-5-20250929/",
    # "structured_gemini-2.0-flash": "output/84_gemini-2.0-flash/",
    # "structured_gpt-4.1-mini": "output/82_openai-responses:gpt-4.1-mini/",
    # "structured_gpt-4.1": "output/82_openai-responses:gpt-4.1/",
    # "90_gpt-4.1_simple": "output/90_gpt-4.1_simple/",
    # "90_gpt-4.1_flat": "output/90_gpt-4.1_flat/",
    # "90_gpt-4.1_structured": "output/90_gpt-4.1_structured/",
    "91_gpt-4.1_simple": "output/91_gpt-4.1_simple/",
    "91_gpt-4.1_simple_patience_ap": "output/91_gpt-4.1_simple_patience_ap/",
    "92_gpt-4.1_structured": "output/92_gpt-4.1_structured/",
    "92_gpt-4.1_flat": "output/92_gpt-4.1_flat/",
}

TALBE_FMT = "github"


EXP_RESULTS = {}
for method, exp_dir in EXP_DIRS.items():
    with open(os.path.join(exp_dir, "result.json"), "r") as f:
        EXP_RESULTS[method] = NL2QRunResult.model_validate_json(f.read())


def main():
    exp_a = EXP_RESULTS["91_gpt-4.1_simple_patience_ap"]
    exp_b = EXP_RESULTS["92_gpt-4.1_structured"]

    for task_a, task_b in zip(exp_a.tasks, exp_b.tasks):
        assert task_a.qid == task_b.qid
        if task_a.eval_metrics["simple_ex"] > task_b.eval_metrics["simple_ex"]:
            print(task_a.qid)

if __name__ == "__main__":
    main()