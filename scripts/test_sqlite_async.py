# mypy: ignore-errors
import time
import asyncio
from typing import Any
from mintq.datahub import dataset_registry
from mintq.db_connector import BaseSQLDBConnector, SQLConnector
from mintq.toolhub import RunQueryTool

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

query1 = """
SELECT COUNT(DISTINCT s.s_suppkey) AS supplier_count
FROM supplier s
JOIN nation n ON s.s_nationkey = n.n_nationkey
JOIN lineitem l_air ON l_air.l_suppkey = s.s_suppkey AND l_air.l_shipmode = 'AIR'
JOIN lineitem l_rail ON l_rail.l_suppkey = s.s_suppkey AND l_rail.l_shipmode = 'RAIL'
WHERE n.n_name = 'UNITED STATES';
"""

invalid_query = """
SELECT * FROM asdfasdfasdf;
"""

query2 = """
SELECT COUNT(DISTINCT t1.account_id)
FROM trans t1
JOIN trans t2
ON t1.account_id = t2.account_id
AND t2.date > t1.date
AND julianday(t2.date) - julianday(t1.date) <= :days_threshold
WHERE t2.balance > t1.balance * (1 + :percentage_increase);
"""

def print_current_time() -> None:
    print(f"Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")


async def run_query(db_connector: BaseSQLDBConnector, query: str, parameters: dict[str, Any], timeout: int) -> None:
    print_current_time()
    # t0 = time.time()
    result = await db_connector.run_query_async(query, parameters, timeout=timeout)
    print(result)
    print(result.latency_seconds)
    print_current_time()


async def main() -> None:
    dataset_loader = dataset_registry.get_class("arcs")()
    # dataset = await dataset_loader.get_split_async("dev")
    # db_connector: SQLConnector = dataset.db_connectors["retails"]
    db_connectors = await dataset_loader.get_db_connectors_async("dev")
    db_connector = db_connectors["retails"]
    # db_connector._t_eng.dbms_semaphore = None
    # db_connector._t_eng.db_semaphore = None
    run_query_tool = RunQueryTool(db_connector, timeout=120)
    # await run_query(db_connector, query, 60)
    t0 = time.time()
    params = {'days_threshold': 7, 'percentage_increase': 0.5}
    await asyncio.gather(*[run_query(db_connector, query2, params, 120) for _ in range(16)])
    # result = await run_query_tool(invalid_query)
    # print(result)
    print(f"Total time taken: {time.time() - t0} seconds")


if __name__ == "__main__":
    asyncio.run(main())
