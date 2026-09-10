"""Tests for cancellation behaviour in :class:`SQLConnector` / :class:`ThrottledEngine`.

These cover the regression where cancelling a partially-built connector
could leave zombie executor threads holding DuckDB connections, making a
subsequent open on the same file with a different config fail with
``"Can't open a connection to same database file with a different
configuration than existing connections"``.
"""

import asyncio
from pathlib import Path
import threading
from typing import Any, cast

import duckdb
import pytest
import sqlalchemy

import tabulaflow.data.sql as sql_module
from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector, ThrottledEngine


async def test_cancel_during_inspection_then_retry_mixed_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inspector work must release its read-only DuckDB connection before retry."""
    db_path = tmp_path / "hf_cache.duckdb"
    duckdb.connect(str(db_path)).execute("CREATE TABLE documents (id INTEGER)").close()
    url = f"duckdb:///{db_path}"
    entered_inspection = threading.Event()
    inspector_abort_called = asyncio.Event()
    real_inspect = getattr(sql_module, "inspect")
    real_abort_handle = ThrottledEngine._abort_handle

    async def track_abort(engine: ThrottledEngine, handle: Any) -> None:
        inspector_abort_called.set()
        await real_abort_handle(engine, handle)

    class SlowInspector:
        def __init__(self, bind: Any) -> None:
            self._bind = bind
            self._inner = real_inspect(bind)

        def get_schema_names(self) -> list[str]:
            entered_inspection.set()
            self._bind.exec_driver_sql(
                """
                WITH RECURSIVE loop(x) AS (
                    VALUES(0)
                    UNION ALL
                    SELECT (x + 1) % 2 FROM loop
                )
                SELECT COUNT(*) FROM loop
                """
            ).scalar()
            return cast(list[str], self._inner.get_schema_names())

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

    monkeypatch.setattr(sql_module, "inspect", SlowInspector)
    monkeypatch.setattr(ThrottledEngine, "_abort_handle", track_abort)
    task = asyncio.create_task(
        SQLConnector.from_url_async(
            global_id="hf-cancel-target",
            url=url,
            display_name="documents",
            read_only=True,
            config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
        )
    )
    await asyncio.wait_for(asyncio.to_thread(entered_inspection.wait), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert inspector_abort_called.is_set()

    monkeypatch.setattr(sql_module, "inspect", real_inspect)
    connector = await SQLConnector.from_url_async(
        global_id="hf-retry",
        url=url,
        display_name="documents",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    assert [table.name for table in connector.schema.tables] == ["documents"]
    await connector.close_async()


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


async def test_load_files_cancel_then_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A cancelled load must leave no DuckDB state and allow a fresh retry."""
    import pandas as pd

    from tabulaflow.data.loaders.files import load_files

    csv = tmp_path / "data.csv"
    pd.DataFrame({"x": [1]}).to_csv(csv, index=False)
    load_started = asyncio.Event()
    release_load = asyncio.Event()
    real_run_query = SQLConnector.run_query_async
    first_load = True

    async def pause_first_load(
        connector: SQLConnector,
        query: Any,
        parameters: Any = (),
        timeout: Any = None,
    ) -> Any:
        nonlocal first_load
        if first_load and str(query).startswith("CREATE TABLE"):
            first_load = False
            load_started.set()
            await release_load.wait()
        return await real_run_query(connector, query, parameters, timeout)

    monkeypatch.setattr(SQLConnector, "run_query_async", pause_first_load)

    task = asyncio.create_task(
        load_files(
            global_id="cancel-files",
            file_paths=[str(csv)],
            display_name="mydata",
            data_dir=str(tmp_path),
            read_only=True,
            config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
        )
    )
    await asyncio.wait_for(load_started.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Retry — fresh load, same global_id (same on-disk path).  If the
    # previous subprocess leaked a file lock, this would fail.
    connector = await load_files(
        global_id="cancel-files",
        file_paths=[str(csv)],
        display_name="mydata",
        data_dir=str(tmp_path),
        read_only=True,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    result = await connector.run_query_async("SELECT COUNT(*) FROM data")
    assert result.df is not None and result.df.iloc[0, 0] == 1
    await connector.close_async()


async def test_load_files_separates_display_name_from_storage_path(tmp_path: Path) -> None:
    import pandas as pd

    from tabulaflow.data.loaders.files import load_files

    csv = tmp_path / "data.csv"
    pd.DataFrame({"x": [1]}).to_csv(csv, index=False)
    data_dir = tmp_path / "loaded"

    connector = await load_files(
        global_id="file-source",
        file_paths=[str(csv)],
        display_name="../human label",
        data_dir=str(data_dir),
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )

    storage_path = data_dir / "file-source.duckdb"
    assert connector.schema.display_name == "../human label"
    assert storage_path.is_file()
    assert not (tmp_path / "human label.duckdb").exists()

    await connector.close_async()
    assert not storage_path.exists()


async def test_run_with_conn_cancel_rolls_back(tmp_path: Path) -> None:
    db_path = str(tmp_path / "rollback.duckdb")
    duckdb.connect(db_path).close()
    connector = await SQLConnector.from_url_async(
        global_id="rollback",
        url=f"duckdb:///{db_path}",
        display_name="t",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    query_started = threading.Event()

    def track_query(
        _conn: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        if "WITH RECURSIVE loop" in statement:
            query_started.set()

    sqlalchemy.event.listen(connector._t_eng.engine, "before_cursor_execute", track_query)

    def write(conn: sqlalchemy.engine.Connection) -> None:
        conn.exec_driver_sql("CREATE TABLE mytbl (x INTEGER)")
        conn.exec_driver_sql(
            """
            WITH RECURSIVE loop(x) AS (
                VALUES(0)
                UNION ALL
                SELECT (x + 1) % 2 FROM loop
            )
            SELECT COUNT(*) FROM loop
            """
        )

    try:
        task = asyncio.create_task(connector._t_eng.run_with_conn_async(write, ddl=True))
        await asyncio.wait_for(asyncio.to_thread(query_started.wait), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        result = await connector.run_query_async(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'mytbl' AND table_schema = 'main'"
        )
        assert result.df is not None
        assert result.df.iloc[0, 0] == 0
    finally:
        await connector.close_async()


async def test_cancel_isolates_to_one_query(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
            display_name="t",
            read_only=False,
            config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
        )

        strategy = connector._t_eng._cancel_strategy
        assert strategy is not None
        captured = threading.Event()
        capture_count = 0
        capture_lock = threading.Lock()
        real_capture = strategy.capture

        def track_capture(conn: Any) -> Any:
            nonlocal capture_count
            handle = real_capture(conn)
            with capture_lock:
                capture_count += 1
                if capture_count == 2:
                    captured.set()
            return handle

        monkeypatch.setattr(strategy, "capture", track_capture)
        query = """
            WITH RECURSIVE loop(x) AS (
                VALUES(0)
                UNION ALL
                SELECT (x + 1) % 2 FROM loop
            )
            SELECT COUNT(*) FROM loop
        """
        t_cancel = asyncio.create_task(connector.run_query_async(query))
        t_keep = asyncio.create_task(connector.run_query_async(query))

        await asyncio.wait_for(asyncio.to_thread(captured.wait), timeout=5)
        t_cancel.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t_cancel
        assert not t_keep.done()
        t_keep.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t_keep

        await connector.close_async()

    await asyncio.wait_for(body(), timeout=20)


# ---------------------------------------------------------------------------
# Async-engine path: aiosqlite (no protocol-level cancel — strategy must
# fire ``conn.interrupt()`` for either timeout or cancel to work).
# ---------------------------------------------------------------------------


async def _make_async_sqlite_connector(tmp_path: Path) -> SQLConnector:
    """Build a SQLConnector backed by aiosqlite."""
    import sqlalchemy

    db_path = str(tmp_path / "async.sqlite")
    eng = sqlalchemy.create_engine(f"sqlite:///{db_path}")
    eng.dispose()

    return await SQLConnector.from_url_async(
        global_id="async-sqlite",
        url=f"sqlite+aiosqlite:///{db_path}",
        display_name="t",
        read_only=True,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )


_NONTERMINATING_AIOSQLITE_QUERY = """
WITH RECURSIVE loop(x) AS (
    VALUES(0)
    UNION ALL
    SELECT (x + 1) % 2 FROM loop
)
SELECT COUNT(*) FROM loop
"""


async def test_aiosqlite_cancel_aborts_query(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cancelling a long aiosqlite query must trigger ``interrupt()`` on
    the underlying sqlite3 connection and raise ``CancelledError``
    promptly — without the strategy, aiosqlite's worker thread would
    keep running until the query naturally completes."""

    async def body() -> None:
        connector = await _make_async_sqlite_connector(tmp_path)
        try:
            strategy = connector._t_eng._cancel_strategy
            assert strategy is not None
            captured = asyncio.Event()
            real_acapture = strategy.acapture

            async def track_capture(conn: Any) -> Any:
                handle = await real_acapture(conn)
                captured.set()
                return handle

            monkeypatch.setattr(strategy, "acapture", track_capture)
            task = asyncio.create_task(connector.run_query_async(_NONTERMINATING_AIOSQLITE_QUERY))
            await asyncio.wait_for(captured.wait(), timeout=5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            await connector.close_async()

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
            result = await connector.run_query_async(_NONTERMINATING_AIOSQLITE_QUERY, timeout=1)
            assert result.error is not None
            assert result.error.exc_type == "TimeoutError"
            next_result = await connector.run_query_async("SELECT 1")
            assert next_result.error is None
        finally:
            await connector.close_async()

    # Outer cap well above the inner timeout to leave room for cleanup.
    await asyncio.wait_for(body(), timeout=20)
