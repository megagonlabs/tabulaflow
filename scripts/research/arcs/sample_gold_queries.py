import argparse
import asyncio
import json
import random
from collections import Counter
from pathlib import Path

from tabulaflow.research.benchmarks.arcs import ARCSDatasetLoader


def sample_count(ambiguity_point_count: int) -> int:
    if ambiguity_point_count == 0:
        return 0
    if ambiguity_point_count == 1:
        return 3
    if ambiguity_point_count == 2:
        return 5
    return 7


async def main() -> None:
    parser = argparse.ArgumentParser(description="Sample executable gold queries for each unsampled ARCS task.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/ARCS/tasks/tasks_gold_intended_query_ids.json"))
    args = parser.parse_args()

    tasks = await ARCSDatasetLoader().get_tasks_async("test_unsampled")
    rng = random.Random(args.seed)
    sampled_ids: dict[str, list[str]] = {}
    counts_by_ambiguity_points: Counter[int] = Counter()

    for task in tasks:
        executable_ids = [
            query.id
            for query in task.gold_queries
            if query.exec_result is not None and query.exec_result.df is not None and not query.exec_result.df.empty
        ]
        count = min(sample_count(len(task.gold_ambiguity_points)), len(executable_ids))
        sampled_ids[task.qid] = rng.sample(executable_ids, count)
        counts_by_ambiguity_points[len(task.gold_ambiguity_points)] += count

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sampled_ids, indent=2) + "\n")
    print(f"Sampled {sum(map(len, sampled_ids.values()))} queries across {len(sampled_ids)} tasks")
    print(f"Queries by ambiguity-point count: {dict(sorted(counts_by_ambiguity_points.items()))}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
