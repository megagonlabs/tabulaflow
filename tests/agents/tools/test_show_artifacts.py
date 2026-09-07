from __future__ import annotations

import pandas as pd
import pytest
from pydantic_ai import ToolReturn

from tabulaflow.output.specs import ChoiceOption, ChoiceParameter
from tabulaflow.core import ExecResult
from tabulaflow.agents.tools import ArtifactBundle, ArtifactRef, ShowArtifactsTool
from tabulaflow.output.store import OutputStore


def _text(result: ToolReturn) -> str:
    value = result.return_value
    assert isinstance(value, str)
    return value


@pytest.fixture
async def output_store() -> OutputStore:
    h = OutputStore()
    await h.add_fixed_result_source("workspace", "duckdb", "SELECT 1", ExecResult(df=pd.DataFrame({"a": [1]})))
    h.add_chart_artifact("S1", {"mark": "bar"})
    return h


class TestShowArtifacts:
    async def test_declares_the_bundle_in_metadata(self, output_store: OutputStore) -> None:
        result = await ShowArtifactsTool(output_store=output_store)(
            [ArtifactRef(id="S1", label="row count"), ArtifactRef(id="CHART1", label="rows by group")]
        )

        assert _text(result) == "showing row count (S1), rows by group (CHART1)"
        assert result.metadata == ArtifactBundle(
            artifacts=(ArtifactRef(id="S1", label="row count"), ArtifactRef(id="CHART1", label="rows by group"))
        )

    async def test_accepts_an_empty_bundle(self, output_store: OutputStore) -> None:
        result = await ShowArtifactsTool(output_store=output_store)([])

        assert _text(result) == "showing nothing"
        assert result.metadata == ArtifactBundle(artifacts=())

    async def test_rejects_unknown_ids(self, output_store: OutputStore) -> None:
        result = await ShowArtifactsTool(output_store=output_store)(
            [ArtifactRef(id="S9", label="missing"), ArtifactRef(id="MAP1", label="also missing")]
        )

        assert _text(result) == "(error: unknown artifact id 'S9'; unknown artifact id 'MAP1')"
        assert result.metadata is None

    async def test_rejects_the_id_as_its_own_label(self, output_store: OutputStore) -> None:
        result = await ShowArtifactsTool(output_store=output_store)([ArtifactRef(id="S1", label="S1")])

        assert "needs a human-readable label" in _text(result)
        assert result.metadata is None

    async def test_parameterized_sources_need_no_show_artifacts_dimensions(self) -> None:
        output_store = OutputStore()
        output_store.add_parameterized_source(
            "workspace",
            [ChoiceParameter(id="metric", label="Metric", choices=[ChoiceOption(id="revenue", label="Revenue")])],
            "SELECT 1",
        )

        result = await ShowArtifactsTool(output_store=output_store)([ArtifactRef(id="S1", label="top customers")])

        assert _text(result) == "showing top customers (S1)"
        assert result.metadata == ArtifactBundle(artifacts=(ArtifactRef(id="S1", label="top customers"),))
