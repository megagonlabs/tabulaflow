import os
import mintq
from mintq.schema import NL2QRunResult

mintq.configure()

result_dir = "output/115_o4-mini-structured/"


with open(os.path.join(result_dir, "result.json"), "r") as f:
    result = NL2QRunResult.model_validate_json(f.read())

for task in result.tasks:
    if task.eval_metrics["simple_ex"] == 0.0:
        print(task.qid, task.extra_info["ambrosia"]["ambig_type"])
