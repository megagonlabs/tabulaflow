import tabulaflow
from tabulaflow.research.benchmarks.arcs import ARCSDatasetLoader
import asyncio


async def main():
    tabulaflow.configure()
    dataset_loader = ARCSDatasetLoader()
    dataset = await dataset_loader.get_split_async("test")
    # tasks = [task for task in dataset.tasks if task.qid.endswith("-0")]
    # for task in tasks:
    #     task.qid = task.qid.replace("-0", "")

    all_sql = []
    for task in dataset.tasks:
        for gq in task.gold_queries:
            all_sql.append(gq.query)

    # sort by char length
    all_sql = sorted(all_sql, key=lambda x: len(x))
    print(f"total number of sql: {len(all_sql)}")
    print()
    print(f"shortest sql (len={len(all_sql[0])}):\n{all_sql[0]}")
    print()
    print(f"longest sql (len={len(all_sql[-1])}):\n{all_sql[-1]}")
    print()
    medium_sql = all_sql[len(all_sql) // 2 + 5]
    print(f"sql at median length (len={len(medium_sql)}):\n{medium_sql}")
    print()
    one_third_sql = all_sql[len(all_sql) * 2 // 3]
    print(f"sql at one-third length (len={len(one_third_sql)}):\n{one_third_sql}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
