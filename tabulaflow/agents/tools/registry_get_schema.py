"""Get-schema tool backed by a DBRegistry, with auto-dispatch by connector type."""

from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

from tabulaflow.data.registry import DBRegistry
from tabulaflow.output.formatting.cypher import CypherSchemaFormatter
from tabulaflow.output.formatting.sql_ddl import SQLDDLSchemaFormatter

_DEFAULT_MAX_CHARS = 50000


class RegistryGetSchemaToolMetrics(BaseModel):
    num_calls: int = 0
    error_unknown_alias: int = 0
    truncated: int = 0


class RegistryGetSchemaTool:
    """Retrieve the full schema of any registered database.

    Automatically dispatches to the appropriate formatter based on the
    connector type (SQL via ``SQLDDLSchemaFormatter``, property graph via
    ``CypherSchemaFormatter``).  Large schemas are truncated to
    ``max_chars``.
    """

    name: ClassVar = "get_schema"

    def __init__(
        self,
        registry: DBRegistry,
        *,
        enable_refresh: bool = False,
        max_chars: int = _DEFAULT_MAX_CHARS,
    ):
        """Initialize the tool.

        Args:
            registry: The database registry containing available connectors.
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
        self._metrics = RegistryGetSchemaToolMetrics()

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_chars:
            return text
        self._metrics.truncated += 1
        return (
            text[: self.max_chars]
            + "\n\n(schema truncated — for SQL databases, use get_table_schema to inspect individual tables)"
        )

    async def _with_refresh(self, db_alias: str, refresh: bool = False) -> str:
        """Get the full schema of a registered database.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
            refresh: If True, re-introspect the schema from the live database
                before returning.
        """
        return await self.execute(db_alias, refresh)

    async def _no_refresh(self, db_alias: str) -> str:
        """Get the full schema of a registered database.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
        """
        return await self.execute(db_alias, False)

    async def execute(self, db_alias: str, refresh: bool = False) -> str:
        """Render a registered database schema as agent-facing text."""

        self._metrics.num_calls += 1

        try:
            connector = self.registry.get(db_alias)
        except ValueError:
            self._metrics.error_unknown_alias += 1
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(error: unknown db_alias: {db_alias!r}; available: {available})"

        if connector.connector_type == "sql":
            if refresh:
                await connector.refresh_schema_async()
            result = self._sql_formatter.format(connector.schema, include_descriptions=True)
        elif connector.connector_type == "property_graph":
            if refresh:
                await connector.refresh_schema_async()
            result = self._graph_formatter.format(connector.schema)
        else:
            return f"(error: unsupported connector type: {connector.connector_type!r})"

        return self._truncate(result)

    async def __call__(self, db_alias: str, refresh: bool = False) -> str:
        return await self.execute(db_alias, refresh if self.enable_refresh else False)

    def as_pydantic_ai_tool(self) -> Tool:
        fn = self._with_refresh if self.enable_refresh else self._no_refresh
        return Tool(fn, name=self.name)

    def metrics(self) -> RegistryGetSchemaToolMetrics:
        return self._metrics
