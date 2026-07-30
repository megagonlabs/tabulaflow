"""Registry-backed query-combination tool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pydantic_ai import Tool, ToolReturn

from tabulaflow.core.config import tabulaflow_config
from tabulaflow.core.db_connector.base import NL2QDBConnector
from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.toolhub.base import ToolCallOutcome
from tabulaflow.toolhub.query_history import QueryFamily, QueryHistory
from tabulaflow.toolhub.run_query_for_each_combination import (
    CombinationQueryRun,
    DEFAULT_MAX_COMBINATIONS,
    QueryDimension,
    RunQueryForEachCombinationTool,
)


@dataclass(frozen=True)
class RegistryCombinationQueryRun:
    """Registered result of one query-combination invocation."""

    output: str
    family: QueryFamily
    run: CombinationQueryRun


class RegistryRunQueryForEachCombinationTool:
    """Run a query-combination template against any registered database."""

    name: ClassVar = "run_query_for_each_combination"

    def __init__(
        self,
        registry: DBRegistry,
        *,
        timeout: int | None = None,
        max_visible_rows: int = 20,
        max_cell_width: int = 200,
        floatfmt: str = ".8g",
        history: QueryHistory | None = None,
        max_combinations: int = DEFAULT_MAX_COMBINATIONS,
    ) -> None:
        self.registry = registry
        self.timeout = tabulaflow_config.query_timeout if timeout is None else timeout
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self._history = history or QueryHistory()
        self.max_combinations = max_combinations
        self._tools: dict[str, tuple[NL2QDBConnector, RunQueryForEachCombinationTool]] = {}

    def _get_tool(self, db_alias: str) -> RunQueryForEachCombinationTool:
        connector = self.registry.get(db_alias)
        entry = self._tools.get(db_alias)
        if entry is not None and entry[0] is connector:
            return entry[1]
        tool = RunQueryForEachCombinationTool(
            connector,
            timeout=self.timeout,
            max_visible_rows=self.max_visible_rows,
            max_cell_width=self.max_cell_width,
            floatfmt=self.floatfmt,
            max_combinations=self.max_combinations,
        )
        self._tools[db_alias] = (connector, tool)
        return tool

    async def _run(
        self,
        db_alias: str,
        dimensions: list[QueryDimension],
        query_template: str,
    ) -> ToolReturn:
        """Run a SQL Jinja template over every combination of dimension choices.

        Use this when one result card needs the same query shape evaluated across a
        small grid of interpretations. Each dimension id is available in the Jinja
        context as the selected choice id. The template must reference exactly the
        declared dimension ids, and each dimension must change the rendered SQL.
        Identical rendered SQL is executed once and shared across matching
        combinations. The full set is recorded as a query family (``QS*``) whose
        per-combination results can later be assembled into interpretation cards.

        Example:
        ```python
        run_query_for_each_combination(
            db_alias="workspace",
            dimensions=[
                {"id": "ranking", "choices": ["net_revenue", "order_count"]},
                {"id": "period", "choices": ["completed_qtr", "last_90_days"]},
            ],
            query_template='''
            SELECT customer_name AS customer,
              {% if ranking == "net_revenue" %} SUM(net_revenue_usd) AS value
              {% elif ranking == "order_count" %} COUNT(*) AS value
              {% endif %}
            FROM orders
            WHERE {% if period == "completed_qtr" %} order_date >= DATE '2026-04-01' AND order_date < DATE '2026-07-01'
                  {% elif period == "last_90_days" %} order_date > CURRENT_DATE - INTERVAL 90 DAY
                  {% endif %}
            GROUP BY customer_name
            ORDER BY value DESC
            LIMIT 5
            ''',
        )
        ```

        Args:
            db_alias: Alias of the target database.
            dimensions: Dimensions to vary over. Choice ids are the values supplied
                to the Jinja variables.
            query_template: SQL Jinja template to render and execute for each
                dimension-choice combination.
        """
        return await self(db_alias, dimensions, query_template)

    async def execute(
        self,
        db_alias: str,
        dimensions: list[QueryDimension],
        query_template: str,
    ) -> RegistryCombinationQueryRun:
        """Run the template and register the resulting query family."""

        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            raise ValueError(f"unknown db_alias: {db_alias!r}; available: {available}") from None

        run = await tool.execute(dimensions, query_template)
        family = await self._history.add_family(
            db_alias,
            tool.db_connector.connector_type,
            run.dimensions,
            run.query_template,
            run.pred_queries_by_selection,
        )
        return RegistryCombinationQueryRun(output=tool.format_run_summary(family, run), family=family, run=run)

    async def __call__(
        self,
        db_alias: str,
        dimensions: list[QueryDimension],
        query_template: str,
    ) -> ToolReturn:
        try:
            execution = await self.execute(db_alias, dimensions, query_template)
        except ValueError as exc:
            return self._error(str(exc))

        return ToolReturn(
            return_value=execution.output,
            metadata=ToolCallOutcome(count=len(execution.run.pred_queries_by_selection), unit="combinations"),
        )

    def _error(self, message: str) -> ToolReturn:
        return ToolReturn(return_value=f"(error: {message})", metadata=ToolCallOutcome(error=True))

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self._run, name=self.name)

    async def get_query_family(self, family_id: str) -> QueryFamily:
        return self._history.get_family(family_id)
