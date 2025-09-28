import argparse
import time
import asyncio
import os
from tqdm import trange
from mintq import dataset_registry
from mintq.schema import NL2QTaskOutput, NL2QRunResult, NL2QDataset
from mintq.db_connector import NL2QDBConnector


async def populate_task_async(
    task: NL2QTaskOutput,
    db_connector: NL2QDBConnector,
    timeout: int | None = None,
) -> NL2QTaskOutput:
    for prefix in ["gold", "pred"]:
        all_queries = []
        if getattr(task, f"{prefix}_query", None):
            all_queries.append(getattr(task, f"{prefix}_query"))
        if getattr(task, f"{prefix}_queries", None):
            all_queries += getattr(task, f"{prefix}_queries")
        queries_to_populate = [q for q in all_queries if not q.exec_result]
        results = await asyncio.gather(
            *[
                db_connector.run_query_async(q.query, parameters=q.parameter_values, timeout=timeout)
                for q in queries_to_populate
            ],
            return_exceptions=True,
        )
        for q, exec_result in zip(queries_to_populate, results):
            q.exec_result = exec_result
    return task


async def populate_exec_results_async(
    result: NL2QRunResult, dataset: NL2QDataset, batch_size: int, timeout: int | None = None
) -> NL2QRunResult:
    for i in trange(0, len(result.tasks), batch_size):
        await asyncio.gather(
            *[
                populate_task_async(task, dataset.db_connectors[task.db], timeout)
                for task in result.tasks[i : i + batch_size]
            ]
        )
    return result


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_dir", default="output/test/")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--debug", action="store_true")
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
    result = await populate_exec_results_async(result, dataset, args.batch_size, args.timeout)
    result.to_directory(args.result_dir)
    print(f"Saved populated exec results to {args.result_dir}")


if __name__ == "__main__":
    asyncio.run(main_async())
