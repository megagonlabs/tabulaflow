# mypy: ignore-errors
import asyncio
from mintq.datahub import dataset_registry


async def main() -> None:
    latency = []
    dataset_loader = dataset_registry.get_class("arcs")()
    dataset = await dataset_loader.get_split_async("dev")
    # dataset.tasks = [task for task in dataset.tasks if task.qid in ["061"]]
    for task in dataset.tasks:
        for gq in task.gold_queries:
            latency.append((gq.exec_result.latency_seconds, task, gq))
    latency = sorted(latency, key=lambda x: -x[0])
    for latency, task, gq in latency[:10]:
        print(f"{task.qid}-{gq.id}: {latency:.2f} seconds")
        print(gq.query)
        print(gq.parameter_values)
        db_connector = dataset.db_connectors[task.db]
        exec_result = await db_connector.run_query_async(gq.query, gq.parameter_values, timeout=None)
        if exec_result.error:
            print(exec_result.error)
        print(f"Real latency: {exec_result.latency_seconds:.2f} seconds")
        print()


if __name__ == "__main__":
    asyncio.run(main())
