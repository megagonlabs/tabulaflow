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
from typing import Any

from pydantic import create_model
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

# Chunk geometry defaults: keep one chunk well within a small model's context while
# overlapping enough that an entity straddling a boundary is seen whole by at least
# one chunk.
DEFAULT_CHUNK_CHARS = 12_000
DEFAULT_CHUNK_OVERLAP_CHARS = 1_000

# Worded as "records" deliberately: more generic than "entity" for the model, so it
# does not narrow extraction to named real-world things (covers line items, events,
# facts, etc.).
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


class EntityExtractor:
    """Extract structured entities from document text by chunking and LLM extraction.

    A single document is split into overlapping chunks; a leaf subagent extracts a
    list of entities from each chunk concurrently (bounded by ``max_concurrency``), and
    the union is returned. Entities are flat dicts keyed by ``output_columns`` (all
    string-valued). No deduplication is performed — overlapping chunks may yield the
    same entity twice, so dedup downstream with full semantic context if needed.

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
        chunk_chars: int = DEFAULT_CHUNK_CHARS,
        chunk_overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
    ) -> None:
        """Initialize the extractor.

        Args:
            output_columns: Fields each extracted entity populates. Must be non-empty.
            llm: LLM identifier used by per-chunk extraction subagents.
            model_settings: Optional pydantic-ai model settings passed to each
                subagent run (e.g. ``openai_service_tier``).
            max_concurrency: Maximum number of chunk subagents to run concurrently
                across all ``extract`` calls on this instance.
            chunk_chars: Maximum characters per document chunk.
            chunk_overlap_chars: Overlap between adjacent chunks, so an entity
                spanning a boundary is seen whole by at least one chunk.

        Raises:
            ValueError: If ``output_columns`` is empty or the chunk geometry is
                invalid.
        """
        if not output_columns:
            raise ValueError("output_columns must be non-empty")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        if chunk_chars <= 0:
            raise ValueError("chunk_chars must be greater than 0")
        if not 0 <= chunk_overlap_chars < chunk_chars:
            raise ValueError("chunk_overlap_chars must satisfy 0 <= overlap < chunk_chars")

        self.output_columns = output_columns
        self.chunk_chars = chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars

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
        self._agent = Agent(
            model=llm,
            output_type=self._result_model,
            model_settings=model_settings,
            instructions=_EXTRACTION_SYSTEM_PROMPT,
        )
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def extract(self, text: str, *, instruction: str) -> list[dict[str, Any]]:
        """Extract entities from one document.

        Args:
            text: The document text to extract from.
            instruction: Natural-language description of what one entity is and how
                to populate ``output_columns``.

        Returns:
            One dict per extracted entity, keyed by ``output_columns``. Empty if the
            document is blank or contains no matching entities.
        """
        if not text.strip():
            return []
        chunks = _chunk_text(text, size=self.chunk_chars, overlap=self.chunk_overlap_chars)
        prompts = [f"{instruction}\n\n<document_excerpt>\n{chunk}\n</document_excerpt>" for chunk in chunks]
        chunk_results = await asyncio.gather(*(self._extract_chunk(p) for p in prompts))
        return [entity for chunk in chunk_results for entity in chunk]

    async def _extract_chunk(self, prompt: str) -> list[dict[str, Any]]:
        async with self._semaphore:
            result = await self._agent.run(prompt)
        output: Any = result.output  # dynamic create_model; fields not statically known
        return [e.model_dump() for e in output.entities]
