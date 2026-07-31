from __future__ import annotations

import pandas as pd
import pytest
from pydantic_ai import ToolReturn

from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub import Artifact, ArtifactBundle, QueryHistory, ShowArtifactsTool


def _text(result: ToolReturn) -> str:
    value = result.return_value
    assert isinstance(value, str)
    return value


@pytest.fixture
async def history() -> QueryHistory:
    h = QueryHistory()
    await h.add("workspace", "sql", PredQuery(query="SELECT 1", exec_result=ExecResult(df=pd.DataFrame({"a": [1]}))))
    h.add_chart("Q1", {"mark": "bar"})
    return h


class TestShowArtifacts:
    @pytest.mark.asyncio
    async def test_declares_the_bundle_in_metadata(self, history: QueryHistory) -> None:
        result = await ShowArtifactsTool(history=history)(
            [Artifact(id="Q1", label="row count"), Artifact(id="CHART1", label="rows by group")]
        )

        assert _text(result) == "showing row count (Q1), rows by group (CHART1)"
        assert result.metadata == ArtifactBundle(
            artifacts=(Artifact(id="Q1", label="row count"), Artifact(id="CHART1", label="rows by group"))
        )

    @pytest.mark.asyncio
    async def test_accepts_an_empty_bundle(self, history: QueryHistory) -> None:
        result = await ShowArtifactsTool(history=history)([])

        assert _text(result) == "showing nothing"
        assert result.metadata == ArtifactBundle(artifacts=())

    @pytest.mark.asyncio
    async def test_rejects_unknown_ids(self, history: QueryHistory) -> None:
        result = await ShowArtifactsTool(history=history)(
            [Artifact(id="Q9", label="missing"), Artifact(id="MAP1", label="also missing")]
        )

        assert _text(result) == "(error: unknown artifact id 'Q9'; unknown artifact id 'MAP1')"
        assert result.metadata is None

    @pytest.mark.asyncio
    async def test_rejects_the_id_as_its_own_label(self, history: QueryHistory) -> None:
        result = await ShowArtifactsTool(history=history)([Artifact(id="Q1", label="Q1")])

        assert "needs a human-readable label" in _text(result)
        assert result.metadata is None
