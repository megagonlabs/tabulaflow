import time
import asyncio
from mintq.datahub import dataset_registry
from mintq.db_connector import SQLConnector

query = """
SELECT n.n_name AS nation, SUM(l.l_extendedprice) AS total_revenue
FROM lineitem l
JOIN orders o ON l.l_orderkey = o.o_orderkey
JOIN customer c ON o.o_custkey = c.c_custkey
JOIN nation n ON c.c_nationkey = n.n_nationkey
WHERE o.o_orderdate >= '1995-01-01' AND o.o_orderdate < '1996-01-01'
GROUP BY n.n_name
ORDER BY n.n_name;
"""


def print_current_time() -> None:
    print(f"Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")


async def run_query(db_connector: SQLConnector, query: str, timeout: int) -> None:
    print_current_time()
    # t0 = time.time()
    result = await db_connector.run_query_async(query, timeout=timeout)
    # print(result)
    print(result.latency_seconds)
    print_current_time()


async def main() -> None:
    dataset_loader = dataset_registry.get_class("arcs")()
    dataset = await dataset_loader.get_split_async("dev")
    db_connector: SQLConnector = dataset.db_connectors["retails"]
    db_connector._t_eng.dbms_semaphore = None
    db_connector._t_eng.db_semaphore = None
    # await run_query(db_connector, query, 60)
    t0 = time.time()
    await asyncio.gather(*[run_query(db_connector, query, 60) for _ in range(10)])
    print(f"Total time taken: {time.time() - t0} seconds")


if __name__ == "__main__":
    asyncio.run(main())
