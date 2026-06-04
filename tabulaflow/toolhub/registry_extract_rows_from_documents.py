"""Extract entities from documents into rows of a registry-backed table."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from pydantic_ai import Tool
from pydantic_ai.settings import ModelSettings

from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.toolhub.extract_rows_from_documents import ExtractRowsFromDocumentsTool


class RegistryExtractRowsFromDocumentsTool:
    """Extract a list of entities from documents and append them to a table.

    The agent specifies which database to target via ``db_alias``. The tool
    resolves the alias through a ``DBRegistry`` and delegates to a per-alias
    ``ExtractRowsFromDocumentsTool`` instance. ``task_query`` and the appended
    rows both live in that database.
    """

    name: ClassVar[str] = "extract_rows_from_documents"

    def __init__(
        self,
        registry: DBRegistry,
        *,
        subagent_llm: str = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
    ) -> None:
        """Initialize the tool.

        Args:
            registry: Registry containing available connectors.
            subagent_llm: LLM identifier used by per-chunk extraction subagents.
            model_settings: Optional pydantic-ai model settings passed to each
                subagent run (e.g. ``openai_service_tier``).
        """
        self.registry = registry
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.on_row_complete: Callable[[int, int], None] | None = None
        self._tools: dict[str, ExtractRowsFromDocumentsTool] = {}

    def _get_tool(self, db_alias: str) -> ExtractRowsFromDocumentsTool:
        """Return a cached ``ExtractRowsFromDocumentsTool`` for ``db_alias``, creating one if needed."""
        tool = self._tools.get(db_alias)
        if tool is None:
            connector = self.registry.get(db_alias)
            if not isinstance(connector, SQLConnector):
                raise TypeError(
                    f"extract_rows_from_documents is only supported for SQL connectors, not {connector.connector_type!r}"
                )
            tool = ExtractRowsFromDocumentsTool(
                connector,
                subagent_llm=self.subagent_llm,
                model_settings=self.model_settings,
            )
            self._tools[db_alias] = tool
        tool.on_row_complete = self.on_row_complete
        return tool

    async def __call__(
        self,
        db_alias: str,
        schema_name: str | None,
        table_name: str,
        *,
        task_query: str,
        task_instruction: str,
        output_columns: list[str],
    ) -> str:
        """Extract entities from documents and append them as new rows.

        Use this tool to turn unstructured documents into structured rows — the
        row-expansion counterpart to ``run_subagent_for_each_row``. Where that tool
        runs one subagent per input row and writes one value back, this tool reads
        one document per input row and appends many extracted entity rows. Reach for
        it to mine a long web page (or several) into a table of entities.

        ``task_query`` selects the source documents: one result row per document, with
        the document text projected as a column named **``content``**; any other
        columns are available to ``task_instruction``. The common case is a page the
        agent already browsed, which was offloaded to ``_internal.messages`` (already
        has a ``content`` column)::

            SELECT content FROM _internal.messages WHERE message_id = 'M7'

        Each document is split into overlapping chunks and a subagent extracts a list
        of entities from each chunk; all entities across all chunks and documents are
        unioned and appended to ``table_name`` (one row per entity, populating
        ``output_columns``). This tool does not deduplicate — overlapping chunks may
        yield the same entity twice, and entity resolution needs semantic context, so
        run a dedicated dedup step afterward if you need it.

        Args:
            db_alias: Alias of the database holding ``task_query``'s sources and
                receiving the appended rows.
            schema_name: Schema containing ``table_name`` (``None`` if unqualified).
            table_name: Existing target table to append rows into. All
                ``output_columns`` must already exist on it; other columns are
                left NULL/default.
            task_query: SELECT producing one row per source document. Must project
                the document text as a column named ``content`` (alias it if needed,
                e.g. ``SELECT body AS content, url FROM ...``); any other columns are
                variables available to ``task_instruction`` (``content`` itself is NOT
                available to the template). Column order does not matter.
            task_instruction: A Jinja2 template rendered once per source document
                describing what one entity is and how to populate ``output_columns``.
                It may reference any column of ``task_query`` other than ``content``
                (e.g. ``{{ url }}``); the document text itself is not available to the
                template. Example: ``"Extract every product mentioned. For each,
                capture name and price_usd."``
            output_columns: Columns each extracted entity populates. Must be
                non-empty and all must already exist on ``table_name``.
        """
        try:
            tool = self._get_tool(db_alias)
        except ValueError:
            available = ", ".join(self.registry.list_aliases()) or "(none)"
            return f"(unknown db_alias: {db_alias!r}; available: {available})"
        except TypeError as e:
            return f"(error: {e})"
        return await tool(
            schema_name,
            table_name,
            task_query=task_query,
            task_instruction=task_instruction,
            output_columns=output_columns,
        )

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
