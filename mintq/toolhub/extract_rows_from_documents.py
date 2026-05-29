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
from pydantic import create_model
from pydantic_ai import Agent, Tool
from pydantic_ai.settings import ModelSettings

from mintq.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)

# Chunk geometry is internal config, not an LLM-facing knob: the agent should
# not reason about chunk sizes. Defaults keep one chunk well within a small
# model's context while overlapping enough that an entity straddling a boundary
# is seen whole by at least one chunk.
_DEFAULT_CHUNK_CHARS = 12_000
_DEFAULT_CHUNK_OVERLAP_CHARS = 1_000

_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)

_EXTRACTION_SYSTEM_PROMPT = (
    "You extract structured records from a document excerpt. Extract every record "
    "that matches the user's instruction and is supported by the excerpt, using only "
    "information present in it — do not infer or invent values. The excerpt may be a "
    "fragment of a larger document; extract whatever is present. Return an empty list "
    "if the excerpt contains no matching records."
)


def _chunk_text(text: str, *, size: int, overlap: int) -> list[str]:
    """Split ``text`` into overlapping windows of at most ``size`` chars."""
    if len(text) <= size:
        return [text]
    step = size - overlap
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += step
    return chunks


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
    """

    name: ClassVar[str] = "extract_rows_from_documents"

    def __init__(
        self,
        db_connector: SQLConnector,
        *,
        subagent_llm: str = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        chunk_chars: int = _DEFAULT_CHUNK_CHARS,
        chunk_overlap_chars: int = _DEFAULT_CHUNK_OVERLAP_CHARS,
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
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        if chunk_chars <= 0:
            raise ValueError("chunk_chars must be greater than 0")
        if not 0 <= chunk_overlap_chars < chunk_chars:
            raise ValueError("chunk_overlap_chars must satisfy 0 <= overlap < chunk_chars")
        self.db_connector = db_connector
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.max_concurrency = max_concurrency
        self.chunk_chars = chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars
        self.on_row_complete: Callable[[int, int], None] | None = None

    async def __call__(
        self,
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
            table_name: Existing target table to append rows into. May be
                schema-qualified (e.g. ``schema.table``). All ``output_columns``
                must already exist on it; other columns are left NULL/default.
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
        # records are extracted from, not a template variable); other undefined
        # references surface at render time via StrictUndefined.
        try:
            parsed = _JINJA_ENV.parse(task_instruction)
        except jinja2.TemplateSyntaxError as e:
            return f"(error: invalid Jinja2 syntax in task_instruction: {e})"
        if content_col in jinja2.meta.find_undeclared_variables(parsed):
            return (
                f"(error: task_instruction may not reference {content_col!r}; "
                f"it is the document text records are extracted from, not interpolated into the instruction)"
            )
        task_template = _JINJA_ENV.from_string(task_instruction)

        # output_columns must already exist on the target table.
        table_columns_result = await self.db_connector.run_query_async(f"SELECT * FROM {table_name} LIMIT 0")
        if table_columns_result.error is not None or table_columns_result.df is None:
            detail = (
                table_columns_result.error.message
                if table_columns_result.error is not None
                else "no dataframe returned"
            )
            return f"(error: failed to inspect target table {table_name!r}: {detail})"
        table_columns = [str(c) for c in table_columns_result.df.columns]
        missing = [c for c in output_columns if c not in table_columns]
        if missing:
            return f"(error: output_columns not found in table {table_name!r}: {missing})"

        # Dynamic structured-output model: one all-string field per output column,
        # wrapped in a list-bearing container for reliable structured extraction.
        record_model = create_model(
            "ExtractedRecord",
            **{col: (str | None, None) for col in output_columns},  # type: ignore[call-overload]
        )
        result_model = create_model(
            "ExtractionResult",
            records=(list[record_model], ...),  # type: ignore[valid-type]
        )

        extractor = Agent(
            model=self.subagent_llm,
            output_type=result_model,
            model_settings=self.model_settings,
            instructions=_EXTRACTION_SYSTEM_PROMPT,
        )

        rows = df.to_dict(orient="records")
        total_docs = len(rows)
        semaphore = asyncio.Semaphore(self.max_concurrency)
        completed_docs = 0

        async def _extract_chunk(prompt: str) -> list[dict[str, Any]]:
            async with semaphore:
                result = await extractor.run(prompt)
            output: Any = result.output  # dynamic create_model; fields not statically known
            return [r.model_dump() for r in output.records]

        async def _process_document(doc_idx: int, row: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
            nonlocal completed_docs
            content = row.get(content_col)
            error: str | None = None
            entities: list[dict[str, Any]] = []
            cancelled = False
            try:
                if not isinstance(content, str) or not content.strip():
                    return [], None
                instruction = task_template.render({c: row.get(c) for c in var_cols})
                chunks = _chunk_text(content, size=self.chunk_chars, overlap=self.chunk_overlap_chars)
                prompts = [f"{instruction}\n\n<document_excerpt>\n{chunk}\n</document_excerpt>" for chunk in chunks]
                chunk_results = await asyncio.gather(*(_extract_chunk(p) for p in prompts))
                for cr in chunk_results:
                    entities.extend(cr)
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
            schema_name: str | None
            if "." in table_name:
                schema_name, _, target_table = table_name.rpartition(".")
            else:
                schema_name, target_table = None, table_name
            try:
                written = await self.db_connector.write_dataframe_async(
                    df=out_df,
                    table_name=target_table,
                    schema_name=schema_name,
                    mode="append",
                )
            except ValueError as e:
                return f"(error: failed to append extracted rows to {table_name!r}: {e})"

        summary = f"Extracted {written} entities from {total_docs} documents; appended to {table_name}."
        if errors:
            summary += "\nSample errors:\n" + "\n".join(f"- {e}" for e in errors[:5])
        return summary

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
