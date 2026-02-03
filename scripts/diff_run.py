import argparse
import os
from mintq.schema import NL2QRunResult


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir_a")
    parser.add_argument("result_dir_b")
    parser.add_argument("--output_path", default="output/diff_run.md")
    args = parser.parse_args()
    print(args)
    print()

    with open(os.path.join(args.result_dir_a, "result.json"), "r") as f:
        result_a = NL2QRunResult.model_validate_json(f.read())
    with open(os.path.join(args.result_dir_b, "result.json"), "r") as f:
        result_b = NL2QRunResult.model_validate_json(f.read())

    sections = {
        "bird_sql_ex_0.0->1.0": [],
        "bird_sql_ex_1.0->0.0": [],
    }

    for task_a, task_b in zip(result_a.tasks, result_b.tasks):
        if task_a.qid != task_b.qid:
            raise ValueError(f"Task IDs do not match: {task_a.qid} != {task_b.qid}")

        if task_a.eval_metrics["bird_sql_ex"] == 0.0 and task_b.eval_metrics["bird_sql_ex"] == 1.0:
            sections["bird_sql_ex_0.0->1.0"].append(task_a.qid)
        elif task_a.eval_metrics["bird_sql_ex"] == 1.0 and task_b.eval_metrics["bird_sql_ex"] == 0.0:
            sections["bird_sql_ex_1.0->0.0"].append(task_a.qid)

    res = ""
    base_dir_a = os.path.dirname(args.result_dir_a)
    base_dir_b = os.path.dirname(args.result_dir_b)
    for key, qs in sections.items():
        res += f"\n\n### {key}\n\n"
        for q in qs:
            res += f"\n- [[{q}]](../{base_dir_a}/readable/{q}/task_readable.md) -> [[{q}]](../{base_dir_b}/readable/{q}/task_readable.md)\n"
    with open(args.output_path, "w") as f:
        f.write(res)
    print(f"Saved to {args.output_path}")
    print()
    for key, qs in sections.items():
        print(f"{key}: {len(qs)}")


if __name__ == "__main__":
    main()
