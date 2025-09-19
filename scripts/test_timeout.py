import os
import asyncio
import time
import func_timeout
import sqlite3
from mintq.db_connector import SQLConnector


# os.environ["MINTQ_CACHE_ENABLED"] = "0"

SQLITE_PATH = "data/ARCS/databases/retails.sqlite"
SHORT_QUERY = "SELECT COUNT(*) FROM lineitem l1"
LONG_QUERY = "SELECT COUNT(DISTINCT l1.l_orderkey) FROM lineitem l1, lineitem l2"


async def test_timeout_aiosqlite() -> None:
    print("Testing test_timeout_aiosqlite...")
    connector = await SQLConnector.from_url_async(
        global_id="arcs+retails",
        db_name="retails",
        engine_type="async",
        url=f"sqlite+aiosqlite:///{SQLITE_PATH}",
        max_concurrency_per_db=4,
    )
    t0 = time.time()
    df = await connector.run_query_async(SHORT_QUERY, return_df=True, timeout=5)
    print(df.head())
    df = await connector.run_query_async(LONG_QUERY, return_df=True, timeout=5)
    print(df.head())
    print(f"Finished in {time.time() - t0:.2f} seconds")


async def test_timeout_sqlite() -> None:
    print("Testing test_timeout_sqlite...")
    connector = await SQLConnector.from_url_async(
        global_id="arcs+retails",
        db_name="retails",
        engine_type="sync",
        url=f"sqlite:///{SQLITE_PATH}",
        max_concurrency_per_db=4,
    )
    t0 = time.time()
    df = await connector.run_query_async(SHORT_QUERY, return_df=True, timeout=5)
    print(df.head())
    df = await connector.run_query_async(LONG_QUERY, return_df=True, timeout=5)
    print(df.head())
    print(f"Finished in {time.time() - t0:.2f} seconds")


def run_query(sqlite_path, sql):
    with sqlite3.connect(sqlite_path) as conn:
        return conn.execute(sql).fetchall()


async def test_func_timeout() -> None:
    print("Testing test_func_timeout...")
    rows = func_timeout.func_timeout(5, lambda: run_query(SQLITE_PATH, SHORT_QUERY))
    print(rows[:5])
    rows = func_timeout.func_timeout(5, lambda: run_query(SQLITE_PATH, LONG_QUERY))
    print(rows[:5])


if __name__ == "__main__":
    asyncio.run(test_func_timeout())
