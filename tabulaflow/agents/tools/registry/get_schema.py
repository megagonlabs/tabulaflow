"""Get-schema tool backed by a DataConnectorRegistry."""

from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool, ToolReturn

from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.output.formatting.cypher import CypherSchemaFormatter
from tabulaflow.output.formatting.sparql import SPARQLSchemaFormatter
from tabulaflow.output.formatting.sql_ddl import SQLDDLSchemaFormatter
from tabulaflow.agents.tools.protocols import ToolCallOutcome, _omit_tool_parameters

_DEFAULT_MAX_CHARS = 50000


class RegistryGetSchemaToolMetrics(BaseModel):
    """Registry schema lookup and truncation counters."""

    num_calls: int = 0
    error_unknown_alias: int = 0
    truncated: int = 0


class RegistryGetSchemaTool:
    """Retrieve the full schema of any registered data source.

    Automatically dispatches to the appropriate formatter based on the tagged
    schema model. Large schemas are truncated to ``max_chars``.
    """

    name: ClassVar = "get_schema"

    def __init__(
        self,
        registry: DataConnectorRegistry,
        *,
        enable_refresh: bool = False,
        max_chars: int = _DEFAULT_MAX_CHARS,
    ):
        """Initialize the tool.

        Args:
            registry: The connector registry.
            enable_refresh: If True, expose the ``refresh`` parameter to the
                LLM.
            max_chars: Maximum characters in the returned schema text.
                Output exceeding this limit is truncated with a notice.
        """
        self.registry = registry
        self.enable_refresh = enable_refresh
        self.max_chars = max_chars
        self._sql_formatter = SQLDDLSchemaFormatter(compact_table_families=True)
        self._graph_formatter = CypherSchemaFormatter()
        self._rdf_formatter = SPARQLSchemaFormatter()
        self._metrics = RegistryGetSchemaToolMetrics()

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_chars:
            return text
        self._metrics.truncated += 1
        return (
            text[: self.max_chars]
            + "\n\n(schema truncated — for SQL databases, use get_table_schema to inspect individual tables)"
        )

    async def execute(self, connector_alias: str, refresh: bool = False) -> str:
        """Render a registered data-source schema as agent-facing text."""

        self._metrics.num_calls += 1

        try:
            connector = self.registry.get(connector_alias)
        except ValueError:
            self._metrics.error_unknown_alias += 1
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            raise ValueError(f"unknown connector_alias: {connector_alias!r}; available: {available}") from None

        from tabulaflow.core import PropertyGraphSchema, RDFSchema, SQLSchema

        schema = connector.schema
        if refresh:
            try:
                schema = await connector.refresh_schema_async()
            except Exception as exc:
                raise RuntimeError(f"schema refresh failed: {exc}") from exc

        if isinstance(schema, SQLSchema):
            result = self._sql_formatter.format(schema, include_descriptions=True)
        elif isinstance(schema, PropertyGraphSchema):
            result = self._graph_formatter.format(schema)
        elif isinstance(schema, RDFSchema):
            result = self._rdf_formatter.format(schema)
        else:
            raise TypeError(f"unsupported schema type: {type(schema)!r}")

        return self._truncate(result)

    async def __call__(self, connector_alias: str, refresh: bool = False) -> ToolReturn:
        """Get the full schema of a registered data source.

        Args:
            connector_alias: Alias of the target connector.
            refresh: Whether to refresh connector schema before rendering.
                Exposed only when schema refresh is enabled.
        """
        try:
            result = await self.execute(connector_alias, refresh if self.enable_refresh else False)
        except (ValueError, TypeError, RuntimeError) as exc:
            return ToolReturn(return_value=f"(error: {exc})", metadata=ToolCallOutcome(error=True))
        return ToolReturn(return_value=result)

    def as_pydantic_ai_tool(self) -> Tool:
        omitted = () if self.enable_refresh else ("refresh",)
        return Tool(self.__call__, name=self.name, prepare=_omit_tool_parameters(*omitted))

    def metrics(self) -> RegistryGetSchemaToolMetrics:
        return self._metrics
