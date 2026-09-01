import argparse
from pathlib import Path

from tabulaflow.research.benchmarks import dataset_registry
from tabulaflow.research.types import NL2QRunResult, NL2QTaskOutput


def load_result(directory: Path) -> NL2QRunResult:
    return NL2QRunResult.model_validate_json((directory / "result.json").read_text())


def task_map(result: NL2QRunResult) -> dict[str, NL2QTaskOutput]:
    tasks = {task.qid: task for task in result.tasks}
    if len(tasks) != len(result.tasks):
        raise ValueError("Run result contains duplicate task qids")
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare per-task metrics from two benchmark runs.")
    parser.add_argument("result_dir_a", type=Path)
    parser.add_argument("result_dir_b", type=Path)
    parser.add_argument("--metric")
    args = parser.parse_args()

    result_a = load_result(args.result_dir_a)
    result_b = load_result(args.result_dir_b)
    if result_a.dataset != result_b.dataset:
        raise ValueError(f"Cannot compare datasets {result_a.dataset!r} and {result_b.dataset!r}")

    tasks_a = task_map(result_a)
    tasks_b = task_map(result_b)
    if tasks_a.keys() != tasks_b.keys():
        only_a = sorted(tasks_a.keys() - tasks_b.keys())
        only_b = sorted(tasks_b.keys() - tasks_a.keys())
        raise ValueError(f"Task qids differ: only in A={only_a}, only in B={only_b}")

    metric = args.metric or dataset_registry.get_class(result_a.dataset).default_metrics[0]
    a_better: list[str] = []
    b_better: list[str] = []
    for task_a in result_a.tasks:
        task_b = tasks_b[task_a.qid]
        metric_a = task_a.eval_metrics[metric]
        metric_b = task_b.eval_metrics[metric]
        if metric_a > metric_b:
            a_better.append(task_a.qid)
        elif metric_a < metric_b:
            b_better.append(task_a.qid)

    print(f"A is better than B ({len(a_better)} tasks):")
    for qid in a_better:
        print(f"  - {qid}")
    print()
    print(f"B is better than A ({len(b_better)} tasks):")
    for qid in b_better:
        print(f"  - {qid}")


if __name__ == "__main__":
    main()
