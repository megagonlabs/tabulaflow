import argparse
import copy
import time
import asyncio
import random
import pandas as pd
from tqdm import trange
from mintq.db_connector import BaseAsyncDBConnector
from mintq.schema import NL2QTaskOutput, NL2QRunResult, NL2QDataset
from mintq.utils import avg_and_round, save_csv
from mintq.datahub import get_dataset_loader
from mintq.metric import get_metric, BaseAsyncNL2QMetric


async def populate_exec_results_async(
    item: NL2QTaskOutput,
    db_connector: BaseAsyncDBConnector,
) -> NL2QTaskOutput:
    if item.task_type != "simple":
        raise ValueError("Only simple NL2Q tasks are supported currently")

    item = copy.deepcopy(item)

    if item.gold_queries:
        dfs = await asyncio.gather(
            *[db_connector.run_query_async(query, return_df=True) for query in item.gold_queries],
            return_exceptions=True,
        )
        item.gold_exec_results = [df.to_dict(orient="records") for df in dfs if isinstance(df, pd.DataFrame)]
    else:
        if not item.gold_exec_results:
            raise ValueError("No gold queries or gold execution results provided")

    try:
        df = await db_connector.run_query_async(item.pred_query, return_df=True)
        item.pred_exec_result = df.to_dict(orient="records")
    except Exception:
        item.pred_exec_result = None
    return item


async def compute_metrics_async(
    item: NL2QTaskOutput, metrics: list[BaseAsyncNL2QMetric], db_connector: BaseAsyncDBConnector
) -> NL2QTaskOutput:
    item = await populate_exec_results_async(item, db_connector)
    for m in metrics:
        item.metrics[m.name] = await m.compute_async(task=item, db_connector=db_connector)
    return item


async def evaluate_async(
    result: NL2QRunResult, dataset: NL2QDataset, metrics: list[BaseAsyncNL2QMetric], batch_size: int
) -> NL2QRunResult:
    result = copy.deepcopy(result)

    # Shuffle the result to reduce concurent query execution on the same database
    qids = {item.qid: i for i, item in enumerate(result.tasks)}
    random.seed(42)
    random.shuffle(result.tasks)

    tasks_with_metrics = []
    for i in trange(0, len(result.tasks), batch_size):
        batch = result.tasks[i : i + batch_size]
        batch_with_metrics = await asyncio.gather(
            *[compute_metrics_async(item, metrics, dataset.db_connectors[item.db]) for item in batch]
        )
        tasks_with_metrics += batch_with_metrics

    # Sort the result so that the order is the same as the original result
    tasks_with_metrics.sort(key=lambda x: qids[x.qid])
    result.tasks = tasks_with_metrics

    aggregated_metrics = {m.name: avg_and_round([item.metrics[m.name] for item in tasks_with_metrics]) for m in metrics}
    result.aggregated_metrics.update(aggregated_metrics)
    return result


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_json", default="output/test/result.json")
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

    with open(args.result_json, "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    t0 = time.time()
    dataset_loader = get_dataset_loader(result.dataset)
    dataset = await dataset_loader.get_split_async(result.split_id, databases=result.databases)
    print(
        f"Loaded {len(dataset.db_connectors)} databases from {result.dataset} {result.split_id} set in {time.time() - t0:.2f} seconds."
    )

    metrics = [get_metric(m) for m in args.metrics]
    result = await evaluate_async(result, dataset, metrics, args.batch_size)

    print()
    print("Aggregated metrics:")
    for m in metrics:
        print(f"- {m.name}: {result.aggregated_metrics[m.name]:.4f}")

    output_path = args.result_json.replace(".json", "_with_metrics.json")
    with open(output_path, "w") as fout:
        fout.write(result.model_dump_json(indent=2))
    print()
    print(f"Saved result with metrics to {output_path}")

    if result.dataset == "spider2-snow":
        metrics_to_include = ["spider2_ex"]
    elif result.dataset == "bird-sql":
        metrics_to_include = ["bird_sql_ex"]
    else:
        metrics_to_include = ["spider2_ex", "bird_sql_ex"]
    csv_path = args.result_json.replace(".json", "_with_metrics.csv")
    save_csv(result, csv_path, metrics_to_include)
    print(f"Saved csv to {csv_path}")

    if args.debug:
        print()
        print("=== DEBUG MODE === ")
        for task in result.tasks:
            print(f"{task.qid}: {task.metrics['bird_sql_ex']:.4f}")


if __name__ == "__main__":
    asyncio.run(main_async())
