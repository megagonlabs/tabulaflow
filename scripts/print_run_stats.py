# mypy: ignore-errors
import argparse
import asyncio
import os
from tabulate import tabulate
import tabulaflow
from tabulaflow.schema import NL2QRunResult, StructuredAmbigNL2QTaskOutput
from tabulaflow.utils import dict_to_df


def print_ambig_stats(tasks: list[StructuredAmbigNL2QTaskOutput]) -> None:
    assert all(task.task_type == "ambig" for task in tasks)
    db_names = list(dict.fromkeys([task.db for task in tasks]))

    # Print number of ambiguity points per task
    max_ap = max([len(task.pred_ambiguity_points) for task in tasks])
    db2counts = {db: {ap: 0 for ap in range(0, max_ap + 1)} for db in db_names}
    for task in tasks:
        db2counts[task.db][len(task.pred_ambiguity_points)] += 1
    print()
    print("### Number of Ambiguity Points (AP) Stats")
    print()
    print(tabulate(dict_to_df(db2counts), headers="keys", tablefmt="github"))

    # Print distrubtion of parameter_dtype in infinite ambiguity points
    db2counts = {db: {dtype: 0 for dtype in ["int", "float", "str"]} for db in db_names}
    for task in tasks:
        for ap in task.pred_ambiguity_points:
            if ap.type == "infinite":
                db2counts[task.db][ap.parameter_dtype] += 1
    print()
    print("### Distribution of parameter_dtype in Infinite Ambiguity Points")
    print("note: this is the number of ambiguity points with the corresponding parameter_dtype")
    print()
    print(tabulate(dict_to_df(db2counts), headers="keys", tablefmt="github"))

    # Print distrubtion of total number of interpretation combinations
    num_intp = sorted(set([len(task.pred_queries) for task in tasks]))
    db2counts = {db: {n: 0 for n in num_intp} for db in db_names}
    for task in tasks:
        db2counts[task.db][len(task.pred_queries)] += 1
    print()
    print("### Distribution of Total Number of Interpretation Combinations")
    print("note: this is the number of tasks with the corresponding number of interpretation combinations")
    print()
    print(tabulate(dict_to_df(db2counts), headers="keys", tablefmt="github"))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_dir", default="output/test/")
    args = parser.parse_args()
    print(args)
    print()

    tabulaflow.configure()

    with open(os.path.join(args.result_dir, "result.json"), "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    print_ambig_stats(result.tasks)


if __name__ == "__main__":
    asyncio.run(main())
