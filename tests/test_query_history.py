"""Tests for QueryHistory LRU spill to workspace DuckDB."""

import pandas as pd
import pytest

from mintq.schema import ExecResult, PredQuery
from mintq.toolhub.query_history import QueryHistory


def _make_pred_query(n_rows: int = 5) -> PredQuery:
    df = pd.DataFrame({"a": range(n_rows), "b": [f"val_{i}" for i in range(n_rows)]})
    return PredQuery(query="SELECT 1", exec_result=ExecResult(df=df))


def _make_error_pred_query() -> PredQuery:
    from mintq.schema import ErrorInfo

    return PredQuery(
        query="SELECT bad",
        exec_result=ExecResult(error=ErrorInfo(exc_type="ProgrammingError", message="syntax error")),
    )


class TestNoConnector:
    """Without a spill connector, everything stays in memory."""

    def test_rejects_zero_max_in_memory(self):
        with pytest.raises(ValueError, match="max_in_memory must be >= 1"):
            QueryHistory(max_in_memory=0)

    @pytest.mark.anyio
    async def test_no_eviction(self):
        h = QueryHistory(max_in_memory=2)
        for _ in range(5):
            await h.add("db", "sql", _make_pred_query())
        assert len(h._spilled) == 0
        assert all(r.pred_query.exec_result.df is not None for r in h._records.values())

    @pytest.mark.anyio
    async def test_get_and_last(self):
        h = QueryHistory()
        await h.add("db", "sql", _make_pred_query(n_rows=3))
        await h.add("db", "sql", _make_pred_query(n_rows=7))
        assert (await h.get("Q1")).pred_query.exec_result.df is not None
        assert len((await h.last()).pred_query.exec_result.df) == 7


class TestWithConnector:
    """With a workspace connector, old DFs are evicted from RAM."""

    @pytest.fixture
    async def workspace(self, tmp_path):
        from mintq.db_connector.sql_conn import SQLConnector

        db_path = tmp_path / "workspace.duckdb"
        connector = await SQLConnector.from_url_async(
            global_id="test-workspace",
            url=f"duckdb:///{db_path}",
            db_name="workspace",
            read_only=False,
            enable_schema_caching=False,
            enable_query_caching=False,
        )
        return connector

    @pytest.mark.anyio
    async def test_no_spill_within_limit(self, workspace):
        h = QueryHistory(max_in_memory=5, spill_connector=workspace)
        for _ in range(5):
            await h.add("db", "sql", _make_pred_query())
        assert len(h._spilled) == 0
        assert len(h._in_memory) == 5

    @pytest.mark.anyio
    async def test_evicts_oldest(self, workspace):
        h = QueryHistory(max_in_memory=3, spill_connector=workspace)
        for _ in range(5):
            await h.add("db", "sql", _make_pred_query())

        assert len(h._in_memory) == 3
        assert h._spilled == {"Q1", "Q2"}
        assert h._records["Q1"].pred_query.exec_result.df is None
        assert h._records["Q2"].pred_query.exec_result.df is None
        assert h._records["Q3"].pred_query.exec_result.df is not None

    @pytest.mark.anyio
    async def test_get_hydrates_spilled_record(self, workspace):
        h = QueryHistory(max_in_memory=2, spill_connector=workspace)
        await h.add("db", "sql", _make_pred_query(n_rows=10))
        await h.add("db", "sql", _make_pred_query(n_rows=20))
        await h.add("db", "sql", _make_pred_query(n_rows=30))
        assert "Q1" in h._spilled

        record = await h.get("Q1")
        df = record.pred_query.exec_result.df
        assert df is not None
        assert len(df) == 10
        # Q1 back in memory, Q2 evicted
        assert "Q1" not in h._spilled
        assert "Q2" in h._spilled

    @pytest.mark.anyio
    async def test_last_returns_most_recent(self, workspace):
        h = QueryHistory(max_in_memory=2, spill_connector=workspace)
        await h.add("db", "sql", _make_pred_query(n_rows=3))
        await h.add("db", "sql", _make_pred_query(n_rows=7))
        record = await h.last()
        assert record.record_id == "Q2"
        assert len(record.pred_query.exec_result.df) == 7

    @pytest.mark.anyio
    async def test_error_records_not_tracked(self, workspace):
        h = QueryHistory(max_in_memory=2, spill_connector=workspace)
        await h.add("db", "sql", _make_error_pred_query())
        await h.add("db", "sql", _make_pred_query())
        assert len(h._in_memory) == 1
        assert len(h._spilled) == 0

    @pytest.mark.anyio
    async def test_roundtrip_preserves_data(self, workspace):
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
        df_loaded = record.pred_query.exec_result.df
        # Hydration goes through the connector read path, which upgrades
        # to nullable extension dtypes (Int64 / Float64 / string).  Values
        # round-trip, dtypes don't.
        pd.testing.assert_frame_equal(df_loaded, df_original, check_dtype=False)

    @pytest.mark.anyio
    async def test_attach_chart_does_not_hydrate(self, workspace):
        h = QueryHistory(max_in_memory=1, spill_connector=workspace)
        await h.add("db", "sql", _make_pred_query())
        await h.add("db", "sql", _make_pred_query())
        assert "Q1" in h._spilled
        h.attach_chart("Q1", {"mark": "bar"})
        assert "Q1" in h._spilled
        assert h._records["Q1"].vegalite_spec == {"mark": "bar"}
