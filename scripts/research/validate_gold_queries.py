import argparse
import asyncio
import time

from tqdm.asyncio import tqdm_asyncio

from tabulaflow.research.benchmarks import dataset_registry
from tabulaflow.research.query_execution import populate_task_exec_results


async def main() -> None:
    parser = argparse.ArgumentParser(description="Execute and validate every gold query in a benchmark split.")
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    started_at = time.perf_counter()
    dataset = await dataset_registry.get_class(args.dataset)().get_split_async(args.split)
    print(
        f"Loaded {len(dataset.tasks)} tasks and {len(dataset.db_connectors)} databases "
        f"in {time.perf_counter() - started_at:.2f} seconds"
    )

    for start in range(0, len(dataset.tasks), args.batch_size):
        batch = dataset.tasks[start : start + args.batch_size]
        await tqdm_asyncio.gather(
            *(populate_task_exec_results(task, dataset.db_connectors[task.db], force=True) for task in batch)
        )

    failures = []
    for task in dataset.tasks:
        if task.task_type == "simple":
            queries = [task.gold_query]
        elif task.task_type == "ambig":
            queries = task.gold_queries
        else:
            raise ValueError(f"Task {task.qid} has no gold SQL queries")
        for query in queries:
            if query.exec_result is None or query.exec_result.error is not None:
                failures.append((task, query))

    for task, query in failures:
        print()
        print(f"### QID: {task.qid}  DB: {task.db}")
        print(query.to_markdown())
    print(f"\n{len(failures)} gold queries failed validation")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
