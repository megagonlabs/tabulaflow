import os
import asyncio
import time
from mintq.db_connector import SQLConnector


# os.environ["MINTQ_CACHE_ENABLED"] = "0"


async def test_timeout_aiosqlite() -> None:
    print("Testing test_timeout_aiosqlite...")
    connector = await SQLConnector.from_url_async(
        global_id="arcs+retails",
        db_name="retails",
        engine_type="async",
        url="sqlite+aiosqlite:///data/ARCS/databases/retails.sqlite",
        max_concurrency_per_db=4,
    )
    t0 = time.time()
    df = await connector.run_query_async(
        "SELECT COUNT(*) FROM lineitem l1", return_df=True, timeout=5
    )
    print(df.head())
    df = await connector.run_query_async(
        "SELECT COUNT(DISTINCT l1.l_orderkey) FROM lineitem l1, lineitem l2", return_df=True, timeout=5
    )
    print(df.head())
    print(f"Finished in {time.time() - t0:.2f} seconds")


async def test_timeout_sqlite() -> None:
    print("Testing test_timeout_sqlite...")
    connector = await SQLConnector.from_url_async(
        global_id="arcs+retails",
        db_name="retails",
        engine_type="sync",
        url="sqlite:///data/ARCS/databases/retails.sqlite",
        max_concurrency_per_db=4,
    )
    t0 = time.time()
    df = await connector.run_query_async(
        "SELECT COUNT(*) FROM lineitem l1", return_df=True, timeout=5
    )
    print(df.head())
    df = await connector.run_query_async(
        "SELECT COUNT(DISTINCT l1.l_orderkey) FROM lineitem l1, lineitem l2", return_df=True, timeout=5
    )
    print(df.head())
    print(f"Finished in {time.time() - t0:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(test_timeout_aiosqlite())
