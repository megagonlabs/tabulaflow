"""Get-db-document tool backed by a DBRegistry."""

from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

from mintq.db_connector.db_registry import DBRegistry
from mintq.formatters.cypher import CypherSchemaFormatter
from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
from mintq.preprocessors.components.schema_compressor import SchemaCompressor
from mintq.preprocessors.db_summarizer import DBSummarizer

_MAX_CHARS = 50000


class RegistryGetDBDocumentToolMetrics(BaseModel):
    """Metrics for `RegistryGetDBDocumentTool`."""

    num_calls: int = 0
    error_unknown_alias: int = 0
    truncated: int = 0


class RegistryGetDBDocumentTool:
    """Retrieve a human-readable database document for any registered database.

    By default this calls `DBSummarizer` to generate the database document.
    Optionally, small databases can skip summarization and return a direct
    formatted schema document.
    """

    name: ClassVar = "get_db_document"

    def __init__(
        self,
        registry: DBRegistry,
        *,
        db_summarizer_llm: str = "openai-responses:gpt-5.4",
        summary_max_words: int = 2000,
        min_items_for_summary: int = 5,
        enable_refresh: bool = False,
    ) -> None:
        """Initialize the tool.

        Args:
            registry: Registry containing available connectors.
            db_summarizer_llm: LLM ID used by `DBSummarizer` for SQL documents.
            summary_max_words: Target max words for generated db summary.
            min_items_for_summary: Minimum number of schema items required to
                run LLM summarization. SQL uses table count; property-graph uses
                node-label count + relationship-pattern count. If the count is
                lower, returns a direct formatted schema document.
            enable_refresh: If True, expose `refresh` to the LLM tool signature.
        """
        self.registry = registry
        self.db_summarizer_llm = db_summarizer_llm
        self.summary_max_words = summary_max_words
        self.min_items_for_summary = min_items_for_summary
        self.enable_refresh = enable_refresh
        self._sql_formatter = SQLDDLSchemaFormatter()
        self._graph_formatter = CypherSchemaFormatter()
        self._compressor = SchemaCompressor()
        self._metrics = RegistryGetDBDocumentToolMetrics()
        self._document_cache: dict[str, str] = {}

    def _schema_item_count(self, db_alias: str) -> int:
        connector = self.registry.get(db_alias)
        if connector.connector_type == "sql":
            return len(self._compressor.compress(connector.schema).tables)
        if connector.connector_type == "property_graph":
            return len(connector.schema.nodes) + len(connector.schema.relationships)
        return 0

    def _format_direct_document(self, db_alias: str) -> str:
        connector = self.registry.get(db_alias)
        if connector.connector_type == "sql":
            schema = self._compressor.compress(connector.schema)
            self._sql_formatter.set_dialect(schema.dialect)
            return self._sql_formatter.format(schema, add_description=True)
        if connector.connector_type == "property_graph":
            return self._graph_formatter.format(connector.schema)
        raise TypeError(f"Unsupported connector type for get_db_document: {connector.connector_type!r}")

    async def _get_document(self, db_alias: str) -> str:
        cached = self._document_cache.get(db_alias)
        if cached is not None:
            return cached
        connector = self.registry.get(db_alias)
        if self.min_items_for_summary > 0 and self._schema_item_count(db_alias) < self.min_items_for_summary:
            document = self._format_direct_document(db_alias)
        else:
            db_summarizer = DBSummarizer(llm=self.db_summarizer_llm, max_summary_words=self.summary_max_words)
            db_summary = await db_summarizer.preprocess_async(connector)
            document = db_summary.db_summary_markdown
        self._document_cache[db_alias] = document
        return document

    def _truncate(self, text: str) -> str:
        if len(text) <= _MAX_CHARS:
            return text
        self._metrics.truncated += 1
        return text[:_MAX_CHARS] + "\n\n(document truncated)"

    async def _with_refresh(self, db_alias: str, refresh: bool = False) -> str:
        """Get a connector-aware database document.

        Args:
            db_alias: Alias of the target database.
            refresh: If True, refresh schema from the live database before rendering.
        """
        return await self._execute(db_alias, refresh)

    async def _no_refresh(self, db_alias: str) -> str:
        """Get a connector-aware database document.

        Args:
            db_alias: Alias of the target database.
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

        if refresh:
            await connector.refresh_schema_async()
            self._document_cache.pop(db_alias, None)

        try:
            result = await self._get_document(db_alias)
        except TypeError as e:
            return f"(error: {e})"

        return self._truncate(result)

    async def __call__(self, db_alias: str, refresh: bool = False) -> str:
        """Get a connector-aware database document.

        Args:
            db_alias: Alias of the target database.
            refresh: Whether to refresh connector schema before rendering.
        """
        return await self._execute(db_alias, refresh if self.enable_refresh else False)

    def as_pydantic_ai_tool(self) -> Tool:
        fn = self._with_refresh if self.enable_refresh else self._no_refresh
        return Tool(fn, name=self.name)

    def metrics(self) -> RegistryGetDBDocumentToolMetrics:
        return self._metrics
