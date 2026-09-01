import argparse
from pathlib import Path

from tabulate import tabulate

from tabulaflow.research.reporting import dict_to_df
from tabulaflow.research.types import NL2QRunResult, StructuredAmbigNL2QTaskOutput


def print_ambiguity_stats(tasks: list[StructuredAmbigNL2QTaskOutput]) -> None:
    if not tasks:
        raise ValueError("Run result contains no tasks")

    databases = list(dict.fromkeys(task.db for task in tasks))
    max_points = max(len(task.pred_ambiguity_points) for task in tasks)
    point_counts: dict[str, dict[str, int]] = {
        database: {str(count): 0 for count in range(max_points + 1)} for database in databases
    }
    for task in tasks:
        point_counts[task.db][str(len(task.pred_ambiguity_points))] += 1

    print("### Number of Ambiguity Points")
    print()
    print(tabulate(dict_to_df(point_counts), headers="keys", tablefmt="github"))
    print()

    parameter_counts: dict[str, dict[str, int]] = {
        database: {dtype: 0 for dtype in ("int", "float", "str")} for database in databases
    }
    for task in tasks:
        for point in task.pred_ambiguity_points:
            if point.type == "infinite":
                parameter_counts[task.db][point.parameter_dtype] += 1

    print("### Infinite Parameter Types")
    print()
    print(tabulate(dict_to_df(parameter_counts), headers="keys", tablefmt="github"))
    print()

    query_counts = sorted({len(task.pred_queries) for task in tasks})
    interpretation_counts: dict[str, dict[str, int]] = {
        database: {str(count): 0 for count in query_counts} for database in databases
    }
    for task in tasks:
        interpretation_counts[task.db][str(len(task.pred_queries))] += 1

    print("### Interpretation Combinations")
    print()
    print(tabulate(dict_to_df(interpretation_counts), headers="keys", tablefmt="github"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Print ambiguity statistics for a structured benchmark run.")
    parser.add_argument("--result-dir", type=Path, default=Path("output/test"))
    args = parser.parse_args()

    result = NL2QRunResult.model_validate_json((args.result_dir / "result.json").read_text())
    tasks: list[StructuredAmbigNL2QTaskOutput] = []
    for task in result.tasks:
        if not isinstance(task, StructuredAmbigNL2QTaskOutput):
            raise ValueError(f"Task {task.qid} is not a structured ambiguity output")
        tasks.append(task)
    print_ambiguity_stats(tasks)


if __name__ == "__main__":
    main()
