from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pydantic_ai import ToolReturn

from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.core.outputs import ChartView
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub import (
    ArtifactRef,
    ArtifactBundle,
    Choice,
    Dimension,
    QueryDimension,
    OutputStore,
    RunQueryForEachCombinationTool,
    ShowArtifactsTool,
)


def _text(result: ToolReturn) -> str:
    value = result.return_value
    assert isinstance(value, str)
    return value


@pytest.fixture
async def output_store() -> OutputStore:
    h = OutputStore()
    await h.add_result("workspace", "sql", PredQuery(query="SELECT 1", exec_result=ExecResult(df=pd.DataFrame({"a": [1]}))))
    h.add_artifact("CHART", ChartView(source="S1", spec={"mark": "bar"}))
    return h


class TestShowArtifacts:
    @pytest.mark.asyncio
    async def test_declares_the_bundle_in_metadata(self, output_store: OutputStore) -> None:
        result = await ShowArtifactsTool(output_store=output_store)(
            [ArtifactRef(id="S1", label="row count"), ArtifactRef(id="CHART1", label="rows by group")]
        )

        assert _text(result) == "showing row count (S1), rows by group (CHART1)"
        assert result.metadata == ArtifactBundle(
            artifacts=(ArtifactRef(id="S1", label="row count"), ArtifactRef(id="CHART1", label="rows by group"))
        )

    @pytest.mark.asyncio
    async def test_accepts_an_empty_bundle(self, output_store: OutputStore) -> None:
        result = await ShowArtifactsTool(output_store=output_store)([])

        assert _text(result) == "showing nothing"
        assert result.metadata == ArtifactBundle(artifacts=())

    @pytest.mark.asyncio
    async def test_rejects_unknown_ids(self, output_store: OutputStore) -> None:
        result = await ShowArtifactsTool(output_store=output_store)(
            [ArtifactRef(id="S9", label="missing"), ArtifactRef(id="MAP1", label="also missing")]
        )

        assert _text(result) == "(error: unknown artifact id 'S9'; unknown artifact id 'MAP1')"
        assert result.metadata is None

    @pytest.mark.asyncio
    async def test_rejects_the_id_as_its_own_label(self, output_store: OutputStore) -> None:
        result = await ShowArtifactsTool(output_store=output_store)([ArtifactRef(id="S1", label="S1")])

        assert "needs a human-readable label" in _text(result)
        assert result.metadata is None


TOP = """
SELECT customer, {% if ranking == "net" %} SUM(net) {% else %} COUNT(*) {% endif %} AS value FROM orders
WHERE {% if period == "q2" %} order_date < DATE '2026-07-01' {% else %} order_date >= DATE '2026-07-01' {% endif %}
GROUP BY customer ORDER BY value DESC
"""
BY_REGION = """
SELECT region, COUNT(*) AS orders FROM orders
WHERE {% if period == "q2" %} order_date < DATE '2026-07-01' {% else %} order_date >= DATE '2026-07-01' {% endif %}
GROUP BY region
"""
QUARTER_ONLY = """
SELECT '{{ period }}' AS period, SUM(net) AS net FROM orders
WHERE {% if period == "q2" %} order_date < DATE '2026-07-01' {% endif %}
"""


def _dimensions() -> list[Dimension]:
    return [
        Dimension(
            id="ranking",
            label="Ranking",
            choices=[Choice(id="net", label="Highest net revenue"), Choice(id="order_count", label="Most orders")],
        ),
        Dimension(
            id="period",
            label="Time period",
            choices=[Choice(id="q2", label="Q2"), Choice(id="q3", label="Q3")],
        ),
    ]


