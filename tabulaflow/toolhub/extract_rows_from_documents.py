"""Extract entities from documents into table rows (the row-expansion dual of run_subagent_for_each_row)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import jinja2
import jinja2.meta
import pandas as pd
from pandas.api import types as pdt
from pydantic_ai import RunContext, Tool
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.toolhub.column_types import resolve_column_types
from tabulaflow.toolhub.utils import qualified_table
from tabulaflow.toolhub.entity_extractor import EntityExtractor
from tabulaflow.toolhub.markdown_splitter import DEFAULT_MAX_CHARS, DEFAULT_TARGET_CHARS

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
    chunk; every chunk's rows are appended to ``table_name``. Deduplication is
    intentionally out of scope (handle it downstream with full semantic context).

    The DB-free extraction engine lives in :class:`EntityExtractor`; this class is the
    database adapter around it (read documents with SQL, write extracted rows back).
    """

    name: ClassVar[str] = "extract_rows_from_documents"

    def __init__(
        self,
        db_connector: SQLConnector,
        *,
        subagent_llm: str | Model = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        chunk_target: int = DEFAULT_TARGET_CHARS,
        chunk_max: int = DEFAULT_MAX_CHARS,
        trajectory_log_dir: Path | None = None,
    ) -> None:
        """Initialize the tool.

        Args:
            db_connector: SQL connector that both evaluates ``task_query`` and
                receives the appended rows (same database).
            subagent_llm: LLM identifier or model object used by per-chunk extraction subagents.
            model_settings: Optional pydantic-ai model settings passed to each
                subagent run (e.g. ``openai_service_tier``).
            max_concurrency: Maximum number of chunk subagents to run
                concurrently across all documents.
            chunk_target: Soft per-chunk size the splitter packs toward.
            chunk_max: Hard per-chunk ceiling; the only size at which a block is split.
            trajectory_log_dir: If set, each per-chunk subagent trajectory is written
                as ``<dir>/<call_id>/doc-<D>-chunk-<N>.md``. A filesystem sink for
                local debugging, mirroring ``run_subagent_for_each_row``.
        """
        self.db_connector = db_connector
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.max_concurrency = max_concurrency
        self.chunk_target = chunk_target
        self.chunk_max = chunk_max
        self.trajectory_log_dir = trajectory_log_dir
        # Called as ``on_rows_extracted(count, tool_call_id)`` with the running count
        # of entities extracted so far; tool_call_id routes progress to the right step.
        self.on_rows_extracted: Callable[[int, str | None], None] | None = None

    async def __call__(
        self,
        ctx: RunContext[Any],
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
        one document per input row and appends many extracted entity rows (e.g.
        mining a long web page into a table of entities). It is the LLM-based
        extraction path: use it when the target data is irregularly formatted,
        requires semantic understanding to extract, or when regex parsing is
        unreliable.

        Internally, each document is split into structure-aware chunks — each carrying
        its section path and any spanning table's header as context so a cut doesn't
        strip the surrounding structure — and a subagent extracts entities from every
        chunk concurrently; every chunk's rows are appended (no dedup), so documents far
        larger than one LLM context are handled.

        ``task_query`` selects the source documents: one result row per document, with
        the document text projected as a column named **``content``**; any other
        columns are available to ``task_instruction``. The common case is a page the
        agent already browsed, which was offloaded to ``_internal.messages`` (already
        has a ``content`` column)::

            SELECT content FROM _internal.messages WHERE message_id = 'M7'

        Entities extracted from each document are appended to ``table_name`` (one row
        per entity, populating ``output_columns``). Any field may be emitted as NULL —
        no placeholder strings like ``"N/A"`` are needed.

        **This tool does not deduplicate.** The same entity may appear in multiple rows,
        and different documents commonly emit variants of the same real-world entity
        (e.g. ``"Microsoft"``, ``"MSFT"``, ``"Microsoft Corp"``). Plan to follow up with a
        canonicalization step.

        Safe to call multiple times in parallel in one turn.

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
                non-empty. All must already exist on ``table_name`` and must be
                scalar, text, or date columns — each value is stored as that column's
                type (numeric/boolean/date → native values; text → text). For
                list/nested values, target a text column holding a JSON string (DuckDB
                ``JSON`` columns work too). Array, struct, map, and binary columns are
                not valid targets.
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
        # entities are extracted from, not a template variable), and require every
        # other placeholder to be a task_query column — catching the mismatch here
        # (vs. StrictUndefined at render time) fails fast and covers the silent
        # ``{{ x | default(...) }}`` / ``is defined`` cases that render empty.
        try:
            parsed = _JINJA_ENV.parse(task_instruction)
        except jinja2.TemplateSyntaxError as e:
            return f"(error: invalid Jinja2 syntax in task_instruction: {e})"
        referenced = jinja2.meta.find_undeclared_variables(parsed)
        if content_col in referenced:
            return (
                f"(error: task_instruction may not reference {content_col!r}; "
                f"it is the document text entities are extracted from, not interpolated into the instruction)"
            )
        unknown = sorted(referenced - set(var_cols))
        if unknown:
            return (
                f"(error: task_instruction references placeholders not in the task_query result: {unknown}; "
                f"available columns (excluding 'content'): {var_cols})"
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

        # Resolve each output column's target type so the LLM emits a native value
        # (int/float/bool/date) instead of a string the database must coerce on INSERT —
        # an unparseable string would otherwise abort the whole batch append. Best-effort
        # off the connector's introspected schema; unresolved columns default to str.
        column_types, unsupported = resolve_column_types(
            self.db_connector.schema, schema_name, table_name, output_columns
        )
        if unsupported:
            return (
                f"(error: cannot extract into non-scalar columns {unsupported} in {qualified_target}; "
                "target scalar, text, or date columns — for list/nested values, use a text column "
                "holding a JSON string)"
            )

        # Per-call trajectory directory (one per __call__, shared across documents);
        # EntityExtractor creates it lazily on first write.
        traj_dir = self.trajectory_log_dir / uuid.uuid4().hex[:12] if self.trajectory_log_dir is not None else None

        try:
            extractor = EntityExtractor(
                output_columns,
                column_types=column_types,
                llm=self.subagent_llm,
                model_settings=self.model_settings,
                max_concurrency=self.max_concurrency,
                chunk_target=self.chunk_target,
                chunk_max=self.chunk_max,
                trajectory_log_dir=traj_dir,
            )
        except ValueError as e:
            return f"(error: {e})"

        rows = df.to_dict(orient="records")
        total_docs = len(rows)
        extracted_count = 0
        tool_call_id = ctx.tool_call_id
        if self.on_rows_extracted is not None and total_docs > 0:
            self.on_rows_extracted(0, tool_call_id)

        def _on_chunk_complete(n: int) -> None:
            nonlocal extracted_count
            extracted_count += n
            if self.on_rows_extracted is not None:
                self.on_rows_extracted(extracted_count, tool_call_id)

        async def _process_document(doc_idx: int, row: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
            content = row.get(content_col)
            error: str | None = None
            entities: list[dict[str, Any]] = []
            try:
                if not isinstance(content, str):
                    return [], None
                instruction = task_template.render({c: row.get(c) for c in var_cols})
                entities = await extractor.extract(
                    content,
                    instruction=instruction,
                    on_chunk_complete=_on_chunk_complete,
                    trajectory_label=f"doc-{doc_idx}",
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                error = f"document {doc_idx}: {type(e).__name__}: {e}"
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
