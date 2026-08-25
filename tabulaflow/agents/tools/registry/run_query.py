"""Run-query tool backed by a DBRegistry, letting agents target any source."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic_ai import Tool, ToolReturn

from tabulaflow.data.protocols import DBConnector
from tabulaflow.data.registry import DBRegistry
from tabulaflow.agents.tools.protocols import ToolCallOutcome, _omit_tool_parameters, sum_tool_metrics
from tabulaflow.output.store import OutputStore
from tabulaflow.agents.tools.run_query import LLMParameter, RunQueryTool, RunQueryToolMetrics

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
        output_store: OutputStore | None = None,
    ):
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
            enable_params: Whether to expose the ``parameters`` argument to
                the LLM.
            enable_refresh: Whether to expose the ``refresh`` argument to
                the LLM.  When True, the agent can request a connector
                schema refresh after DDL.
            timeout: Query timeout in seconds. When omitted, use each connector's
                default; ``None`` explicitly disables the timeout.
            max_visible_rows: Maximum rows shown in the formatted output.
            max_cell_width: Maximum character width per cell in the formatted
                output.
            floatfmt: Float format string passed to tabulate.
            output_store: Optional shared output store. If not provided, the
                tool creates its own in-memory output_store.
        """
        self.registry = registry
        self.enable_params = enable_params
        self.enable_refresh = enable_refresh
        self.timeout = timeout
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self._tools: dict[str, tuple[DBConnector, RunQueryTool]] = {}
        self._output_store = output_store or OutputStore()

    def _get_tool(self, db_alias: str) -> RunQueryTool:
        """Return a cached ``RunQueryTool`` for ``db_alias``, rebuilding it if the alias was re-bound."""
        connector = self.registry.get(db_alias)
        entry = self._tools.get(db_alias)
        if entry is not None and entry[0] is connector:
            return entry[1]
        kwargs: dict[str, Any] = {}
        if self.timeout is not _UNSET:
            kwargs["timeout"] = self.timeout
        tool = RunQueryTool(
            connector,
            enable_params=self.enable_params,
            enable_refresh=self.enable_refresh,
            max_visible_rows=self.max_visible_rows,
            max_cell_width=self.max_cell_width,
            floatfmt=self.floatfmt,
            **kwargs,
        )
        self._tools[db_alias] = (connector, tool)
        return tool

    async def __call__(
        self,
        db_alias: str,
        query: str,
        parameters: list[LLMParameter] | None = None,
        refresh: bool = False,
    ) -> ToolReturn:
        """Execute a query against a registered database.

        Args:
            db_alias: Alias of the target database.
            query: The SQL or Cypher query to execute.
            parameters: Values for named query placeholders. Exposed only when
                parameterized queries are enabled.
            refresh: Whether to refresh connector schema after execution. Exposed
                only when schema refresh is enabled.
        """
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return ToolReturn(
                return_value=f"(error: unknown db_alias: {db_alias!r}; available: {available})",
                metadata=ToolCallOutcome(error=True),
            )
        execution = await tool.execute(query, parameters, refresh and self.enable_refresh)
        exec_result = execution.exec_result
        if exec_result.error is not None:
            return ToolReturn(return_value=execution.output, metadata=ToolCallOutcome(error=True))
        outcome = None
        if exec_result.df is not None:
            outcome = ToolCallOutcome(count=len(exec_result.df), unit="rows")
        source = await self._output_store.add_fixed_result_source(
            db_alias=db_alias,
            connector_type=tool.db_connector.connector_type,
            query=execution.query,
            exec_result=exec_result,
        )
        return ToolReturn(return_value=f"[source_id={source.id}]\n{execution.output}", metadata=outcome)

    def as_pydantic_ai_tool(self) -> Tool:
        omitted = []
        if not self.enable_params:
            omitted.append("parameters")
        if not self.enable_refresh:
            omitted.append("refresh")
        return Tool(self.__call__, name=self.name, prepare=_omit_tool_parameters(*omitted))

    def metrics(self) -> RunQueryToolMetrics:
        """Return aggregated metrics across all aliases."""
        return sum_tool_metrics((t.metrics() for _, t in self._tools.values()), RunQueryToolMetrics)
