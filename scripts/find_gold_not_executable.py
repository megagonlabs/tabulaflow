import asyncio
import argparse
from tqdm.asyncio import tqdm_asyncio
from mintq.datahub import dataset_registry
from mintq.pipelines.populate_exec_results import populate_task_async


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="bird-sql")
    parser.add_argument("--split", default="dev_20240627")
    args = parser.parse_args()
    print(args)
    print()

    dataset_loader = dataset_registry.get_class(args.dataset)()
    dataset = await dataset_loader.get_split_async(args.split)

    await tqdm_asyncio.gather(*[populate_task_async(task, dataset.db_connectors[task.db]) for task in dataset.tasks])

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
                print(f"### QID: {task.qid}")
                print(task.gold_query.to_readable())

    print(f"Number of not executable gold queries: {num_not_executable}")


if __name__ == "__main__":
    asyncio.run(main())
