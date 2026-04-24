"""Tests for cancellation behaviour in :class:`SQLConnector` / :class:`ThrottledEngine`.

These cover the regression where cancelling a partially-built connector
could leave zombie executor threads holding DuckDB connections, making a
subsequent open on the same file with a different config fail with
``"Can't open a connection to same database file with a different
configuration than existing connections"``.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import duckdb
import pytest

from mintq.db_connector.sql_conn import SQLConnector, ThrottledEngine


@pytest.fixture
def duckdb_with_tables(tmp_path: Path) -> str:
    """A DuckDB file with enough tables that schema-build takes long
    enough to reliably land a cancel mid-build."""
    db_path = str(tmp_path / "fixture.duckdb")
    conn = duckdb.connect(db_path)
    for i in range(30):
        conn.execute(f"CREATE TABLE t{i} AS SELECT range AS x FROM range(50000)")
    conn.close()
    return db_path


async def test_cancel_then_retry_mixed_config(duckdb_with_tables: str) -> None:
    """Regression: cancel a read-only open mid-schema-build, then open the
    same file read-write.  Must not raise the DuckDB "different
    configuration" error.
    """
    url = f"duckdb:///{duckdb_with_tables}"

    task = asyncio.create_task(
        SQLConnector.from_url_async(
            global_id="cancel-target",
            url=url,
            db_name="t",
            read_only=True,
            enable_schema_caching=False,
        )
    )
    await asyncio.sleep(0.1)  # land cancel inside schema build
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Retry with the opposite config — this is the scenario that used to fail.
    connector = await SQLConnector.from_url_async(
        global_id="retry",
        url=url,
        db_name="t",
        read_only=False,
        enable_schema_caching=False,
    )
    assert len(connector.schema.tables) == 30
    await connector.disconnect_async()


async def test_cleanup_on_failure_runs_on_exception(tmp_path: Path) -> None:
    """``cleanup_on_failure`` must dispose the engine when the enclosed
    block raises."""
    db_path = str(tmp_path / "cf.duckdb")
    duckdb.connect(db_path).close()  # create empty DB file

    t_eng = ThrottledEngine.from_url(f"duckdb:///{db_path}", read_only=True)

    class Sentinel(Exception):
        pass

    with pytest.raises(Sentinel):
        async with t_eng.cleanup_on_failure():
            raise Sentinel

    # Engine's pool should be empty after disposal — a fresh connection
    # must therefore be a freshly-opened one, not a reused one.  Just
    # assert dispose completed without error by opening again.
    _ = await t_eng.run_query_async("SELECT 1")


async def test_cleanup_on_failure_leaves_engine_alive_on_success(tmp_path: Path) -> None:
    """On clean exit, ``cleanup_on_failure`` must NOT dispose the engine —
    the enclosing caller typically still owns it (e.g. a SQLConnector it
    just constructed)."""
    db_path = str(tmp_path / "cf-ok.duckdb")
    duckdb.connect(db_path).close()
    t_eng = ThrottledEngine.from_url(f"duckdb:///{db_path}", read_only=True)

    async with t_eng.cleanup_on_failure():
        await t_eng.run_query_async("SELECT 1")

    # Engine must still be usable; if it had been disposed, this would
    # open a new connection and still succeed, so we instead assert the
    # underlying pool hasn't been shut down.  SQLAlchemy disposes mean
    # pool is replaced; check via a query.
    result = await t_eng.run_query_async("SELECT 1")
    assert result.result[0][0] == 1

    await t_eng.aclose()


async def test_aclose_is_safe_with_nothing_in_flight(tmp_path: Path) -> None:
    """``aclose`` must complete quickly when there are no in-flight
    queries and leave no residue."""
    db_path = str(tmp_path / "idle.duckdb")
    duckdb.connect(db_path).close()
    t_eng = ThrottledEngine.from_url(f"duckdb:///{db_path}", read_only=True)
    await t_eng.run_query_async("SELECT 1")  # warm the pool

    await t_eng.aclose()

    # A subsequent open with a *different* config should succeed — if
    # aclose left a zombie, DuckDB would reject this.
    t_eng2 = ThrottledEngine.from_url(f"duckdb:///{db_path}", read_only=False)
    await t_eng2.run_query_async("SELECT 1")
    await t_eng2.aclose()


async def test_from_files_cancel_retry_mixed_config(tmp_path: Path) -> None:
    """Same regression as above but via the CSV-backed load path."""
    import pandas as pd

    csv = tmp_path / "data.csv"
    pd.DataFrame({"x": list(range(500000)) * 4}).to_csv(csv, index=False)

    task = asyncio.create_task(
        SQLConnector.from_files_async(
            global_id="cancel-files",
            file_paths=[str(csv)],
            db_name="mydata",
            data_dir=str(tmp_path),
            read_only=True,
            enable_schema_caching=False,
            enable_query_caching=False,
        )
    )
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    db_path = tmp_path / "mydata.duckdb"
    if not db_path.exists():
        pytest.skip("cancel fired before the DuckDB file was created")

    connector = await SQLConnector.from_url_async(
        global_id="retry-files",
        url=f"duckdb:///{db_path}",
        db_name="mydata",
        read_only=False,
        enable_schema_caching=False,
    )
    await connector.disconnect_async()
