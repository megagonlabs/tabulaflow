import argparse
import copy
import time
import asyncio
import random
import os
import pandas as pd
from tqdm import trange
from mintq.db_connector import BaseAsyncDBConnector
from mintq.schema import NL2QTaskOutput, NL2QRunResult, NL2QDataset
from mintq.utils import avg_and_round, save_csv
from mintq.datahub import get_dataset_loader
from mintq.metric import get_metric, BaseAsyncNL2QMetric
from mintq.toolhub.utils import format_df


async def compute_metrics_async(
    task: NL2QTaskOutput, metrics: list[BaseAsyncNL2QMetric], db_connector: BaseAsyncDBConnector
) -> NL2QTaskOutput:
    results = await asyncio.gather(*[m.compute_async(task=task, db_connector=db_connector) for m in metrics])
    for m, r in zip(metrics, results):
        task.metrics[m.name] = r
    return task


async def evaluate_async(
    result: NL2QRunResult, dataset: NL2QDataset, metrics: list[BaseAsyncNL2QMetric], batch_size: int
) -> NL2QRunResult:
    for i in trange(0, len(result.tasks), batch_size):
        await asyncio.gather(
            *[
                compute_metrics_async(task, metrics, dataset.db_connectors[task.db])
                for task in result.tasks[i : i + batch_size]
            ]
        )
    aggregated_metrics = {m.name: avg_and_round([task.metrics[m.name] for task in result.tasks]) for m in metrics}
    result.aggregated_metrics.update(aggregated_metrics)
    return result


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=[
            "spider2_ex",
            "bird_sql_ex",
            "bird_sql_ex_soft",
            "executable",
            "gold_executable",
            "gold_result_not_empty",
        ],
    )
    args = parser.parse_args()
    print(args)
    print()

    with open(os.path.join(args.result_dir, "result.json"), "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    t0 = time.time()
    dataset_loader = get_dataset_loader(result.dataset)
    dataset = await dataset_loader.get_split_async(
        result.split, databases=result.databases, subsample_size=result.subsample_size
    )
    print(
        f"Loaded {len(dataset.db_connectors)} databases from {result.dataset} {result.split} in {time.time() - t0:.2f} seconds."
    )
    metrics = [get_metric(m) for m in args.metrics]
    result = await evaluate_async(result, dataset, metrics, args.batch_size)

    result.to_directory(args.result_dir)
    print(f"Saved evaluated result to {args.result_dir}")

    print()
    print("Aggregated metrics:")
    for m in metrics:
        print(f"- {m.name}: {result.aggregated_metrics[m.name]:.4f}")

    if args.debug:
        print()
        print("=== DEBUG MODE === ")
        for task in result.tasks:
            print(f"{task.qid}: {task.metrics['bird_sql_ex']:.4f}")


if __name__ == "__main__":
    asyncio.run(main_async())
