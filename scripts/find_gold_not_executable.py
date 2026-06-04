import asyncio
import argparse
import time
from tqdm.asyncio import tqdm_asyncio
import tabulaflow
from tabulaflow.datahub import dataset_registry
from tabulaflow.pipelines.populate_exec_results import populate_task_async


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--batch_size", type=int, default=8)
    args = parser.parse_args()
    print(args)
    print()

    tabulaflow.configure()

    t0 = time.time()
    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split)
    print(
        f"Loaded {len(dataset.tasks)} tasks and {len(dataset.db_connectors)} databases from {args.dataset} ({args.split}) in {time.time() - t0:.2f} seconds."
    )
    for i in range(0, len(dataset.tasks), args.batch_size):
        j = min(i + args.batch_size, len(dataset.tasks))
        batch = dataset.tasks[i:j]
        await tqdm_asyncio.gather(
            *[populate_task_async(task, dataset.db_connectors[task.db], force=True) for task in batch]
        )
        print(f"{j}/{len(dataset.tasks)} tasks populated.")

    num_not_executable = 0
    for task in dataset.tasks:
        if task.task_type == "simple":
            all_queries = [task.gold_query]
        elif task.task_type == "ambig":
            all_queries = task.gold_queries
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")

        for query in all_queries:
            if query.exec_result.error is not None:
                num_not_executable += 1
                print()
                print()
                print(f"### QID: {task.qid}  DB: {task.db}")
                print(query.to_readable())

    print(f"Number of not executable gold queries: {num_not_executable}")


if __name__ == "__main__":
    asyncio.run(main())
