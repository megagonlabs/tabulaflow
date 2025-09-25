import argparse
import time
import asyncio
import os
from tqdm import trange
from mintq.db_connector import BaseAsyncDBConnector
from mintq.schema import NL2QTaskOutput, NL2QRunResult, NL2QDataset
from mintq.utils import aggregate_metrics
from mintq.datahub import get_dataset_loader
from mintq.metrics import get_metric, BaseAsyncNL2QMetric


async def compute_metrics_async(
    task: NL2QTaskOutput, metrics: list[BaseAsyncNL2QMetric], db_connector: BaseAsyncDBConnector
) -> NL2QTaskOutput:
    results = await asyncio.gather(*[m.compute_async(task=task, db_connector=db_connector) for m in metrics])
    task.eval_metrics = {m.name: r for m, r in zip(metrics, results)}
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
    result.aggregated_eval_metrics = aggregate_metrics(
        [task.eval_metrics for task in result.tasks], ops=["avg"], decimals=4
    )
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

    result.to_directory(args.result_dir, eval_metrics_in_summary=args.metrics)
    print(f"Saved evaluated result to {args.result_dir}")

    print()
    print("Aggregated metrics:")
    for m in metrics:
        print(f"- {m.name}: {result.aggregated_eval_metrics[m.name]['avg']:.4f}")

    if args.debug:
        print()
        print("=== DEBUG MODE === ")
        for task in result.tasks:
            print(f"{task.qid}: {task.eval_metrics['bird_sql_ex']:.4f}")


if __name__ == "__main__":
    asyncio.run(main_async())
