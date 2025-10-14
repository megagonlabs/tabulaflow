import time
import asyncio
from mintq.datahub import dataset_registry
from mintq.db_connector import SQLConnector
from mintq.toolhub import RunQueryTool


async def main() -> None:
    latency = []
    dataset_loader = dataset_registry.get_class("arcs")()
    dataset = await dataset_loader.get_split_async("dev")
    db_connector: SQLConnector = dataset.db_connectors["retails"]
    for task in dataset.tasks:
        for gq in task.gold_queries:
            latency.append((gq.exec_result.latency_seconds, task.qid, gq.id, gq.query))
    latency = sorted(latency, key=lambda x: -x[0])
    for latency, qid, id, query in latency[:10]:
        print(f"{qid}-{id}: {latency:.2f} seconds")
        print(query)
        exec_result = await db_connector.run_query_async(query, timeout=None)
        print(f"Real latency: {exec_result.latency_seconds:.2f} seconds")
        print()


if __name__ == "__main__":
    asyncio.run(main())
