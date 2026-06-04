"""Extract entities from documents into table rows (the row-expansion dual of run_subagent_for_each_row)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any, ClassVar

import jinja2
import jinja2.meta
import pandas as pd
from pandas.api import types as pdt
from pydantic_ai import Tool
from pydantic_ai.settings import ModelSettings

from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.core.tools.utils import qualified_table
from tabulaflow.toolhub.entity_extractor import DEFAULT_CHUNK_CHARS, DEFAULT_CHUNK_OVERLAP_CHARS, EntityExtractor

logger = logging.getLogger(__name__)

_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)


class ExtractRowsFromDocumentsTool:
    """Extract a list of entities from each source document and append them as table rows.

    This is the row-expansion dual of ``run_subagent_for_each_row`` (which expands
    columns): one source document in, many entity rows out. ``task_query`` yields
    one row per document — its first column is the document text, the remaining
    columns feed the ``task_instruction`` Jinja template. ``task_query`` must project
    the document text as a column named ``content``; any other columns feed the
    template. Each document is chunked and a leaf subagent extracts entities from each
    chunk; the union is appended to ``table_name``. Deduplication is intentionally out
    of scope (handle it downstream with full semantic context).

    The DB-free extraction engine lives in :class:`EntityExtractor`; this class is the
    database adapter around it (read documents with SQL, write extracted rows back).
    """

    name: ClassVar[str] = "extract_rows_from_documents"

    def __init__(
        self,
        db_connector: SQLConnector,
        *,
        subagent_llm: str = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        chunk_chars: int = DEFAULT_CHUNK_CHARS,
        chunk_overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
    ) -> None:
        """Initialize the tool.

        Args:
            db_connector: SQL connector that both evaluates ``task_query`` and
                receives the appended rows (same database).
            subagent_llm: LLM identifier used by per-chunk extraction subagents.
            model_settings: Optional pydantic-ai model settings passed to each
                subagent run (e.g. ``openai_service_tier``).
            max_concurrency: Maximum number of chunk subagents to run
                concurrently across all documents.
            chunk_chars: Maximum characters per document chunk.
            chunk_overlap_chars: Overlap between adjacent chunks, so an entity
                spanning a boundary is seen whole by at least one chunk.
        """
        self.db_connector = db_connector
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.max_concurrency = max_concurrency
        self.chunk_chars = chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars
        self.on_row_complete: Callable[[int, int], None] | None = None

    async def __call__(
        self,
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

        Entities extracted from each document are appended to ``table_name`` (one row
        per entity, populating ``output_columns``). **This tool does not deduplicate.**
        The same entity may appear in multiple rows, and different documents commonly
        emit variants of the same real-world entity (e.g. ``"Microsoft"``, ``"MSFT"``,
        ``"Microsoft Corp"``). Plan to follow up with a canonicalization step.

        Args:
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
        if not output_columns:
            return "(error: output_columns must be non-empty)"

        select_result = await self.db_connector.run_query_async(task_query)
        if select_result.error is not None or select_result.df is None:
            detail = select_result.error.message if select_result.error is not None else "no dataframe returned"
            return f"(error: failed to evaluate task_query: {detail})"

        df = select_result.df
        source_columns = [str(c) for c in df.columns]
        if not source_columns:
            return "(error: task_query returned no columns)"

        content_col = "content"
        if content_col not in source_columns:
            return (
                "(error: task_query must project the document text as a column named 'content' "
                "(e.g. SELECT body AS content, url FROM ...))"
            )
        var_cols = [c for c in source_columns if c != content_col]
        if not (pdt.is_object_dtype(df[content_col]) or pdt.is_string_dtype(df[content_col])):
            return f"(error: the 'content' column must hold document text, but has dtype {df[content_col].dtype})"

        # Compile the template. Reject {{ content }} upfront (it is the source the
        # entities are extracted from, not a template variable); other undefined
        # references surface at render time via StrictUndefined.
        try:
            parsed = _JINJA_ENV.parse(task_instruction)
        except jinja2.TemplateSyntaxError as e:
            return f"(error: invalid Jinja2 syntax in task_instruction: {e})"
        if content_col in jinja2.meta.find_undeclared_variables(parsed):
            return (
                f"(error: task_instruction may not reference {content_col!r}; "
                f"it is the document text entities are extracted from, not interpolated into the instruction)"
            )
        task_template = _JINJA_ENV.from_string(task_instruction)

        # output_columns must already exist on the target table.
        qualified_target = qualified_table(schema_name, table_name)
        table_columns_result = await self.db_connector.run_query_async(f"SELECT * FROM {qualified_target} LIMIT 0")
        if table_columns_result.error is not None or table_columns_result.df is None:
            detail = (
                table_columns_result.error.message
                if table_columns_result.error is not None
                else "no dataframe returned"
            )
            return f"(error: failed to inspect target table {qualified_target}: {detail})"
        table_columns = [str(c) for c in table_columns_result.df.columns]
        missing = [c for c in output_columns if c not in table_columns]
        if missing:
            return f"(error: output_columns not found in table {qualified_target}: {missing})"

        try:
            extractor = EntityExtractor(
                output_columns,
                llm=self.subagent_llm,
                model_settings=self.model_settings,
                max_concurrency=self.max_concurrency,
                chunk_chars=self.chunk_chars,
                chunk_overlap_chars=self.chunk_overlap_chars,
            )
        except ValueError as e:
            return f"(error: {e})"

        rows = df.to_dict(orient="records")
        total_docs = len(rows)
        completed_docs = 0
        # Emit a 0/total tick up front so the UI shows the counter immediately
        # rather than sitting empty until the first document finishes.
        if self.on_row_complete is not None and total_docs > 0:
            self.on_row_complete(0, total_docs)

        async def _process_document(doc_idx: int, row: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
            nonlocal completed_docs
            content = row.get(content_col)
            error: str | None = None
            entities: list[dict[str, Any]] = []
            cancelled = False
            try:
                if not isinstance(content, str):
                    return [], None
                instruction = task_template.render({c: row.get(c) for c in var_cols})
                entities = await extractor.extract(content, instruction=instruction)
            except asyncio.CancelledError:
                cancelled = True
                raise
            except Exception as e:
                error = f"document {doc_idx}: {type(e).__name__}: {e}"
            finally:
                if not cancelled:
                    completed_docs += 1
                    if self.on_row_complete is not None:
                        self.on_row_complete(completed_docs, total_docs)
                        await asyncio.sleep(0)
            return entities, error

        results = await asyncio.gather(*(_process_document(i, row) for i, row in enumerate(rows, start=1)))

        all_entities: list[dict[str, Any]] = []
        errors: list[str] = []
        for entities, error in results:
            all_entities.extend(entities)
            if error is not None:
                errors.append(error)

        written = 0
        if all_entities:
            out_df = pd.DataFrame(all_entities, columns=output_columns)
            try:
                written = await self.db_connector.write_dataframe_async(
                    df=out_df,
                    table_name=table_name,
                    schema_name=schema_name,
                    mode="append",
                )
            except ValueError as e:
                return f"(error: failed to append extracted rows to {qualified_target}: {e})"

        summary = f"Extracted {written} entities from {total_docs} documents; appended to {qualified_target}."
        if errors:
            summary += "\nSample errors:\n" + "\n".join(f"- {e}" for e in errors[:5])
        return summary

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