@pytest.fixture
async def families(tmp_path: Path) -> tuple[OutputStore, ShowArtifactsTool]:
    """A output_store holding three families: arity 2, arity 1, and one partial over ``period``."""
    connector = await SQLConnector.from_url_async(
        global_id="test-panel",
        url=f"duckdb:///{tmp_path / 'w.duckdb'}",
        db_name="w",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    await connector.run_query_async("CREATE TABLE orders(customer TEXT, region TEXT, net INT, order_date DATE)")
    await connector.run_query_async(
        """
        INSERT INTO orders VALUES
        ('Acme', 'EU', 10, DATE '2026-04-02'),
        ('Acme', 'EU', 20, DATE '2026-07-02'),
        ('Globex', 'US', 7, DATE '2026-04-03')
        """
    )
    registry = DBRegistry()
    registry.register("workspace", connector)
    output_store = OutputStore()
    runner = RunQueryForEachCombinationTool(registry, output_store=output_store)
    both = [
        QueryDimension(id="ranking", choices=["net", "order_count"]),
        QueryDimension(id="period", choices=["q2", "q3"]),
    ]
    await runner("workspace", both, TOP)  # S1
    await runner("workspace", [QueryDimension(id="period", choices=["q2", "q3"])], BY_REGION)  # S2
    await runner("workspace", [QueryDimension(id="period", choices=["q2"])], QUARTER_ONLY)  # S3
    return output_store, ShowArtifactsTool(output_store=output_store)


class TestShowArtifactsPanel:
    @pytest.mark.asyncio
    async def test_declares_dimensions_and_flags_partial_coverage(
        self, families: tuple[OutputStore, ShowArtifactsTool]
    ) -> None:
        _, show = families

        result = await show(
            [
                ArtifactRef(id="S1", label="top customers"),
                ArtifactRef(id="S2", label="orders by region"),
                ArtifactRef(id="S3", label="net revenue"),
            ],
            _dimensions(),
        )

        assert _text(result) == (
            "showing top customers (S1), orders by region (S2), net revenue (S3 — only applies at period=q2)"
        )
        assert result.metadata is not None
        assert [dim.id for dim in result.metadata.dimensions] == ["ranking", "period"]

    @pytest.mark.asyncio
    async def test_rejects_a_family_without_a_panel(self, families: tuple[OutputStore, ShowArtifactsTool]) -> None:
        _, show = families

        result = await show([ArtifactRef(id="S1", label="top customers")])

        assert "S1 varies over ranking, period; declare them as dimensions" in _text(result)
        assert result.metadata is None

    @pytest.mark.asyncio
    async def test_rejects_an_undeclared_dimension_or_choice(
        self, families: tuple[OutputStore, ShowArtifactsTool]
    ) -> None:
        _, show = families
        period_only = [_dimensions()[1]]

        result = await show([ArtifactRef(id="S1", label="top customers")], period_only)
        assert "S1 varies over 'ranking', which is not a declared dimension" in _text(result)

        narrowed = [
            _dimensions()[0],
            Dimension(
                id="period",
                label="Time period",
                choices=[Choice(id="q2", label="Q2"), Choice(id="q4", label="Q4")],
            ),
        ]
        result = await show([ArtifactRef(id="S1", label="top customers")], narrowed)
        assert "S1 ran period=q3, not declared for 'period'" in _text(result)

    @pytest.mark.asyncio
    async def test_rejects_a_dimension_no_card_varies_over(
        self, families: tuple[OutputStore, ShowArtifactsTool]
    ) -> None:
        _, show = families

        result = await show([ArtifactRef(id="S2", label="orders by region")], _dimensions())

        assert "dimension 'ranking' is not varied over by any card" in _text(result)
        assert result.metadata is None

    @pytest.mark.asyncio
    async def test_rejects_a_card_that_misses_the_first_choice(
        self, families: tuple[OutputStore, ShowArtifactsTool]
    ) -> None:
        _, show = families
        q3_first = [
            _dimensions()[0],
            Dimension(
                id="period",
                label="Time period",
                choices=[Choice(id="q3", label="Q3"), Choice(id="q2", label="Q2")],
            ),
        ]

        result = await show(
            [ArtifactRef(id="S1", label="top customers"), ArtifactRef(id="S3", label="net revenue")], q3_first
        )

        assert "S3 does not apply at period=q3, the first choice of 'period'" in _text(result)
        assert result.metadata is None
