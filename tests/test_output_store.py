"""Tests for OutputStore LRU spill to workspace DuckDB."""

from pathlib import Path
from typing import AsyncGenerator

import pandas as pd
import pytest

from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.sql import SQLConnector
from tabulaflow.output.specs import ChartArtifactSpec, GraphArtifactSpec, MapArtifactSpec
from tabulaflow.core import ExecResult
from tabulaflow.output.store import OutputStore


def _make_execution(n_rows: int = 5) -> tuple[str, ExecResult]:
    df = pd.DataFrame({"a": range(n_rows), "b": [f"val_{i}" for i in range(n_rows)]})
    return "SELECT 1", ExecResult(df=df)


def _chart_artifact(output_store: OutputStore, chart_id: str) -> ChartArtifactSpec:
    artifact = output_store.get_artifact(chart_id)
    assert isinstance(artifact, ChartArtifactSpec)
    return artifact


def _map_artifact(output_store: OutputStore, map_id: str) -> MapArtifactSpec:
    artifact = output_store.get_artifact(map_id)
    assert isinstance(artifact, MapArtifactSpec)
    return artifact


def _graph_artifact(output_store: OutputStore, graph_id: str) -> GraphArtifactSpec:
    artifact = output_store.get_artifact(graph_id)
    assert isinstance(artifact, GraphArtifactSpec)
    return artifact


def _make_error_execution() -> tuple[str, ExecResult]:
    from tabulaflow.core import ErrorInfo

    return "SELECT bad", ExecResult(error=ErrorInfo(exc_type="ProgrammingError", message="syntax error"))


