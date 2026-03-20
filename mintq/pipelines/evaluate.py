import argparse
import asyncio
import os
import time
from tqdm.asyncio import tqdm_asyncio
from mintq import metric_registry, dataset_registry
import mintq
from mintq.schema import NL2QTaskOutput, NL2QRunResult, NL2QDataset, DbtTaskOutput
from mintq.db_connector import NL2QDBConnector, SQLConnector
from mintq.metrics import NL2QMetric, BaseMetricAggregator
from mintq.metrics.aggregators import (
    ByAmbrosiaTaxonomyTypeAggregator,
    SimpleAverageAggregator,
    RealScoreAggregator,
    ByDBAggregator,
    ByAmbigPointNumAggregator,
    ByBirdSQLDifficultyAggregator,
)
from mintq.utils import pprint_dict


async def compute_metrics_async(
    task: NL2QTaskOutput, metrics: list[NL2QMetric], db_connector: NL2QDBConnector
) -> NL2QTaskOutput:
    results = await asyncio.gather(*[m.compute_async(task, db_connector) for m in metrics])  # type: ignore
    task.eval_metrics = {}
    for m, r in zip(metrics, results):
        if isinstance(r, dict):
            task.eval_metrics.update(r)
        else:
            task.eval_metrics[m.name] = r
    return task


async def _build_dbt_working_connector(task: DbtTaskOutput, dataset: NL2QDataset) -> tuple[str, SQLConnector]:
    """Create a read-only connector to the predicted DuckDB for a dbt task."""
    original_conn = dataset.db_connectors.get(task.db)
    global_id = original_conn.global_id if original_conn is not None else f"spider2-dbt+{task.db}"
    conn = await SQLConnector.from_url_async(
        global_id=global_id,
        db_name=task.db,
        engine_type="sync",
        url=f"duckdb:///{task.pred_db_path}",
        max_concurrency_per_db=4,
        read_only=True,
        enable_caching=False,
    )
    return task.db, conn


async def evaluate_async(
    result: NL2QRunResult,
    dataset: NL2QDataset,
    metrics: list[NL2QMetric],
    batch_size: int,
    metric_aggregators: list[BaseMetricAggregator],
    verbose: bool = True,
) -> NL2QRunResult:
    dbt_db_connectors = {}
    dbt_tasks = [
        t for t in result.tasks if t.task_type == "dbt" and t.pred_db_path and os.path.exists(t.pred_db_path)
    ]
    if dbt_tasks:
        pairs = await asyncio.gather(*[_build_dbt_working_connector(t, dataset) for t in dbt_tasks])
        for db, conn in pairs:
            dbt_db_connectors[db] = conn

    def _get_db_connector(task: NL2QTaskOutput) -> NL2QDBConnector:
        if task.task_type == "dbt" and task.db in dbt_db_connectors:
            return dbt_db_connectors[task.db]
        return dataset.db_connectors[task.db]

    for i in range(0, len(result.tasks), batch_size):
        j = min(i + batch_size, len(result.tasks))
        batch = result.tasks[i:j]
        await tqdm_asyncio.gather(
            *[compute_metrics_async(task, metrics, _get_db_connector(task)) for task in batch],
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
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--metrics", nargs="+", default=None)
    args = parser.parse_args()
    print(args)
    print()

    mintq.configure()

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
    metric_names = args.metrics or metric_registry.list_names()
    metrics = []
    for m in metric_names:
        metric_cls = metric_registry.get_class(m)
        if any(output_type not in metric_cls.compatible_output_types for output_type in unique_output_types):
            print(
                f"WARNING: Metric {m} is not compatible with at least one output type in {unique_output_types}, skipping..."
            )
            continue
        if metric_cls.name == "schema_linking_stats":
            if all(task.extra_pred_info.linked_schema is None for task in result.tasks):
                print("WARNING: skipping schema_linking_stats because no linked schema found in any task")
                continue
        metrics.append(metric_cls())

    metric_aggregators: list[BaseMetricAggregator] = [
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

    if args.debug:
        print()
        print("=== DEBUG MODE === ")
        for task in result.tasks:
            md_path = os.path.join(args.result_dir, "readable", task.qid, "task_readable.md")
            if task.output_type == "dbt":
                print(f"{md_path}  spider2_duckdb_match: {task.eval_metrics['spider2_duckdb_match']:.4f}")
            else:
                print(
                    f"{md_path}  simple_ex: {task.eval_metrics['simple_ex']:.4f}  bird_sql_ex: {task.eval_metrics['bird_sql_ex']:.4f}"
                )


if __name__ == "__main__":
    asyncio.run(main_async())
