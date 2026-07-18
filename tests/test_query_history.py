"""Tests for QueryHistory LRU spill to workspace DuckDB."""

from pathlib import Path
from typing import AsyncGenerator

import pandas as pd
import pytest

from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub.query_history import QueryHistory


def _make_pred_query(n_rows: int = 5) -> PredQuery:
    df = pd.DataFrame({"a": range(n_rows), "b": [f"val_{i}" for i in range(n_rows)]})
    return PredQuery(query="SELECT 1", exec_result=ExecResult(df=df))


def _make_error_pred_query() -> PredQuery:
    from tabulaflow.core.types import ErrorInfo

    return PredQuery(
        query="SELECT bad",
        exec_result=ExecResult(error=ErrorInfo(exc_type="ProgrammingError", message="syntax error")),
    )


def _exec_result(pq: PredQuery) -> ExecResult:
    """Narrow ``pq.exec_result`` from ``ExecResult | None`` for test
    assertions — callers in this file always construct ``PredQuery``
    with a non-None ``exec_result``."""
    assert pq.exec_result is not None
    return pq.exec_result


class TestNoConnector:
    """Without a spill connector, everything stays in memory."""

    def test_rejects_zero_max_in_memory(self) -> None:
        with pytest.raises(ValueError, match="max_in_memory must be >= 1"):
            QueryHistory(max_in_memory=0)

    @pytest.mark.asyncio
    async def test_no_eviction(self) -> None:
        h = QueryHistory(max_in_memory=2)
        for _ in range(5):
            await h.add("db", "sql", _make_pred_query())
        assert len(h._spilled) == 0
        assert all(_exec_result(r.pred_query).df is not None for r in h._records.values())

    @pytest.mark.asyncio
    async def test_get_and_last(self) -> None:
        h = QueryHistory()
        await h.add("db", "sql", _make_pred_query(n_rows=3))
        await h.add("db", "sql", _make_pred_query(n_rows=7))
        assert _exec_result((await h.get("Q1")).pred_query).df is not None
        last_df = _exec_result((await h.last()).pred_query).df
        assert last_df is not None
        assert len(last_df) == 7


class TestWithConnector:
    """With a workspace connector, old DFs are evicted from RAM."""

    @pytest.fixture
    async def workspace(self, tmp_path: Path) -> AsyncGenerator[SQLConnector, None]:
        db_path = tmp_path / "workspace.duckdb"
        connector = await SQLConnector.from_url_async(
            global_id="test-workspace",
            url=f"duckdb:///{db_path}",
            db_name="workspace",
            read_only=False,
            enable_schema_caching=False,
            enable_query_caching=False,
        )
        yield connector

    @pytest.mark.asyncio
    async def test_no_spill_within_limit(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=5, spill_connector=workspace)
        for _ in range(5):
            await h.add("db", "sql", _make_pred_query())
        assert len(h._spilled) == 0
        assert len(h._in_memory) == 5

    @pytest.mark.asyncio
    async def test_evicts_oldest(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=3, spill_connector=workspace)
        for _ in range(5):
            await h.add("db", "sql", _make_pred_query())

        assert len(h._in_memory) == 3
        assert h._spilled == {"Q1", "Q2"}
        assert _exec_result(h._records["Q1"].pred_query).df is None
        assert _exec_result(h._records["Q2"].pred_query).df is None
        assert _exec_result(h._records["Q3"].pred_query).df is not None

    @pytest.mark.asyncio
    async def test_get_hydrates_spilled_record(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=2, spill_connector=workspace)
        await h.add("db", "sql", _make_pred_query(n_rows=10))
        await h.add("db", "sql", _make_pred_query(n_rows=20))
        await h.add("db", "sql", _make_pred_query(n_rows=30))
        assert "Q1" in h._spilled

        record = await h.get("Q1")
        df = _exec_result(record.pred_query).df
        assert df is not None
        assert len(df) == 10
        # Q1 back in memory, Q2 evicted
        assert "Q1" not in h._spilled
        assert "Q2" in h._spilled

    @pytest.mark.asyncio
    async def test_last_returns_most_recent(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=2, spill_connector=workspace)
        await h.add("db", "sql", _make_pred_query(n_rows=3))
        await h.add("db", "sql", _make_pred_query(n_rows=7))
        record = await h.last()
        assert record.record_id == "Q2"
        last_df = _exec_result(record.pred_query).df
        assert last_df is not None
        assert len(last_df) == 7

    @pytest.mark.asyncio
    async def test_error_records_not_tracked(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=2, spill_connector=workspace)
        await h.add("db", "sql", _make_error_pred_query())
        await h.add("db", "sql", _make_pred_query())
        assert len(h._in_memory) == 1
        assert len(h._spilled) == 0

    @pytest.mark.asyncio
    async def test_roundtrip_preserves_data(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=1, spill_connector=workspace)
        df_original = pd.DataFrame(
            {
                "int_col": [1, 2, 3],
                "float_col": [1.5, 2.5, 3.5],
                "str_col": ["a", "b", "c"],
            }
        )
        pq = PredQuery(query="SELECT *", exec_result=ExecResult(df=df_original.copy()))
        await h.add("db", "sql", pq)
        await h.add("db", "sql", _make_pred_query())  # evicts Q1
        assert "Q1" in h._spilled

        record = await h.get("Q1")
        df_loaded = _exec_result(record.pred_query).df
        # Hydration goes through the connector read path, which upgrades
        # to nullable extension dtypes (Int64 / Float64 / string).  Values
        # round-trip, dtypes don't.
        pd.testing.assert_frame_equal(df_loaded, df_original, check_dtype=False)

    @pytest.mark.asyncio
    async def test_add_chart_does_not_hydrate(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=1, spill_connector=workspace)
        await h.add("db", "sql", _make_pred_query())
        await h.add("db", "sql", _make_pred_query())
        assert "Q1" in h._spilled
        chart_id = h.add_chart("Q1", {"mark": "bar"})
        assert "Q1" in h._spilled
        assert chart_id == "CHART1"
        chart = h.get_chart("CHART1")
        assert chart.record_id == "Q1"
        assert chart.chart_spec == {"mark": "bar"}
        with pytest.raises(KeyError):
            h.add_chart("Q9", {"mark": "bar"})
        with pytest.raises(KeyError):
            h.get_chart("CHART9")

    @pytest.mark.asyncio
    async def test_add_map_stores_standalone_artifact(self, workspace: SQLConnector) -> None:
        h = QueryHistory(spill_connector=workspace)
        spec = {"layers": [{"type": "points", "source": "Q1", "lat": "lat", "lng": "lng"}]}
        map_id = h.add_map(spec)
        assert map_id == "MAP1"
        assert h.get_map("MAP1").map_spec == spec
        assert h.add_map(spec) == "MAP2"
        with pytest.raises(KeyError):
            h.get_map("MAP9")

    @pytest.mark.asyncio
    async def test_add_graph_stores_standalone_artifact(self, workspace: SQLConnector) -> None:
        h = QueryHistory(spill_connector=workspace)
        spec = {"layout": "force", "edges": [{"record_id": "Q1", "source": "src", "target": "dst"}]}
        graph_id = h.add_graph(spec)
        assert graph_id == "GRAPH1"
        assert h.get_graph("GRAPH1").graph_spec == spec
        assert h.add_graph(spec) == "GRAPH2"
        with pytest.raises(KeyError):
            h.get_graph("GRAPH9")