class TestNoConnector:
    """Without a spill connector, everything stays in memory."""

    def test_rejects_zero_max_in_memory(self) -> None:
        with pytest.raises(ValueError, match="max_in_memory must be >= 1"):
            OutputStore(max_in_memory=0)

    @pytest.mark.asyncio
    async def test_no_eviction(self) -> None:
        h = OutputStore(max_in_memory=2)
        for _ in range(5):
            await h.add_fixed_result_source("db", "sql", *_make_execution())
        assert h._results.in_memory_count == 5
        assert all(h._results.has_in_memory(r.metadata.id) for r in h._results_by_id.values())

    @pytest.mark.asyncio
    async def test_get(self) -> None:
        h = OutputStore()
        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=3))
        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=7))
        assert (await h.get_payload("R1")).metadata.query == "SELECT 1"
        q2_df = (await h.get_payload("R2")).df
        assert q2_df is not None
        assert len(q2_df) == 7

    @pytest.mark.asyncio
    async def test_get_payload(self) -> None:
        h = OutputStore()
        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=3))

        payload = await h.get_payload("R1")

        assert payload.metadata.id == "R1"
        assert payload.metadata.query == "SELECT 1"
        assert payload.df is not None
        assert len(payload.df) == 3

    @pytest.mark.asyncio
    async def test_result_metadata_records_affected_rows(self) -> None:
        h = OutputStore()
        await h.add_fixed_result_source(
            "db",
            "sql",
            "UPDATE t SET a = 1",
            ExecResult(affected_rows=2),
        )

        payload = await h.get_payload("R1")

        assert payload.metadata.affected_rows == 2


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
            config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
        )
        yield connector

    @pytest.mark.asyncio
    async def test_no_spill_within_limit(self, workspace: SQLConnector) -> None:
        h = OutputStore(max_in_memory=5, spill_connector=workspace)
        for _ in range(5):
            await h.add_fixed_result_source("db", "sql", *_make_execution())
        assert h._results.in_memory_count == 5

    @pytest.mark.asyncio
    async def test_evicts_oldest(self, workspace: SQLConnector) -> None:
        h = OutputStore(max_in_memory=3, spill_connector=workspace)
        for _ in range(5):
            await h.add_fixed_result_source("db", "sql", *_make_execution())

        assert h._results.in_memory_count == 3
        assert not h._results.has_in_memory("R1")
        assert not h._results.has_in_memory("R2")
        assert h._results.has_in_memory("R3")
        assert h._results.is_persisted("R1")
        assert h._results_by_id["R1"].has_dataframe

    @pytest.mark.asyncio
    async def test_eviction_does_not_mutate_caller_owned_pred_query(self, workspace: SQLConnector) -> None:
        h = OutputStore(max_in_memory=1, spill_connector=workspace)
        query, exec_result = _make_execution(n_rows=10)

        await h.add_fixed_result_source("db", "sql", query, exec_result)
        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=20))

        assert exec_result.df is not None
        assert not h._results.has_in_memory("R1")
        assert h._results_by_id["R1"].has_dataframe

    @pytest.mark.asyncio
    async def test_get_dataframe_loads_evicted_result(self, workspace: SQLConnector) -> None:
        h = OutputStore(max_in_memory=2, spill_connector=workspace)
        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=10))
        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=20))
        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=30))
        assert not h._results.has_in_memory("R1")

        df = (await h.get_payload("R1")).df
        assert df is not None
        assert len(df) == 10
        assert h._results.has_in_memory("R1")
        assert not h._results.has_in_memory("R2")

    @pytest.mark.asyncio
    async def test_persist_failure_keeps_result_in_memory(
        self, workspace: SQLConnector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        h = OutputStore(max_in_memory=1, spill_connector=workspace)

        async def fake_persist(storage_key: str, df: pd.DataFrame) -> bool:
            return storage_key != "R1"

        monkeypatch.setattr(h._results, "_persist", fake_persist)

        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=10))
        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=20))
        await h.add_fixed_result_source("db", "sql", *_make_execution(n_rows=30))

        assert h._results.has_in_memory("R1")
        assert not h._results.is_persisted("R1")
        assert not h._results.has_in_memory("R2")

        df = (await h.get_payload("R1")).df
        assert df is not None
        assert len(df) == 10

    @pytest.mark.asyncio
    async def test_error_results_not_tracked(self, workspace: SQLConnector) -> None:
        h = OutputStore(max_in_memory=2, spill_connector=workspace)
        with pytest.raises(ValueError, match="syntax error"):
            await h.add_fixed_result_source("db", "sql", *_make_error_execution())
        await h.add_fixed_result_source("db", "sql", *_make_execution())
        assert h._results.in_memory_count == 1

    @pytest.mark.asyncio
    async def test_roundtrip_preserves_data(self, workspace: SQLConnector) -> None:
        h = OutputStore(max_in_memory=1, spill_connector=workspace)
        df_original = pd.DataFrame(
            {
                "int_col": [1, 2, 3],
                "float_col": [1.5, 2.5, 3.5],
                "str_col": ["a", "b", "c"],
            }
        )
        exec_result = ExecResult(df=df_original.copy())
        await h.add_fixed_result_source("db", "sql", "SELECT *", exec_result)
        await h.add_fixed_result_source("db", "sql", *_make_execution())  # evicts Q1
        assert not h._results.has_in_memory("R1")

        df_loaded = (await h.get_payload("R1")).df
        assert df_loaded is not None
        # Hydration goes through the connector read path, which upgrades
        # to nullable extension dtypes (Int64 / Float64 / string).  Values
        # round-trip, dtypes don't.
        pd.testing.assert_frame_equal(df_loaded, df_original, check_dtype=False)

    @pytest.mark.asyncio
    async def test_add_chart_does_not_hydrate(self, workspace: SQLConnector) -> None:
        h = OutputStore(max_in_memory=1, spill_connector=workspace)
        await h.add_fixed_result_source("db", "sql", *_make_execution())
        await h.add_fixed_result_source("db", "sql", *_make_execution())
        assert not h._results.has_in_memory("R1")
        chart_id = h.add_chart_artifact("S1", {"mark": "bar"}).id
        assert not h._results.has_in_memory("R1")
        assert chart_id == "CHART1"
        assert _chart_artifact(h, "CHART1").source_id == "S1"
        assert _chart_artifact(h, "CHART1").spec == {"mark": "bar"}
        with pytest.raises(KeyError):
            h.add_chart_artifact("S9", {"mark": "bar"})
        with pytest.raises(KeyError):
            h.get_artifact("CHART9")

    @pytest.mark.asyncio
    async def test_add_map_stores_standalone_artifact(self, workspace: SQLConnector) -> None:
        h = OutputStore(spill_connector=workspace)
        await h.add_fixed_result_source("db", "sql", *_make_execution())
        spec = {"layers": [{"type": "points", "source": "S1", "lat": "lat", "lng": "lng"}]}
        map_id = h.add_map_artifact(["S1"], spec).id
        assert map_id == "MAP1"
        assert _map_artifact(h, "MAP1").spec == spec
        assert h.add_map_artifact(["S1"], spec).id == "MAP2"
        with pytest.raises(KeyError):
            h.get_artifact("MAP9")

    @pytest.mark.asyncio
    async def test_add_graph_stores_standalone_artifact(self, workspace: SQLConnector) -> None:
        h = OutputStore(spill_connector=workspace)
        graph_spec = {
            "layout": "force",
            "nodes": [{"data": [{"id": "a"}, {"id": "b"}], "id": "id"}],
            "edges": [{"data": [{"source": "a", "target": "b"}], "source": "source", "target": "target"}],
        }
        graph_id = h.add_graph_artifact([], graph_spec).id
        assert graph_id == "GRAPH1"
        assert _graph_artifact(h, "GRAPH1").spec == graph_spec
        assert h.add_graph_artifact([], graph_spec).id == "GRAPH2"
        with pytest.raises(KeyError):
            h.get_artifact("GRAPH9")
