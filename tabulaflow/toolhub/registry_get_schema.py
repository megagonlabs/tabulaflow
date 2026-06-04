"""Get-schema tool backed by a DBRegistry, with auto-dispatch by connector type."""

from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.formatters.cypher import CypherSchemaFormatter
from tabulaflow.core.formatters.sql_ddl import SQLDDLSchemaFormatter
from tabulaflow.core.preprocessors.components.schema_compressor import SchemaCompressor
from tabulaflow.core.types import SQLSchema

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
        self._sql_formatter = SQLDDLSchemaFormatter()
        self._graph_formatter = CypherSchemaFormatter()
        self._compressor = SchemaCompressor()
        self._metrics = RegistryGetSchemaToolMetrics()
        self._compressed_cache: dict[str, SQLSchema] = {}

    def _get_compressed_sql_schema(self, alias: str, schema: SQLSchema) -> SQLSchema:
        """Return a compressed SQL schema, cached per alias."""
        cached = self._compressed_cache.get(alias)
        if cached is not None:
            return cached
        compressed = self._compressor.compress(schema)
        self._compressed_cache[alias] = compressed
        return compressed

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
        return await self._execute(db_alias, refresh)

    async def _no_refresh(self, db_alias: str) -> str:
        """Get the full schema of a registered database.

        Args:
            db_alias: Alias of the target database (see ``list_databases``).
        """
        return await self._execute(db_alias, False)

    async def _execute(self, db_alias: str, refresh: bool) -> str:
        self._metrics.num_calls += 1

        try:
            connector = self.registry.get(db_alias)
        except ValueError:
            self._metrics.error_unknown_alias += 1
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown db_alias: {db_alias!r}; available: {available})"

        if connector.connector_type == "sql":
            if refresh:
                await connector.refresh_schema_async()
                self._compressed_cache.pop(db_alias, None)
            schema = self._get_compressed_sql_schema(db_alias, connector.schema)
            self._sql_formatter.set_dialect(schema.dialect)
            result = self._sql_formatter.format(schema, add_description=True)
        elif connector.connector_type == "property_graph":
            if refresh:
                await connector.refresh_schema_async()
            result = self._graph_formatter.format(connector.schema)
        else:
            return f"(unsupported connector type: {connector.connector_type!r})"

        return self._truncate(result)

    async def __call__(self, db_alias: str, refresh: bool = False) -> str:
        return await self._execute(db_alias, refresh if self.enable_refresh else False)

    def as_pydantic_ai_tool(self) -> Tool:
        fn = self._with_refresh if self.enable_refresh else self._no_refresh
        return Tool(fn, name=self.name)

    def metrics(self) -> RegistryGetSchemaToolMetrics:
        return self._metrics
