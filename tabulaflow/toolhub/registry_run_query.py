"""Run-query tool backed by a DBRegistry, letting agents target any source."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic_ai import Tool, ToolReturn

from tabulaflow.core.config import tabulaflow_config
from tabulaflow.core.db_connector.base import NL2QDBConnector
from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.toolhub.base import ToolCallOutcome, sum_tool_metrics
from tabulaflow.toolhub.query_history import QueryHistory, QueryRecord
from tabulaflow.toolhub.run_query import LLMParameter, RunQueryTool, RunQueryToolMetrics

_UNSET = object()


class RegistryRunQueryTool:
    """Execute a query against any registered database.

    The agent specifies which database to target via ``db_alias``.  The tool
    resolves the alias through a ``DBRegistry`` and delegates execution to a
    per-alias ``RunQueryTool`` instance.
    """

    name: ClassVar = "run_query"

    def __init__(
        self,
        registry: DBRegistry,
        *,
        enable_params: bool = False,
        enable_refresh: bool = False,
        timeout: int | None | object = _UNSET,
        max_visible_rows: int = 20,
        max_cell_width: int = 200,
        floatfmt: str = ".8g",
        history: QueryHistory | None = None,
    ):
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
            enable_params: Whether to expose the ``parameters`` argument to
                the LLM.
            enable_refresh: Whether to expose the ``refresh`` argument to
                the LLM.  When True, the agent can request a connector
                schema refresh after DDL.
            timeout: Query timeout in seconds.  Defaults to
                ``tabulaflow_config.query_timeout``.
            max_visible_rows: Maximum rows shown in the formatted output.
            max_cell_width: Maximum character width per cell in the formatted
                output.
            floatfmt: Float format string passed to tabulate.
            history: Optional shared query-history store. If not provided, the
                tool creates its own in-memory history.
        """
        self.registry = registry
        self.enable_params = enable_params
        self.enable_refresh = enable_refresh
        self.timeout: int | None = tabulaflow_config.query_timeout if timeout is _UNSET else timeout  # type: ignore[assignment]
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self._tools: dict[str, tuple[NL2QDBConnector, RunQueryTool]] = {}
        self._history = history or QueryHistory()

    def _get_tool(self, db_alias: str) -> RunQueryTool:
        """Return a cached ``RunQueryTool`` for ``db_alias``, rebuilding it if the alias was re-bound."""
        connector = self.registry.get(db_alias)
        entry = self._tools.get(db_alias)
        if entry is not None and entry[0] is connector:
            return entry[1]
        tool = RunQueryTool(
            connector,
            enable_params=self.enable_params,
            enable_refresh=self.enable_refresh,
            timeout=self.timeout,
            max_visible_rows=self.max_visible_rows,
            max_cell_width=self.max_cell_width,
            floatfmt=self.floatfmt,
        )
        self._tools[db_alias] = (connector, tool)
        return tool

    async def _run_with_params_with_refresh(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter] = [],
        refresh: bool = False,
    ) -> ToolReturn:
        """Execute a query against a registered database and return the results.

        Returning large result sets is safe — the display is automatically
        truncated, and full execution results are always recorded.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            query: The query to execute.
            parameters: Query parameters.  A list of dictionaries, each
                containing a ``parameter_name`` and a ``parameter_value`` field.
            refresh: If True, re-introspect the connector's schema after
                the query. Use only when the query changes the schema (DDL:
                ``CREATE`` / ``DROP`` / ``ALTER``). Triggers a full schema
                rebuild — be conservative on large cloud warehouses (e.g.
                Snowflake).
        """
        return await self(db_alias, query, parameters, refresh)

    async def _run_with_params(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter] = [],
    ) -> ToolReturn:
        """Execute a query against a registered database and return the results.

        Returning large result sets is safe — the display is automatically
        truncated, and full execution results are always recorded.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            query: The query to execute.
            parameters: Query parameters.  A list of dictionaries, each
                containing a ``parameter_name`` and a ``parameter_value`` field.
        """
        return await self(db_alias, query, parameters, False)

    async def _run_no_params_with_refresh(self, db_alias: str, query: str, refresh: bool = False) -> ToolReturn:
        """Execute a query against a registered database and return the results.

        Returning large result sets is safe — the display is automatically
        truncated, and full execution results are always recorded.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            query: The query to execute.
            refresh: If True, re-introspect the connector's schema after
                the query. Use only when the query changes the schema (DDL:
                ``CREATE`` / ``DROP`` / ``ALTER``). Triggers a full schema
                rebuild — be conservative on large cloud warehouses (e.g.
                Snowflake).
        """
        return await self(db_alias, query, [], refresh)

    async def _run_no_params(self, db_alias: str, query: str) -> ToolReturn:
        """Execute a query against a registered database and return the results.

        Returning large result sets is safe — the display is automatically
        truncated, and full execution results are always recorded.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            query: The query to execute.
        """
        return await self(db_alias, query, [], False)

    async def __call__(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter] | None = None,
        refresh: bool = False,
    ) -> ToolReturn:
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return ToolReturn(
                return_value=f"(error: unknown db_alias: {db_alias!r}; available: {available})",
                metadata=ToolCallOutcome(error=True),
            )
        result = await tool(query, parameters or [], refresh and self.enable_refresh)
        pred_query = tool.last_pred_query()
        record = await self._history.add(db_alias, tool.db_connector.connector_type, pred_query)
        exec_result = pred_query.exec_result
        outcome = None
        if exec_result is not None and exec_result.df is not None:
            outcome = ToolCallOutcome(count=len(exec_result.df), unit="rows")
        elif exec_result is not None and exec_result.error:
            outcome = ToolCallOutcome(error=True)
        return ToolReturn(return_value=f"[record_id={record.record_id}]\n{result}", metadata=outcome)

    def as_pydantic_ai_tool(self) -> Tool:
        fn: Any
        if self.enable_params:
            fn = self._run_with_params_with_refresh if self.enable_refresh else self._run_with_params
        else:
            fn = self._run_no_params_with_refresh if self.enable_refresh else self._run_no_params
        return Tool(fn, name=self.name)

    def metrics(self) -> RunQueryToolMetrics:
        """Return aggregated metrics across all aliases."""
        return sum_tool_metrics((t.metrics() for _, t in self._tools.values()), RunQueryToolMetrics)

    async def get_query_record(self, record_id: str) -> QueryRecord:
        """Return the record for a previously executed query.

        Args:
            record_id: The string ID assigned to the query record at execution time.

        Raises:
            KeyError: If no query with ``record_id`` exists.
        """
        return await self._history.get(record_id)
