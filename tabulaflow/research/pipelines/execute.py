import argparse
import logging
import time
import asyncio
import os
from typing import Literal
from tqdm.asyncio import tqdm_asyncio
from tabulaflow.research.benchmarks.registry import dataset_registry
from tabulaflow.research.query_execution import populate_task_exec_results
from tabulaflow.research.types import NL2QRunResult, NL2QDataset
from tabulaflow.data import Neo4jConnectorConfig, SQLConnectorConfig


async def execute_async(
    result: NL2QRunResult,
    dataset: NL2QDataset,
    batch_size: int,
    timeout: int | None = None,
    force: bool = False,
    verbose: bool = True,
) -> NL2QRunResult:
    """Populate missing query results in an experiment run.

    Args:
        result: Run result to update in place.
        dataset: Dataset providing database connectors.
        batch_size: Maximum tasks processed concurrently.
        timeout: Optional timeout for each query.
        force: Whether to replace existing execution results.
        verbose: Whether to display progress.

    Returns:
        The updated run result.
    """
    for i in range(0, len(result.tasks), batch_size):
        j = min(i + batch_size, len(result.tasks))
        batch = result.tasks[i:j]
        await tqdm_asyncio.gather(
            *[populate_task_exec_results(task, dataset.db_connectors[task.db], timeout, force) for task in batch],
            disable=not verbose,
        )
        if verbose:
            print(f"{j}/{len(result.tasks)} tasks populated.")
    return result


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir", nargs="?", default="output/test/")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-query-cache", action="store_true", help="Disable query result cache for this run")
    parser.add_argument("--log-level", type=str.upper, choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="WARNING")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)
    print(args)
    print()

    with open(os.path.join(args.result_dir, "result.json"), "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    t0 = time.time()
    query_cache_mode: Literal["off", "read_write"] = "off" if args.no_query_cache else "read_write"
    connector_config = (
        Neo4jConnectorConfig()
        if result.dataset == "cypherbench"
        else SQLConnectorConfig(query_cache_mode=query_cache_mode)
    )
    dataset_loader = dataset_registry.get_class(result.dataset)(  # type: ignore[call-arg]
        connector_config=connector_config
    )
    dataset = await dataset_loader.get_split_async(
        result.split,
        databases=result.databases,
        subsample_size=result.subsample_size,
        qids=[task.qid for task in result.tasks],
    )
    print(
        f"Loaded {len(dataset.db_connectors)} databases from {result.dataset} {result.split} in {time.time() - t0:.2f} seconds."
    )
    result = await execute_async(result, dataset, args.batch_size, args.timeout, args.force, verbose=True)
    result.to_directory(args.result_dir)
    print(f"Saved populated exec results to {args.result_dir}")


if __name__ == "__main__":
    asyncio.run(main_async())
