from mintq.datahub.arcs import ARCSDatasetLoader
from mintq.schema import AmbigNL2QTask
from pydantic import TypeAdapter
import os
import asyncio


async def main():
    dataset_loader = ARCSDatasetLoader()
    dataset = await dataset_loader.get_split_async("test")
    # tasks = [task for task in dataset.tasks if task.qid.endswith("-0")]
    # for task in tasks:
    #     task.qid = task.qid.replace("-0", "")

    counts = {
        "semantic_column": 0,
        "semantic_table": 0,
        "semantic_value": 0,
        "semantic_computation": 0,
        "syntactic_column": 0,
        "syntactic_table": 0,
        "syntactic_value": 0,
        "syntactic_computation": 0,
    }
    for task in dataset.tasks:
        for ap in task.gold_ambiguity_points:
            counts[ap.ambiguity_type] += 1

    print(counts)


if __name__ == "__main__":
    asyncio.run(main())
