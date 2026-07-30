from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_ai import ToolReturn

from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.toolhub import QueryDimension, QueryHistory, RegistryRunQueryForEachCombinationTool, ToolCallOutcome


def _text(result: ToolReturn) -> str:
    value = result.return_value
    assert isinstance(value, str)
    return value


@pytest.fixture
async def registry(tmp_path: Path) -> DBRegistry:
    connector = await SQLConnector.from_url_async(
        global_id="test-combinations",
        url=f"duckdb:///{tmp_path / 'w.duckdb'}",
        db_name="w",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    await connector.run_query_async("CREATE TABLE orders(customer TEXT, net INT, gross INT, order_date DATE)")
    await connector.run_query_async(
        """
        INSERT INTO orders VALUES
        ('Acme', 10, 12, DATE '2026-04-02'),
        ('Acme', 20, 25, DATE '2026-07-02'),
        ('Globex', 7, 9, DATE '2026-04-03')
        """
    )
    r = DBRegistry()
    r.register("workspace", connector)
    return r


def _tool(registry: DBRegistry, history: QueryHistory | None = None) -> RegistryRunQueryForEachCombinationTool:
    return RegistryRunQueryForEachCombinationTool(registry, history=history or QueryHistory(), max_combinations=16)


class TestRunQueryForEachCombination:
    @pytest.mark.asyncio
    async def test_expands_and_registers_family(self, registry: DBRegistry) -> None:
        history = QueryHistory()
        result = await _tool(registry, history)(
            "workspace",
            [
                QueryDimension(id="ranking", choices=["net", "gross"]),
                QueryDimension(id="period", choices=["q2", "q3"]),
            ],
            """
            SELECT customer,
              {% if ranking == "net" %} SUM(net) AS value {% else %} SUM(gross) AS value {% endif %}
            FROM orders
            WHERE {% if period == "q2" %} order_date < DATE '2026-07-01' {% else %} order_date >= DATE '2026-07-01' {% endif %}
            GROUP BY customer ORDER BY value DESC
            """,
        )

        assert result.metadata == ToolCallOutcome(count=4, unit="combinations")
        assert _text(result).startswith("QS1 —")
        family = history.get_family("QS1")
        assert family.dimensions == {"ranking": ["net", "gross"], "period": ["q2", "q3"]}
        assert set(family.record_ids_by_selection) == {
            "period=q2;ranking=net",
            "period=q3;ranking=net",
            "period=q2;ranking=gross",
            "period=q3;ranking=gross",
        }
        record = await history.get(family.record_ids_by_selection["period=q2;ranking=net"])
        assert record.pred_query.exec_result is not None
        assert record.pred_query.exec_result.df is not None
        assert record.pred_query.exec_result.df.to_dict("records")[0] == {"customer": "Acme", "value": 10}

    @pytest.mark.asyncio
    async def test_identical_renders_share_record(self, registry: DBRegistry) -> None:
        history = QueryHistory()
        result = await _tool(registry, history)(
            "workspace",
            [
                QueryDimension(id="ranking", choices=["net", "gross"]),
                QueryDimension(id="period", choices=["q2", "q3"]),
            ],
            """
            SELECT customer,
              {% if ranking == "net" %}
                {% if period == "q2" %} SUM(net) AS value FROM orders WHERE order_date < DATE '2026-07-01'
                {% else %} SUM(net) AS value FROM orders WHERE order_date >= DATE '2026-07-01'
                {% endif %}
              {% else %}
                SUM(gross) AS value FROM orders
              {% endif %}
            GROUP BY customer ORDER BY value DESC
            """,
        )

        assert "4 combinations, 3 executed (1 identical)" in _text(result)
        family = history.get_family("QS1")
        assert (
            family.record_ids_by_selection["period=q2;ranking=gross"]
            == family.record_ids_by_selection["period=q3;ranking=gross"]
        )

    @pytest.mark.asyncio
    async def test_template_variables_must_match_dimensions(self, registry: DBRegistry) -> None:
        result = await _tool(registry)(
            "workspace",
            [QueryDimension(id="ranking", choices=["net", "gross"])],
            "SELECT '{{ period }}'",
        )

        assert result.metadata == ToolCallOutcome(error=True)
        assert "missing template variables for dimensions: ranking" in _text(result)
        assert "template variables not declared as dimensions: period" in _text(result)

    @pytest.mark.asyncio
    async def test_dimension_must_affect_rendered_sql(self, registry: DBRegistry) -> None:
        result = await _tool(registry)(
            "workspace",
            [QueryDimension(id="ranking", choices=["net", "gross"])],
            "SELECT 1 -- {{ ranking }}",
        )

        assert result.metadata == ToolCallOutcome(error=True)
        assert "changing dimension 'ranking' never changes" in _text(result)

    @pytest.mark.asyncio
    async def test_query_failure_registers_no_family(self, registry: DBRegistry) -> None:
        history = QueryHistory()
        result = await _tool(registry, history)(
            "workspace",
            [QueryDimension(id="ranking", choices=["net", "gross"])],
            "SELECT * FROM missing_{{ ranking }}",
        )

        assert result.metadata == ToolCallOutcome(error=True)
        with pytest.raises(KeyError):
            history.get_family("QS1")

    @pytest.mark.asyncio
    async def test_duplicate_dimension_and_choice_validation(self, registry: DBRegistry) -> None:
        result = await _tool(registry)(
            "workspace",
            [QueryDimension(id="ranking", choices=["net"]), QueryDimension(id="ranking", choices=["gross"])],
            "SELECT '{{ ranking }}'",
        )
        assert result.metadata == ToolCallOutcome(error=True)
        assert "dimension ids must be unique" in _text(result)

        result = await _tool(registry)(
            "workspace",
            [QueryDimension(id="ranking", choices=["net", "net"])],
            "SELECT '{{ ranking }}'",
        )
        assert result.metadata == ToolCallOutcome(error=True)
        assert "duplicate choices" in _text(result)
