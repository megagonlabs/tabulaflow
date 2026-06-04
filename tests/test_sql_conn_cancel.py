"""Tests for cancellation behaviour in :class:`SQLConnector` / :class:`ThrottledEngine`.

These cover the regression where cancelling a partially-built connector
could leave zombie executor threads holding DuckDB connections, making a
subsequent open on the same file with a different config fail with
``"Can't open a connection to same database file with a different
configuration than existing connections"``.
"""

import asyncio
from pathlib import Path

import duckdb
import pytest

from tabulaflow.db_connector.sql_conn import SQLConnector, ThrottledEngine


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


async def test_aclose_is_safe_with_nothing_in_flight(tmp_path: Path) -> None:
    """``aclose`` must complete quickly when there are no in-flight
    queries and leave no residue."""
    db_path = str(tmp_path / "idle.duckdb")
    duckdb.connect(db_path).close()
    t_eng = ThrottledEngine.from_url(f"duckdb:///{db_path}", read_only=True)
    await t_eng.execute_async("SELECT 1")  # warm the pool

    await t_eng.aclose()

    # A subsequent open with a *different* config should succeed — if
    # aclose left a zombie, DuckDB would reject this.
    t_eng2 = ThrottledEngine.from_url(f"duckdb:///{db_path}", read_only=False)
    await t_eng2.execute_async("SELECT 1")
    await t_eng2.aclose()


