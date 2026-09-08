"""Get-data-source-document tool backed by a DataConnectorRegistry."""

from typing import Any, Callable, ClassVar, cast

from pydantic import BaseModel
from pydantic_ai import Tool, ToolReturn
from pydantic_ai.settings import ModelSettings

from tabulaflow.data.protocols import DataConnector
from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.output.formatting.cypher import CypherSchemaFormatter
from tabulaflow.output.formatting.sparql import SPARQLSchemaFormatter
from tabulaflow.output.formatting.sql_ddl import SQLDDLSchemaFormatter
from tabulaflow.agents.tools.protocols import ToolCallOutcome, _omit_tool_parameters

_MAX_CHARS = 50000


class RegistryGetDataSourceDocumentToolMetrics(BaseModel):
    """Metrics for `RegistryGetDataSourceDocumentTool`."""

    num_calls: int = 0
    error_unknown_alias: int = 0
    truncated: int = 0


class RegistryGetDataSourceDocumentTool:
    """Retrieve a human-readable source document for any registered data source.

    By default this calls `DataSourceSummarizer` to generate the source document.
    Optionally, small sources can skip summarization and return a direct
    formatted schema document.
    """

    name: ClassVar = "get_data_source_document"

    def __init__(
        self,
        registry: DataConnectorRegistry,
        *,
        summarizer_cls: Callable[..., Any],
        summarizer_llm: str = "openai-responses:gpt-5.4",
        summary_max_words: int = 2000,
        min_items_for_summary: int = 10,
        enable_refresh: bool = False,
        model_settings: ModelSettings | None = None,
    ) -> None:
        """Initialize the tool.

        Args:
            registry: Registry containing available connectors.
            summarizer_cls: Data-source summarizer implementation.
            summarizer_llm: LLM ID used for generated source documents.
            summary_max_words: Target maximum words for generated summaries.
            min_items_for_summary: Minimum number of schema items required to
                run LLM summarization. SQL uses table count; property-graph uses
                node-label count + relationship-pattern count. If the count is
                lower, returns a direct formatted schema document.
            enable_refresh: If True, expose `refresh` to the LLM tool signature.
            model_settings: Optional pydantic-ai model settings passed to
                summarizer agents.
        """
        self.registry = registry
        self._summarizer_cls = summarizer_cls
        self.summarizer_llm = summarizer_llm
        self.model_settings = model_settings
        self.summary_max_words = summary_max_words
        self.min_items_for_summary = min_items_for_summary
        self.enable_refresh = enable_refresh
        self._sql_formatter = SQLDDLSchemaFormatter(compact_table_families=True)
        self._graph_formatter = CypherSchemaFormatter()
        self._rdf_formatter = SPARQLSchemaFormatter()
        self._metrics = RegistryGetDataSourceDocumentToolMetrics()
        self._document_cache: dict[str, tuple[DataConnector, str]] = {}

    def apply_llm_profile(self, *, llm: str, model_settings: ModelSettings | None) -> None:
        """Apply the LLM profile used by generated source summaries."""
        if self.summarizer_llm != llm or self.model_settings != model_settings:
            self.summarizer_llm = llm
            self.model_settings = model_settings
            self._document_cache.clear()

    def _schema_item_count(self, connector_alias: str) -> int:
        from tabulaflow.core import PropertyGraphSchema, SQLSchema

        connector = self.registry.get(connector_alias)
        schema = connector.schema
        if isinstance(schema, SQLSchema):
            return len(schema.tables)
        if isinstance(schema, PropertyGraphSchema):
            pattern_count = sum(len(rel.endpoints) for rel in schema.relationships)
            return len(schema.nodes) + len(schema.relationships) + pattern_count
        return 0

    def _format_direct_document(self, connector_alias: str) -> str:
        from tabulaflow.core import PropertyGraphSchema, RDFSchema, SQLSchema

        connector = self.registry.get(connector_alias)
        schema = connector.schema
        if isinstance(schema, SQLSchema):
            return self._sql_formatter.format(schema, include_descriptions=True)
        if isinstance(schema, PropertyGraphSchema):
            return self._graph_formatter.format(schema)
        if isinstance(schema, RDFSchema):
            return self._rdf_formatter.format(schema)
        raise TypeError(f"Unsupported schema type for get_data_source_document: {type(schema)!r}")

    async def _get_document(self, connector_alias: str) -> str:
        connector = self.registry.get(connector_alias)
        cached = self._document_cache.get(connector_alias)
        if cached is not None and cached[0] is connector:
            return cached[1]

        use_summarizer = not (
            self.min_items_for_summary > 0 and self._schema_item_count(connector_alias) < self.min_items_for_summary
        )

        if use_summarizer:
            summarizer = self._summarizer_cls(
                llm=self.summarizer_llm, max_words=self.summary_max_words, model_settings=self.model_settings
            )
            document = cast(str, await summarizer.summarize(connector))
        else:
            schema_doc = self._format_direct_document(connector_alias)
            document = f"<data_source_schema>\n{schema_doc}\n</data_source_schema>"

        self._document_cache[connector_alias] = (connector, document)
        return document

    def _truncate(self, text: str) -> str:
        if len(text) <= _MAX_CHARS:
            return text
        self._metrics.truncated += 1
        return text[:_MAX_CHARS] + "\n\n(document truncated)"

    async def execute(self, connector_alias: str, refresh: bool = False) -> str:
        """Render a registered data-source document as agent-facing text."""

        self._metrics.num_calls += 1

        try:
            connector = self.registry.get(connector_alias)
        except ValueError:
            self._metrics.error_unknown_alias += 1
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            raise ValueError(f"unknown connector_alias: {connector_alias!r}; available: {available}") from None

        if refresh:
            try:
                await connector.refresh_schema_async()
            except Exception as exc:
                raise RuntimeError(f"schema refresh failed: {exc}") from exc
            self._document_cache.pop(connector_alias, None)

        result = await self._get_document(connector_alias)
        return self._truncate(result)

    async def __call__(self, connector_alias: str, refresh: bool = False) -> ToolReturn:
        """Get a connector-aware data-source document.

        Args:
            connector_alias: Alias of the target connector.
            refresh: Whether to refresh connector schema before rendering.
        """
        try:
            result = await self.execute(connector_alias, refresh if self.enable_refresh else False)
        except (ValueError, TypeError, RuntimeError) as exc:
            return ToolReturn(return_value=f"(error: {exc})", metadata=ToolCallOutcome(error=True))
        return ToolReturn(return_value=result)

    def as_pydantic_ai_tool(self) -> Tool:
        omitted = () if self.enable_refresh else ("refresh",)
        return Tool(self.__call__, name=self.name, prepare=_omit_tool_parameters(*omitted))

    def metrics(self) -> RegistryGetDataSourceDocumentToolMetrics:
        return self._metrics
