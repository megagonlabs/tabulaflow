import argparse
import random
import asyncio
import collections
from mintq.datahub.arcs import ARCSDatasetLoader
import json


num_tasks_by_ambiguity_points = collections.defaultdict(int)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(args)
    print()

    random.seed(args.seed)

    dataset_loader = ARCSDatasetLoader()
    dataset = await dataset_loader.get_split_async("test")

    qid_to_gold_query_ids = {}
    for task in dataset.tasks:
        gold_query_ids = [gq.id for gq in task.gold_queries]

        if len(task.gold_ambiguity_points) == 1:
            num_sample = 2
        elif len(task.gold_ambiguity_points) == 2:
            num_sample = 3
        elif len(task.gold_ambiguity_points) >= 3:
            num_sample = 5

        num_sample = min(num_sample, len(gold_query_ids))

        gold_query_ids.remove(task.gold_intended_query_id)
        sampled_gold_query_ids = random.sample(gold_query_ids, num_sample - 1)
        sampled_gold_query_ids = [task.gold_intended_query_id] + sampled_gold_query_ids

        qid_to_gold_query_ids[task.qid] = sampled_gold_query_ids

        num_tasks_by_ambiguity_points[len(task.gold_ambiguity_points)] += num_sample

    print(f"Total number of tasks: {sum(len(gold_query_ids) for gold_query_ids in qid_to_gold_query_ids.values())}")
    print(num_tasks_by_ambiguity_points)

    with open("data/ARCS/tasks/sampled_gold_intended_query_ids.json", "w") as f:
        json.dump(qid_to_gold_query_ids, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
