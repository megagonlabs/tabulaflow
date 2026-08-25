"""Get-db-document tool backed by a DBRegistry."""

from typing import Any, Callable, ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool, ToolReturn
from pydantic_ai.settings import ModelSettings

from tabulaflow.data.protocols import DBConnector
from tabulaflow.data.registry import DBRegistry
from tabulaflow.output.formatting.cypher import CypherSchemaFormatter
from tabulaflow.output.formatting.sql_ddl import SQLDDLSchemaFormatter
from tabulaflow.agents.tools.base import ToolCallOutcome, _omit_tool_parameters

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
        db_summarizer_cls: Callable[..., Any],
        db_summarizer_llm: str = "openai-responses:gpt-5.4",
        summary_max_words: int = 2000,
        min_items_for_summary: int = 10,
        enable_refresh: bool = False,
        model_settings: ModelSettings | None = None,
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
            model_settings: Optional pydantic-ai model settings passed to
                summarizer agents.
        """
        self.registry = registry
        self._db_summarizer_cls = db_summarizer_cls
        self.db_summarizer_llm = db_summarizer_llm
        self.model_settings = model_settings
        self.summary_max_words = summary_max_words
        self.min_items_for_summary = min_items_for_summary
        self.enable_refresh = enable_refresh
        self._sql_formatter = SQLDDLSchemaFormatter(compact_table_families=True)
        self._graph_formatter = CypherSchemaFormatter()
        self._metrics = RegistryGetDBDocumentToolMetrics()
        self._document_cache: dict[str, tuple[DBConnector, str]] = {}

    def apply_llm_profile(self, *, llm: str, model_settings: ModelSettings | None) -> None:
        """Apply the LLM profile used by generated database summaries."""
        if self.db_summarizer_llm != llm or self.model_settings != model_settings:
            self.db_summarizer_llm = llm
            self.model_settings = model_settings
            self._document_cache.clear()

    def _schema_item_count(self, db_alias: str) -> int:
        connector = self.registry.get(db_alias)
        if connector.connector_type == "sql":
            return len(connector.schema.tables)
        if connector.connector_type == "property_graph":
            pattern_count = sum(len(rel.endpoints) for rel in connector.schema.relationships)
            return len(connector.schema.nodes) + len(connector.schema.relationships) + pattern_count
        return 0

    def _format_direct_document(self, db_alias: str) -> str:
        connector = self.registry.get(db_alias)
        if connector.connector_type == "sql":
            return self._sql_formatter.format(connector.schema, include_descriptions=True)
        if connector.connector_type == "property_graph":
            return self._graph_formatter.format(connector.schema)
        raise TypeError(f"Unsupported connector type for get_db_document: {connector.connector_type!r}")

    async def _get_document(self, db_alias: str) -> str:
        connector = self.registry.get(db_alias)
        cached = self._document_cache.get(db_alias)
        if cached is not None and cached[0] is connector:
            return cached[1]

        use_summarizer = not (
            self.min_items_for_summary > 0 and self._schema_item_count(db_alias) < self.min_items_for_summary
        )

        if use_summarizer:
            db_summarizer = self._db_summarizer_cls(
                llm=self.db_summarizer_llm, max_summary_words=self.summary_max_words, model_settings=self.model_settings
            )
            db_summary = await db_summarizer.summarize(connector)
            document: str = db_summary.db_summary_markdown
        else:
            schema_doc = self._format_direct_document(db_alias)
            document = f"<db_schema>\n{schema_doc}\n</db_schema>"

        self._document_cache[db_alias] = (connector, document)
        return document

    def _truncate(self, text: str) -> str:
        if len(text) <= _MAX_CHARS:
            return text
        self._metrics.truncated += 1
        return text[:_MAX_CHARS] + "\n\n(document truncated)"

    async def execute(self, db_alias: str, refresh: bool = False) -> str:
        """Render a registered database document as agent-facing text."""

        self._metrics.num_calls += 1

        try:
            connector = self.registry.get(db_alias)
        except ValueError:
            self._metrics.error_unknown_alias += 1
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            raise ValueError(f"unknown db_alias: {db_alias!r}; available: {available}") from None

        if refresh:
            try:
                await connector.refresh_schema_async()
            except Exception as exc:
                raise RuntimeError(f"schema refresh failed: {exc}") from exc
            self._document_cache.pop(db_alias, None)

        result = await self._get_document(db_alias)
        return self._truncate(result)

    async def __call__(self, db_alias: str, refresh: bool = False) -> ToolReturn:
        """Get a connector-aware database document.

        Args:
            db_alias: Alias of the target database.
            refresh: Whether to refresh connector schema before rendering.
        """
        try:
            result = await self.execute(db_alias, refresh if self.enable_refresh else False)
        except (ValueError, TypeError, RuntimeError) as exc:
            return ToolReturn(return_value=f"(error: {exc})", metadata=ToolCallOutcome(error=True))
        return ToolReturn(return_value=result)

    def as_pydantic_ai_tool(self) -> Tool:
        omitted = () if self.enable_refresh else ("refresh",)
        return Tool(self.__call__, name=self.name, prepare=_omit_tool_parameters(*omitted))

    def metrics(self) -> RegistryGetDBDocumentToolMetrics:
        return self._metrics
