import os
import tabulaflow
from tabulaflow.schema import NL2QRunResult

tabulaflow.configure()

result_dir = "output/115_o4-mini-structured/"


EXP_DIRS = {
    "claude-sonnet-4-5_structured": "output/133_claude-sonnet-4-5-structured/",
    "claude-opus-4-5_structured": "output/143_claude-opus-4-5-structured/",
    "claude-sonnet-4-5_structured_gold-ap": "output/137_claude-sonnet-4-5-structured-gold_ap/",
    "claude-opus-4-5_structured_gold-ap": "output/143_claude-opus-4-5-structured-gold_ap/",
}

RESULTS = {}

for method, exp_dir in EXP_DIRS.items():
    with open(os.path.join(exp_dir, "result.json"), "r") as f:
        RESULTS[method] = NL2QRunResult.model_validate_json(f.read())

pseudo_ex_sonnet = 0.0
pseudo_ex_opus = 0.0

pseudo_1_ex_0_sonnet = 0.0
pseudo_1_ex_0_opus = 0.0

pseudo_0_ex_1_sonnet = 0.0
pseudo_0_ex_1_opus = 0.0

for task_sonnet, task_opus, task_sonnet_gold_ap, task_opus_gold_ap in zip(
    RESULTS["claude-sonnet-4-5_structured"].tasks,
    RESULTS["claude-opus-4-5_structured"].tasks,
    RESULTS["claude-sonnet-4-5_structured_gold-ap"].tasks,
    RESULTS["claude-opus-4-5_structured_gold-ap"].tasks,
):
    assert task_sonnet.qid == task_opus.qid == task_sonnet_gold_ap.qid == task_opus_gold_ap.qid
    pseudo_ex_sonnet_flag = float(
        task_sonnet.eval_metrics["perfect_disambiguation_r"] == 1.0
        and task_sonnet_gold_ap.eval_metrics["simple_ex"] == 1.0
    )

    pseudo_ex_sonnet += pseudo_ex_sonnet_flag
    pseudo_1_ex_0_sonnet += float(pseudo_ex_sonnet_flag == 1.0 and task_sonnet.eval_metrics["simple_ex"] == 0.0)
    pseudo_0_ex_1_sonnet += float(pseudo_ex_sonnet_flag == 0.0 and task_sonnet.eval_metrics["simple_ex"] == 1.0)

    pseudo_ex_opus_flag = float(
        task_opus.eval_metrics["perfect_disambiguation_r"] == 1.0 and task_opus_gold_ap.eval_metrics["simple_ex"] == 1.0
    )

    pseudo_ex_opus += pseudo_ex_opus_flag
    pseudo_1_ex_0_opus += float(pseudo_ex_opus_flag == 1.0 and task_opus.eval_metrics["simple_ex"] == 0.0)
    pseudo_0_ex_1_opus += float(pseudo_ex_opus_flag == 0.0 and task_opus.eval_metrics["simple_ex"] == 1.0)

print(f"Pseudo EX (Sonnet): {pseudo_ex_sonnet}")
print(f"Pseudo EX (Opus): {pseudo_ex_opus}")
print(f"Pseudo 1 EX 0 (Sonnet): {pseudo_1_ex_0_sonnet}")
print(f"Pseudo 1 EX 0 (Opus): {pseudo_1_ex_0_opus}")
print(f"Pseudo 0 EX 1 (Sonnet): {pseudo_0_ex_1_sonnet}")
print(f"Pseudo 0 EX 1 (Opus): {pseudo_0_ex_1_opus}")