async def test_load_files_cancel_then_retry(tmp_path: Path) -> None:
    """``load_files`` runs its load phase in a subprocess; a cancel should
    kill that subprocess, leave no leaked DuckDB state, and allow a fresh
    retry to the same path to succeed and load all rows.
    """
    import pandas as pd

    from tabulaflow.db_connector.loaders.files import load_files

    csv = tmp_path / "data.csv"
    pd.DataFrame({"x": list(range(200000)) * 4}).to_csv(csv, index=False)

    task = asyncio.create_task(
        load_files(
            global_id="cancel-files",
            file_paths=[str(csv)],
            db_name="mydata",
            data_dir=str(tmp_path),
            read_only=True,
            enable_schema_caching=False,
            enable_query_caching=False,
        )
    )
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Retry — fresh load, same db_name (same on-disk path).  If the
    # previous subprocess leaked a file lock, this would fail.
    connector = await load_files(
        global_id="retry-files",
        file_paths=[str(csv)],
        db_name="mydata",
        data_dir=str(tmp_path),
        read_only=True,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    result = await connector.run_query_async("SELECT COUNT(*) FROM data")
    assert result.df is not None and result.df.iloc[0, 0] == 800000
    await connector.disconnect_async()


async def test_write_dataframe_cancel_rolls_back(tmp_path: Path) -> None:
    """Cancelling a ``write_dataframe_async`` mid-flight must abort the
    in-flight write and roll back the transaction — the target table
    must not exist after the cancel propagates.
    """
    import pandas as pd

    async def body() -> None:
        db_path = str(tmp_path / "w.duckdb")
        duckdb.connect(db_path).close()
        connector = await SQLConnector.from_url_async(
            global_id="w",
            url=f"duckdb:///{db_path}",
            db_name="t",
            read_only=False,
            enable_schema_caching=False,
            enable_query_caching=False,
        )
        df = pd.DataFrame({"x": range(500_000), "y": range(500_000)})

        task = asyncio.create_task(connector.write_dataframe_async(df, "mytbl", mode="replace"))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        r = await connector.run_query_async(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'mytbl' AND table_schema = 'main'"
        )
        assert r.df is not None and r.df.iloc[0, 0] == 0
        await connector.disconnect_async()

    # Bound the test: a regression that leaves the cancelled write's
    # connection wedged would otherwise stall ``aclose``'s 5s drain loop
    # and look like a hang.
    await asyncio.wait_for(body(), timeout=20)


async def test_cancel_isolates_to_one_query(tmp_path: Path) -> None:
    """Cancelling one in-flight query must not abort other queries
    running concurrently on the same connector — guards against
    accidentally calling the bulk ``_cancel_inflight`` from a per-call
    cancellation site.
    """

    async def body() -> None:
        db_path = str(tmp_path / "iso.duckdb")
        duckdb.connect(db_path).close()
        connector = await SQLConnector.from_url_async(
            global_id="iso",
            url=f"duckdb:///{db_path}",
            db_name="t",
            read_only=False,
            enable_schema_caching=False,
            enable_query_caching=False,
        )

        slow_sql = "CREATE TABLE {name} AS SELECT range AS x, range * 2 AS y FROM range(5_000_000)"
        t_cancel = asyncio.create_task(connector.run_query_async(slow_sql.format(name="cancelled_table")))
        t_keep = asyncio.create_task(connector.run_query_async(slow_sql.format(name="kept_table")))

        await asyncio.sleep(0.1)
        t_cancel.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t_cancel

        # The non-cancelled query must still complete normally.
        keep_result = await t_keep
        assert keep_result.error is None

        r = await connector.run_query_async(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name"
        )
        assert r.df is not None
        tables = list(r.df.iloc[:, 0])
        assert "kept_table" in tables
        assert "cancelled_table" not in tables

        await connector.disconnect_async()

    await asyncio.wait_for(body(), timeout=20)


# ---------------------------------------------------------------------------
# Async-engine path: aiosqlite (no protocol-level cancel — strategy must
# fire ``conn.interrupt()`` for either timeout or cancel to work).
# ---------------------------------------------------------------------------


async def _make_async_sqlite_connector(tmp_path: Path) -> SQLConnector:
    """Build a SQLConnector backed by aiosqlite with a table large enough
    that a recursive CTE-style query takes long enough to land a cancel."""
    import sqlalchemy

    db_path = str(tmp_path / "async.sqlite")
    # Pre-create with a "numbers" table we can self-cross-join for slowness.
    eng = sqlalchemy.create_engine(f"sqlite:///{db_path}")
    with eng.connect() as conn:
        conn.execute(sqlalchemy.text("CREATE TABLE numbers (n INTEGER)"))
        conn.execute(
            sqlalchemy.text(
                "WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<5000) "
                "INSERT INTO numbers SELECT n FROM seq"
            )
        )
        conn.commit()
    eng.dispose()

    return await SQLConnector.from_url_async(
        global_id="async-sqlite",
        url=f"sqlite+aiosqlite:///{db_path}",
        db_name="t",
        read_only=True,
        enable_schema_caching=False,
    )


# A self-cross-join over a 5K-row table → 25 million rows.  Slow enough
# that a 50ms cancel reliably lands while it's running, fast enough that
# tests don't drag if the cancel mechanism breaks (we cap with wait_for
# in each test).
_SLOW_AIOSQLITE_QUERY = "SELECT COUNT(*) FROM numbers a, numbers b, numbers c"


async def test_aiosqlite_cancel_aborts_query(tmp_path: Path) -> None:
    """Cancelling a long aiosqlite query must trigger ``interrupt()`` on
    the underlying sqlite3 connection and raise ``CancelledError``
    promptly — without the strategy, aiosqlite's worker thread would
    keep running until the query naturally completes."""

    async def body() -> None:
        connector = await _make_async_sqlite_connector(tmp_path)
        try:
            task = asyncio.create_task(connector.run_query_async(_SLOW_AIOSQLITE_QUERY))
            await asyncio.sleep(0.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            await connector.disconnect_async()

    await asyncio.wait_for(body(), timeout=20)


async def test_aiosqlite_timeout_aborts_query(tmp_path: Path) -> None:
    """``timeout=`` on aiosqlite must use the same ``interrupt()``
    primitive — the unified path treats timeout as just "cancel after N
    seconds" and routes through the strategy.  ``SQLConnector`` surfaces
    query-level failures as ``result.error`` (not raised), so we assert
    on the surfaced error rather than ``pytest.raises``.
    """

    async def body() -> None:
        connector = await _make_async_sqlite_connector(tmp_path)
        try:
            result = await connector.run_query_async(_SLOW_AIOSQLITE_QUERY, timeout=1)
            assert result.error is not None
            assert result.error.exc_type == "TimeoutError"
        finally:
            await connector.disconnect_async()

    # Outer cap well above the inner timeout to leave room for cleanup.
    await asyncio.wait_for(body(), timeout=20)
