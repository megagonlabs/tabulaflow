import argparse
import random
import asyncio
import collections
from mintq.config import mintq_config
from mintq.datahub.arcs import ARCSDatasetLoader
import json


num_tasks_by_ambiguity_points = collections.defaultdict(int)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(args)
    print()

    mintq_config.setup_logging()
    total_tasks = 0

    random.seed(args.seed)

    dataset_loader = ARCSDatasetLoader()
    dataset = await dataset_loader.get_split_async("test_unsampled")

    qid_to_gold_query_ids = {}
    for task in dataset.tasks:
        gold_query_ids = [gq.id for gq in task.gold_queries if not gq.exec_result.df.empty]

        if len(task.gold_ambiguity_points) == 1:
            num_sample = 3
        elif len(task.gold_ambiguity_points) == 2:
            num_sample = 5
        elif len(task.gold_ambiguity_points) >= 3:
            num_sample = 7

        num_sample = min(num_sample, len(gold_query_ids))

        # gold_query_ids.remove(task.gold_intended_query_id)
        sampled_gold_query_ids = random.sample(gold_query_ids, num_sample)
        # sampled_gold_query_ids = [task.gold_intended_query_id] + sampled_gold_query_ids

        qid_to_gold_query_ids[task.qid] = sampled_gold_query_ids

        num_tasks_by_ambiguity_points[len(task.gold_ambiguity_points)] += num_sample
        total_tasks += len(sampled_gold_query_ids)

    print(f"Total number of tasks: {sum(len(gold_query_ids) for gold_query_ids in qid_to_gold_query_ids.values())}")
    print(num_tasks_by_ambiguity_points)

    print(f"Total number of tasks: {total_tasks}")

    with open("data/ARCS/tasks/tasks_gold_intended_query_ids.json", "w") as f:
        json.dump(qid_to_gold_query_ids, f, indent=2)

    print(f"Written {len(qid_to_gold_query_ids)} tasks to data/ARCS/tasks/tasks_gold_intended_query_ids.json")


if __name__ == "__main__":
    asyncio.run(main())
