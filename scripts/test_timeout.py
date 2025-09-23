import asyncio
import time
import func_timeout
import sqlite3
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine
import aiosqlite
from mintq.db_connector import SQLConnector
from concurrent.futures import ProcessPoolExecutor


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


async def run_query_in_process_pool(sqlite_path, sql):
    loop = asyncio.get_running_loop()
    process_pool = ProcessPoolExecutor(max_workers=4)
    return await asyncio.wait_for(
        loop.run_in_executor(process_pool, run_query, sqlite_path, sql),
        timeout=5,
    )


async def test_process_pool() -> None:
    print("Testing test_func_timeout...")
    rows = await run_query_in_process_pool(SQLITE_PATH, SHORT_QUERY)
    print(rows[:5])
    rows = await run_query_in_process_pool(SQLITE_PATH, LONG_QUERY)
    print(rows[:5])


async def run_with_interrupt(sqlite_path, sql, timeout):
    async with aiosqlite.connect(sqlite_path) as conn:
        # Schedule interrupt after timeout
        async def interrupt_after():
            await asyncio.sleep(timeout)
            await conn.interrupt()
            print("Interrupt sent!")

        interrupter = asyncio.create_task(interrupt_after())
        try:
            rows = []
            result = await conn.execute(sql)
            async for row in result:
                rows.append(row)
            return rows
        except sqlite3.OperationalError:
            raise TimeoutError(f"Query {sql} timed out after {timeout} seconds")
        finally:
            interrupter.cancel()


async def test_interrupt_aiosqlite() -> None:
    print("Testing test_interrupt_aiosqlite...")
    rows = await run_with_interrupt(SQLITE_PATH, SHORT_QUERY, 5)
    print(rows[:5])
    rows = await run_with_interrupt(SQLITE_PATH, LONG_QUERY, 5)
    print(rows[:5])


async def run_with_interrupt_sqlalchemy(sqlite_path, sql, timeout):
    engine = create_async_engine(f"sqlite+aiosqlite:///{sqlite_path}")

    async with engine.connect() as conn:

        async def interrupt_after():
            await asyncio.sleep(timeout)
            print("Interrupt sending...")
            print(type(conn))
            raw_conn = await conn.get_raw_connection()
            print(type(raw_conn))
            print(type(raw_conn.driver_connection))
            await raw_conn.driver_connection.interrupt()
            print("Interrupt sent!")

        interrupter = asyncio.create_task(interrupt_after())

        try:
            rows = []
            result = await conn.stream(sqlalchemy.text(sql))
            async for row in result:
                rows.append(row)
            return rows
        except sqlalchemy.exc.OperationalError:
            raise TimeoutError(f"Query {sql} timed out after {timeout} seconds")
        finally:
            interrupter.cancel()


async def test_interrupt_sqlalchemy() -> None:
    print("Testing test_interrupt_sqlalchemy...")
    rows = await run_with_interrupt_sqlalchemy(SQLITE_PATH, SHORT_QUERY, 5)
    print(rows[:5])
    rows = await run_with_interrupt_sqlalchemy(SQLITE_PATH, LONG_QUERY, 5)
    print(rows[:5])


if __name__ == "__main__":
    asyncio.run(test_timeout_aiosqlite())
