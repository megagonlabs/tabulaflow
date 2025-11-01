from mintq.datahub.arcs import ARCSDatasetLoader
import json
from mintq.schema import AmbigNL2QTask
from pydantic import TypeAdapter
import os
import time
import asyncio


async def main():
    dataset_loader = ARCSDatasetLoader()
    dataset = await dataset_loader.get_split_async("test")
    tasks = [task for task in dataset.tasks if task.qid.endswith("-0")]
    for task in tasks:
        task.qid = task.qid.replace("-0", "")

    res = tasks

    output_path = os.path.join("data/ARCS/tasks", "tasks_unsampled.json")
    with open(output_path, "w") as f:
        f.write(TypeAdapter(list[AmbigNL2QTask]).dump_json(res, indent=2).decode())

    for task in res:
        task.to_directory(os.path.join("data/ARCS/tasks", "readable", task.qid))

    print(f"{len(res)} tasks saved to {output_path}")
    # print(f"Finished in {time.time() - t0:.2f} seconds.")


if __name__ == "__main__":
    asyncio.run(main())
