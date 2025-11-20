import argparse
import os
from mintq.schema import NL2QRunResult


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir_a")
    parser.add_argument("result_dir_b")
    parser.add_argument("--metric", default="simple_ex")
    args = parser.parse_args()
    print(args)
    print()

    with open(os.path.join(args.result_dir_a, "result.json"), "r") as f:
        result_a = NL2QRunResult.model_validate_json(f.read())
    with open(os.path.join(args.result_dir_b, "result.json"), "r") as f:
        result_b = NL2QRunResult.model_validate_json(f.read())


    a_better = []
    b_better = []

    for task_a, task_b in zip(result_a.tasks, result_b.tasks):
        if task_a.qid != task_b.qid:
            raise ValueError(f"Only results with the same set of task qids can be compared: {task_a.qid} != {task_b.qid}")
        metric_a = task_a.eval_metrics[args.metric]
        metric_b = task_b.eval_metrics[args.metric]
        if metric_a > metric_b:
            a_better.append(task_a)
        elif metric_a < metric_b:
            b_better.append(task_b)
    print()
    print(f"A is better than B ({len(a_better)} tasks):")
    for task in a_better:
        print(f"  - {task.qid}")
    print()
    print(f"B is better than A ({len(b_better)} tasks):")
    for task in b_better:
        print(f"  - {task.qid}")

if __name__ == "__main__":
    main()
