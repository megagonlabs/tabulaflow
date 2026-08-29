import argparse
import asyncio
import os
import time
from tqdm.asyncio import tqdm_asyncio
from tabulaflow.research.benchmarks.registry import dataset_registry
from tabulaflow.research.metrics.registry import metric_registry
from tabulaflow.research.types import NL2QTaskOutput, NL2QRunResult, NL2QDataset
from tabulaflow.data import DBConnector
from tabulaflow.research.metrics import MetricProtocol, MetricAggregatorProtocol
from tabulaflow.research.metrics.aggregators import (
    ByAmbrosiaTaxonomyTypeAggregator,
    SimpleAverageAggregator,
    RealScoreAggregator,
    ByDBAggregator,
    ByAmbigPointNumAggregator,
    ByBirdSQLDifficultyAggregator,
)
from tabulaflow.research.pipelines.utils import pprint_dict


async def compute_metrics_async(
    task: NL2QTaskOutput, metrics: list[MetricProtocol], db_connector: DBConnector | None
) -> NL2QTaskOutput:
    results = await asyncio.gather(*[m.compute_async(task, db_connector) for m in metrics])
    task.eval_metrics = {}
    for m, r in zip(metrics, results):
        if isinstance(r, dict):
            task.eval_metrics.update(r)
        else:
            task.eval_metrics[m.name] = r
    return task


async def evaluate_async(
    result: NL2QRunResult,
    dataset: NL2QDataset,
    metrics: list[MetricProtocol],
    batch_size: int,
    metric_aggregators: list[MetricAggregatorProtocol],
    verbose: bool = True,
) -> NL2QRunResult:
    for i in range(0, len(result.tasks), batch_size):
        j = min(i + batch_size, len(result.tasks))
        batch = result.tasks[i:j]
        await tqdm_asyncio.gather(
            *[compute_metrics_async(task, metrics, dataset.db_connectors.get(task.db)) for task in batch],
            disable=not verbose,
        )
        if verbose:
            print(f"{j}/{len(result.tasks)} tasks evaluated.")
    result.aggregated_eval_metrics = {}
    for aggregator in metric_aggregators:
        result.aggregated_eval_metrics.update(aggregator.aggregate(result))
    return result


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir", nargs="?", default="output/test/")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--metrics", nargs="+", default=None)
    args = parser.parse_args()
    print(args)
    print()

    with open(os.path.join(args.result_dir, "result.json"), "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(result.dataset)()
    dataset = await dataset_loader.get_split_async(
        result.split, databases=result.databases, subsample_size=result.subsample_size
    )
    print(
        f"Loaded {len(dataset.db_connectors)} databases from {result.dataset} {result.split} in {time.time() - t0:.2f} seconds."
    )

    unique_output_types = list(dict.fromkeys([task.output_type for task in result.tasks]))
    metric_names = args.metrics or dataset_loader.default_metrics
    metrics = []
    for m in metric_names:
        metric_cls = metric_registry.get_class(m)
        if any(output_type not in metric_cls.compatible_output_types for output_type in unique_output_types):
            continue
        if metric_cls.name == "schema_linking_stats":
            if all(task.extra_pred_info.linked_schema is None for task in result.tasks):
                continue
        metrics.append(metric_cls())

    metric_aggregators: list[MetricAggregatorProtocol] = [
        SimpleAverageAggregator(),
        RealScoreAggregator(),
        ByDBAggregator(),
        ByAmbigPointNumAggregator(),
        ByAmbrosiaTaxonomyTypeAggregator(),
        ByBirdSQLDifficultyAggregator(),
    ]
    result = await evaluate_async(result, dataset, metrics, args.batch_size, metric_aggregators)

    result.to_directory(args.result_dir, eval_metrics_in_summary=metric_names)
    print(f"Saved evaluated result to {args.result_dir}")

    print()
    print("Aggregated metrics:")
    print(pprint_dict(result.aggregated_eval_metrics))

    print()
    print("Task preview:")
    primary_metric = metrics[0].name if metrics else None
    for task in result.tasks[:10]:
        path = os.path.join(args.result_dir, "readable", task.qid, "task_readable.md")
        metric = (
            f"  {primary_metric}: {task.eval_metrics[primary_metric]}"
            if primary_metric is not None and primary_metric in task.eval_metrics
            else ""
        )
        print(f"{path}{metric}")
    remaining = len(result.tasks) - 10
    if remaining > 0:
        print(f"{remaining:,} more tasks are available in result_summary.csv, readable/, and result.json")


if __name__ == "__main__":
    asyncio.run(main_async())
