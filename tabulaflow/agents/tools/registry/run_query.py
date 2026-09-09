"""Run-query tool backed by a DataConnectorRegistry, letting agents target any source."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic_ai import Tool, ToolReturn

from tabulaflow.data.protocols import DataConnector
from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.agents.tools.protocols import ToolCallOutcome, _omit_tool_parameters, sum_tool_metrics
from tabulaflow.output.store import OutputStore, ArtifactSourceResolutionError
from tabulaflow.agents.tools.run_query import LLMParameter, RunQueryTool, RunQueryToolMetrics

_UNSET = object()


class RegistryRunQueryTool:
    """Execute a query against any registered data source.

    The agent specifies which connector to target via ``connector_alias``.  The tool
    resolves the alias through a ``DataConnectorRegistry`` and delegates execution to a
    per-alias ``RunQueryTool`` instance.
    """

    name: ClassVar = "run_query"

    def __init__(
        self,
        registry: DataConnectorRegistry,
        *,
        enable_params: bool = False,
        enable_refresh: bool = False,
        enable_media: bool = False,
        timeout: int | None | object = _UNSET,
        max_visible_rows: int = 20,
        max_cell_width: int = 200,
        floatfmt: str = ".8g",
        output_store: OutputStore | None = None,
    ):
        """Initialize the tool.

        Args:
            registry: The connector registry.
            enable_params: Whether to expose the ``parameters`` argument to
                the LLM.
            enable_refresh: Whether to expose the ``refresh`` argument to
                the LLM.  When True, the agent can request a connector
                schema refresh after DDL.
            enable_media: Whether to expose inline result-cell media inspection.
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
        self.enable_media = enable_media
        self.timeout = timeout
        self.max_visible_rows = max_visible_rows
        self.max_cell_width = max_cell_width
        self.floatfmt = floatfmt
        self._tools: dict[str, tuple[DataConnector, RunQueryTool]] = {}
        self._output_store = output_store or OutputStore()

    def _get_tool(self, connector_alias: str) -> RunQueryTool:
        """Return a cached ``RunQueryTool`` for ``connector_alias``, rebuilding it if the alias was re-bound."""
        connector = self.registry.get(connector_alias)
        entry = self._tools.get(connector_alias)
        if entry is not None and entry[0] is connector:
            return entry[1]
        kwargs: dict[str, Any] = {}
        if self.timeout is not _UNSET:
            kwargs["timeout"] = self.timeout
        tool = RunQueryTool(
            connector,
            enable_params=self.enable_params,
            enable_refresh=self.enable_refresh,
            enable_media=self.enable_media,
            max_visible_rows=self.max_visible_rows,
            max_cell_width=self.max_cell_width,
            floatfmt=self.floatfmt,
            **kwargs,
        )
        self._tools[connector_alias] = (connector, tool)
        return tool

    async def __call__(
        self,
        connector_alias: str,
        query: str,
        parameters: list[LLMParameter] | None = None,
        refresh: bool = False,
        include_media: bool = False,
    ) -> ToolReturn:
        """Execute a query against a registered data source.

        Args:
            connector_alias: Alias of the target connector.
            query: The SQL, Cypher, or SPARQL query to execute.
            parameters: Values for named query placeholders. Exposed only when
                parameterized queries are enabled.
            refresh: Whether to refresh connector schema after execution. Exposed
                only when schema refresh is enabled.
            include_media: Whether to attach inline images and PDFs from result cells
                to the model for inspection. Audio and video remain available for
                artifact display but are not attached to the model. Does not fetch
                paths, URLs, or object-store URIs.
        """
        try:
            tool = self._get_tool(connector_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return ToolReturn(
                return_value=f"(error: unknown connector_alias: {connector_alias!r}; available: {available})",
                metadata=ToolCallOutcome(error=True),
            )
        execution = await tool.execute(
            query,
            parameters,
            refresh and self.enable_refresh,
            include_media=include_media and self.enable_media,
        )
        exec_result = execution.exec_result
        if exec_result.error is not None:
            return ToolReturn(return_value=execution.output, metadata=ToolCallOutcome(error=True))
        outcome = None
        if exec_result.df is not None:
            outcome = ToolCallOutcome(count=len(exec_result.df), unit="rows")
        try:
            source = await self._output_store.add_fixed_artifact_source(
                connector_alias=connector_alias,
                query_language=tool.connector.language,
                query=execution.query,
                exec_result=exec_result,
            )
        except ArtifactSourceResolutionError as exc:
            return ToolReturn(return_value=f"(error: {exc})", metadata=ToolCallOutcome(error=True))
        return ToolReturn(
            return_value=f"[source_id={source.id}]\n{execution.output}",
            content=execution.media_content or None,
            metadata=outcome,
        )

    def as_pydantic_ai_tool(self) -> Tool:
        omitted = []
        if not self.enable_params:
            omitted.append("parameters")
        if not self.enable_refresh:
            omitted.append("refresh")
        if not self.enable_media:
            omitted.append("include_media")
        return Tool(self.__call__, name=self.name, prepare=_omit_tool_parameters(*omitted))

    def metrics(self) -> RunQueryToolMetrics:
        """Return aggregated metrics across all aliases."""
        return sum_tool_metrics((t.metrics() for _, t in self._tools.values()), RunQueryToolMetrics)
