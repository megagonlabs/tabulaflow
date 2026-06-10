"""DB-free engine that extracts structured entities from document text via an LLM.

Usable standalone, without any database or workspace::

    extractor = EntityExtractor(["name", "price_usd"])
    entities = await extractor.extract(page_text, instruction="Extract every product...")

The companion ``ExtractRowsFromDocumentsTool`` is a thin database adapter around this:
it reads documents with SQL, calls :meth:`EntityExtractor.extract` per document, and
appends the results to a table.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from pydantic import create_model
from pydantic_ai.settings import ModelSettings
from tabulaflow.core.llm import make_agent
from tabulaflow.toolhub.markdown_splitter import DEFAULT_MAX_CHARS, DEFAULT_TARGET_CHARS, Chunk, split_markdown

# Worded as "records" deliberately: more generic than "entity" for the model, so it
# does not narrow extraction to named real-world things (covers line items, events,
# facts, etc.).
_EXTRACTION_SYSTEM_PROMPT = (
    "You extract structured records from a document excerpt. Extract every record "
    "that matches the user's instruction and is supported by the excerpt, using only "
    "information present in it — do not infer or invent values. The excerpt may be a "
    "fragment of a larger document; extract whatever is present. "
    "A `<context>...</context>` block at the very start of an excerpt holds context "
    "about where the excerpt sits in the document (e.g. its section path) — it is "
    "context, not content: use it to interpret the excerpt (including to populate "
    "context-dependent fields), but never extract anything inside `<context>` as a "
    "record of its own. Return an empty list if the excerpt contains no matching records."
)


def _render_excerpt(chunk: Chunk, doc_context: str | None) -> str:
    """Render a :class:`Chunk` as the excerpt the model reads.

    The splitter returns context as data; here the consumer turns it into the LLM-facing
    form: a ``<context>`` block (document-level ``doc_context``, the section path, and a
    split table's header — all read-only context the prompt forbids extracting) followed
    by the chunk body. This is the single place the ``<context>`` convention lives, next
    to the system-prompt rule that interprets it.
    """
    lines: list[str] = []
    if doc_context:
        lines.append(doc_context)
    if chunk.section:
        lines.append("Section: " + " > ".join(chunk.section))
    if chunk.table_header:
        lines.append(chunk.table_header)
    prefix = "<context>\n" + "\n".join(lines) + "\n</context>\n\n" if lines else ""
    return prefix + chunk.body


class EntityExtractor:
    """Extract structured entities from document text by chunking and LLM extraction.

    A single document is split into non-overlapping, structure-aware chunks (see
    :func:`tabulaflow.toolhub.markdown_splitter.split_markdown`); a leaf subagent
    extracts a list of entities from each chunk concurrently (bounded by
    ``max_concurrency``), and the union is returned. Entities are flat dicts keyed by
    ``output_columns`` (all string-valued). No deduplication is performed — a record
    whose evidence straddles a chunk boundary may still be reported by neighboring
    chunks, so dedup downstream with full semantic context if needed.

    The pydantic output model, the extraction Agent, and the concurrency semaphore are
    built once at construction and reused across ``extract`` calls, so build one
    instance per ``output_columns`` schema and reuse it for many documents.
    """

    def __init__(
        self,
        output_columns: list[str],
        *,
        llm: str = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        chunk_target: int = DEFAULT_TARGET_CHARS,
        chunk_max: int = DEFAULT_MAX_CHARS,
    ) -> None:
        """Initialize the extractor.

        Args:
            output_columns: Fields each extracted entity populates. Must be non-empty.
            llm: LLM identifier used by per-chunk extraction subagents.
            model_settings: Optional pydantic-ai model settings passed to each
                subagent run (e.g. ``openai_service_tier``).
            max_concurrency: Maximum number of chunk subagents to run concurrently
                across all ``extract`` calls on this instance.
            chunk_target: Soft per-chunk size the splitter packs toward — tunes density
                for many-small-entity documents.
            chunk_max: Hard per-chunk ceiling; the only size at which a single block is
                split. A larger entity stays whole up to this.

        Raises:
            ValueError: If ``output_columns`` is empty or a size argument is invalid.
        """
        if not output_columns:
            raise ValueError("output_columns must be non-empty")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        if chunk_target <= 0 or chunk_max <= 0:
            raise ValueError("chunk_target and chunk_max must be greater than 0")

        self.output_columns = output_columns
        self.chunk_target = chunk_target
        self.chunk_max = chunk_max

        # Dynamic structured-output model: one all-string field per output column,
        # wrapped in a list-bearing container for reliable structured extraction.
        entity_model = create_model(
            "ExtractedEntity",
            **{col: (str | None, None) for col in output_columns},  # type: ignore[call-overload]
        )
        self._result_model = create_model(
            "ExtractionResult",
            entities=(list[entity_model], ...),  # type: ignore[valid-type]
        )
        self._agent = make_agent(
            llm, output_type=self._result_model, model_settings=model_settings, instructions=_EXTRACTION_SYSTEM_PROMPT
        )
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def extract(
        self,
        text: str,
        *,
        instruction: str,
        doc_context: str | None = None,
        on_chunk_complete: Callable[[int], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract entities from one document.

        Args:
            text: The document text to extract from.
            instruction: Natural-language description of what one entity is and how
                to populate ``output_columns``.
            doc_context: Optional document-level context (e.g. ``"Source: <title> (<url>)"``)
                surfaced in every chunk's ``<context>`` block, so provenance/framing
                reaches each excerpt without the caller threading it through ``instruction``.
            on_chunk_complete: Optional callback invoked as each chunk finishes, with
                the number of entities that chunk produced. Chunks run concurrently,
                so it fires in completion order, not document order.

        Returns:
            One dict per extracted entity, keyed by ``output_columns``. Empty if the
            document is blank or contains no matching entities.
        """
        if not text.strip():
            return []
        chunks = split_markdown(text, max_chars=self.chunk_max, target=self.chunk_target)
        prompts = [
            f"{instruction}\n\n<document_excerpt>\n{_render_excerpt(c, doc_context)}\n</document_excerpt>"
            for c in chunks
        ]

        async def _run(prompt: str) -> list[dict[str, Any]]:
            entities = await self._extract_chunk(prompt)
            if on_chunk_complete is not None:
                on_chunk_complete(len(entities))
            return entities

        chunk_results = await asyncio.gather(*(_run(p) for p in prompts))
        return [entity for chunk in chunk_results for entity in chunk]

    async def _extract_chunk(self, prompt: str) -> list[dict[str, Any]]:
        async with self._semaphore:
            result = await self._agent.run(prompt)
        output: Any = result.output  # dynamic create_model; fields not statically known
        return [e.model_dump() for e in output.entities]
