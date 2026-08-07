"""Tests for QueryHistory LRU spill to workspace DuckDB."""

from pathlib import Path
from typing import AsyncGenerator

import pandas as pd
import pytest

from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.core.types import ExecResult, GraphView, PredQuery
from tabulaflow.toolhub.query_history import (
    QueryFailure,
    QueryHistory,
    ResolvedRecordRef,
    SourceNotApplicable,
    TabularResult,
)


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
        assert h._results.in_memory_count == 5
        assert all(h._results.has_in_memory(r.record_id) for r in h._records.values())

    @pytest.mark.asyncio
    async def test_get(self) -> None:
        h = QueryHistory()
        await h.add("db", "sql", _make_pred_query(n_rows=3))
        await h.add("db", "sql", _make_pred_query(n_rows=7))
        assert (await h.get("Q1")).query == "SELECT 1"
        q2_df = await h.get_dataframe("Q2")
        assert len(q2_df) == 7

    @pytest.mark.asyncio
    async def test_get_query_record_payload(self) -> None:
        h = QueryHistory()
        await h.add("db", "sql", _make_pred_query(n_rows=3))

        payload = await h.get_query_record_payload("Q1")

        assert payload.record_id == "Q1"
        assert payload.query == "SELECT 1"
        assert payload.query_lexer == "sql"
        assert payload.df is not None
        assert len(payload.df) == 3

    @pytest.mark.asyncio
    async def test_resolves_fixed_artifact_source(self) -> None:
        h = QueryHistory()
        await h.add("db", "sql", _make_pred_query())

        resolution = h.resolve_source_id("Q1", {"ranking": "net"})

        assert resolution == ResolvedRecordRef("Q1")

    @pytest.mark.asyncio
    async def test_resolves_family_artifact_source_by_projecting_selection(self) -> None:
        h = QueryHistory()
        await h.add_family(
            "db",
            "sql",
            {"ranking": ["net", "count"], "period": ["q2", "q3"]},
            "SELECT 1",
            {
                "period=q2;ranking=net": PredQuery(
                    query="SELECT 1", exec_result=ExecResult(df=pd.DataFrame({"a": [1]}))
                ),
                "period=q3;ranking=net": PredQuery(
                    query="SELECT 2", exec_result=ExecResult(df=pd.DataFrame({"a": [2]}))
                ),
                "period=q2;ranking=count": PredQuery(
                    query="SELECT 3", exec_result=ExecResult(df=pd.DataFrame({"a": [3]}))
                ),
                "period=q3;ranking=count": PredQuery(
                    query="SELECT 4", exec_result=ExecResult(df=pd.DataFrame({"a": [4]}))
                ),
            },
        )

        resolution = h.resolve_source_id("QS1", {"ranking": "count", "period": "q3", "unrelated": "ignored"})

        assert resolution == ResolvedRecordRef("QS1_v3")

    @pytest.mark.asyncio
    async def test_resolves_query_record_payload_from_family_source(self) -> None:
        h = QueryHistory()
        await h.add_family(
            "db",
            "sql",
            {"period": ["q2", "q3"]},
            "SELECT 1",
            {
                "period=q2": PredQuery(query="SELECT 2 AS a", exec_result=ExecResult(df=pd.DataFrame({"a": [2]}))),
                "period=q3": PredQuery(query="SELECT 3 AS a", exec_result=ExecResult(df=pd.DataFrame({"a": [3]}))),
            },
        )

        payload = await h.resolve_query_record("QS1", {"period": "q3"})

        assert not isinstance(payload, SourceNotApplicable)
        assert payload.record_id == "QS1_v1"
        assert payload.df is not None
        assert payload.df.loc[0, "a"] == 3

    @pytest.mark.asyncio
    async def test_family_artifact_source_is_not_applicable_outside_coverage(self) -> None:
        h = QueryHistory()
        await h.add_family(
            "db",
            "sql",
            {"period": ["q2"]},
            "SELECT 1",
            {"period=q2": _make_pred_query()},
        )

        resolution = h.resolve_source_id("QS1", {"period": "q3"})

        assert isinstance(resolution, SourceNotApplicable)
        assert resolution.reason == "period=q3 is outside QS1"

    @pytest.mark.asyncio
    async def test_family_artifact_source_requires_relevant_selection(self) -> None:
        h = QueryHistory()
        await h.add_family(
            "db",
            "sql",
            {"period": ["q2"]},
            "SELECT 1",
            {"period=q2": _make_pred_query()},
        )

        resolution = h.resolve_source_id("QS1", {})

        assert isinstance(resolution, SourceNotApplicable)
        assert resolution.reason == "missing selection for 'period'"

    @pytest.mark.asyncio
    async def test_family_artifact_source_raises_for_corrupt_record_reference(self) -> None:
        h = QueryHistory()
        family = await h.add_family(
            "db",
            "sql",
            {"period": ["q2"]},
            "SELECT 1",
            {"period=q2": _make_pred_query()},
        )
        family.record_ids_by_selection["period=q2"] = "Q999"

        with pytest.raises(KeyError, match="No query with id Q999"):
            h.resolve_source_id("QS1", {"period": "q2"})


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
        assert h._results.in_memory_count == 5

    @pytest.mark.asyncio
    async def test_evicts_oldest(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=3, spill_connector=workspace)
        for _ in range(5):
            await h.add("db", "sql", _make_pred_query())

        assert h._results.in_memory_count == 3
        assert not h._results.has_in_memory("Q1")
        assert not h._results.has_in_memory("Q2")
        assert h._results.has_in_memory("Q3")
        assert h._results.is_persisted("Q1")
        assert isinstance(h._records["Q1"].outcome, TabularResult)

    @pytest.mark.asyncio
    async def test_eviction_does_not_mutate_caller_owned_pred_query(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=1, spill_connector=workspace)
        pred_query = _make_pred_query(n_rows=10)

        await h.add("db", "sql", pred_query)
        await h.add("db", "sql", _make_pred_query(n_rows=20))

        assert pred_query.id == "PQRY"
        assert _exec_result(pred_query).df is not None
        assert not h._results.has_in_memory("Q1")
        assert isinstance(h._records["Q1"].outcome, TabularResult)

    @pytest.mark.asyncio
    async def test_get_dataframe_loads_evicted_record(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=2, spill_connector=workspace)
        await h.add("db", "sql", _make_pred_query(n_rows=10))
        await h.add("db", "sql", _make_pred_query(n_rows=20))
        await h.add("db", "sql", _make_pred_query(n_rows=30))
        assert not h._results.has_in_memory("Q1")

        df = await h.get_dataframe("Q1")
        assert len(df) == 10
        assert h._results.has_in_memory("Q1")
        assert not h._results.has_in_memory("Q2")

    @pytest.mark.asyncio
    async def test_persist_failure_keeps_record_in_memory(
        self, workspace: SQLConnector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        h = QueryHistory(max_in_memory=1, spill_connector=workspace)

        async def fake_persist(storage_key: str, df: pd.DataFrame) -> bool:
            return storage_key != "Q1"

        monkeypatch.setattr(h._results, "_persist", fake_persist)

        await h.add("db", "sql", _make_pred_query(n_rows=10))
        await h.add("db", "sql", _make_pred_query(n_rows=20))
        await h.add("db", "sql", _make_pred_query(n_rows=30))

        assert h._results.has_in_memory("Q1")
        assert not h._results.is_persisted("Q1")
        assert not h._results.has_in_memory("Q2")

        df = await h.get_dataframe("Q1")
        assert len(df) == 10

    @pytest.mark.asyncio
    async def test_error_records_not_tracked(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=2, spill_connector=workspace)
        record = await h.add("db", "sql", _make_error_pred_query())
        await h.add("db", "sql", _make_pred_query())
        assert isinstance(record.outcome, QueryFailure)
        assert h._results.in_memory_count == 1

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
        assert not h._results.has_in_memory("Q1")

        df_loaded = await h.get_dataframe("Q1")
        # Hydration goes through the connector read path, which upgrades
        # to nullable extension dtypes (Int64 / Float64 / string).  Values
        # round-trip, dtypes don't.
        pd.testing.assert_frame_equal(df_loaded, df_original, check_dtype=False)

    @pytest.mark.asyncio
    async def test_add_chart_does_not_hydrate(self, workspace: SQLConnector) -> None:
        h = QueryHistory(max_in_memory=1, spill_connector=workspace)
        await h.add("db", "sql", _make_pred_query())
        await h.add("db", "sql", _make_pred_query())
        assert not h._results.has_in_memory("Q1")
        chart_id = h.add_chart("Q1", {"mark": "bar"})
        assert not h._results.has_in_memory("Q1")
        assert chart_id == "CHART1"
        chart = h.get_chart("CHART1")
        assert chart.source_id == "Q1"
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
        graph = GraphView(nodes=[{"id": "a"}, {"id": "b"}], edges=[{"source": "a", "target": "b"}])
        graph_id = h.add_graph(graph, layout="force")
        assert graph_id == "GRAPH1"
        assert h.get_graph("GRAPH1").graph == graph
        assert h.get_graph("GRAPH1").layout == "force"
        assert h.add_graph(graph) == "GRAPH2"
        with pytest.raises(KeyError):
            h.get_graph("GRAPH9")
