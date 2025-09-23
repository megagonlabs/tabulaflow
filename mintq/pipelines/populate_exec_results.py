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


async def populate_task_async(
    item: NL2QTaskOutput,
    db_connector: BaseAsyncDBConnector,
    timeout: int | None = None,
) -> NL2QTaskOutput:
    for prefix in ["gold", "pred"]:
        all_queries = []
        if getattr(item, f"{prefix}_query", None):
            all_queries.append(item.gold_query)
        if getattr(item, f"{prefix}_queries", None):
            all_queries += item.gold_queries
        results = await asyncio.gather(
            *[
                db_connector.run_query_async(q.query, parameters=q.parameter_values, timeout=timeout)
                for q in all_queries
            ],
            return_exceptions=True,
        )
        for q, exec_result in zip(all_queries, results):
            q.exec_result = exec_result
    return item


async def populate_exec_results_async(result: NL2QRunResult, dataset: NL2QDataset, batch_size: int) -> NL2QRunResult:
    for i in trange(0, len(result.tasks), batch_size):
        await asyncio.gather(
            *[populate_task_async(item, dataset.db_connectors[item.db]) for item in result.tasks[i : i + batch_size]]
        )
    return result


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--debug", action="store_true")
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
    result = await populate_exec_results_async(result, dataset, args.batch_size)
    result.to_directory(args.result_dir)
    print(f"Saved populated exec results to {args.result_dir}")


if __name__ == "__main__":
    asyncio.run(main_async())
