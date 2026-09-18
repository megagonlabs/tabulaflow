"""Extract structured entities from documents via an LLM.

Usable standalone, without any database or workspace::

    class Product(BaseModel):
        name: str
        price_usd: float | None = None

    extractor = EntityExtractor()
    entities = await extractor.extract(page_text, record_type=Product, instruction="Extract every product...")

The companion ``ExtractRowsFromDocumentsTool`` is a thin database adapter around this:
it reads documents with SQL, calls :meth:`EntityExtractor.extract` per document, and
appends the results to a table.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import TypeVar, cast

from pydantic import BaseModel
from pydantic_ai import AgentRunResult
from pydantic_ai.messages import BinaryContent, UserContent
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings
from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.media import select_pdf_pages
from tabulaflow.agents.extraction.markdown import (
    DEFAULT_MAX_CHARS,
    DEFAULT_TARGET_CHARS,
    Chunk,
    split_markdown,
)

_PDF_PAGES_PER_CHUNK = 20
_EntityT = TypeVar("_EntityT", bound=BaseModel)

# Worded as "records" deliberately: more generic than "entity" for the model, so it
# does not narrow extraction to named real-world things (covers line items, events,
# facts, etc.).
_EXTRACTION_SYSTEM_PROMPT = (
    "You extract structured records from a document excerpt supplied as text or attached media. Extract every record "
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


def _media_prompts(
    content: BinaryContent,
    instruction: str,
    doc_context: str | None,
) -> list[list[UserContent]]:
    chunks: list[tuple[BinaryContent, str]] = []
    if content.media_type.startswith("image/"):
        chunks.append((content, "Image document"))
    elif content.media_type == "application/pdf":
        pdf = select_pdf_pages(content.data)
        for first_page in range(1, pdf.total_pages + 1, _PDF_PAGES_PER_CHUNK):
            last_page = min(first_page + _PDF_PAGES_PER_CHUNK - 1, pdf.total_pages)
            selected = select_pdf_pages(content.data, (first_page, last_page))
            chunks.append(
                (
                    BinaryContent(data=selected.data, media_type="application/pdf"),
                    f"PDF pages {first_page}-{last_page} of {pdf.total_pages}",
                )
            )
    else:
        raise ValueError(f"unsupported document media type: {content.media_type}")

    prompts: list[list[UserContent]] = []
    for media, chunk_context in chunks:
        context = "\n".join(part for part in (doc_context, chunk_context) if part)
        prompts.append(
            [
                f"{instruction}\n\n<context>\n{context}\n</context>\n\nThe document excerpt is attached.",
                media,
            ]
        )
    return prompts


class EntityExtractor:
    """Extract structured entities from document text or media with an LLM.

    Long documents are split into chunks and processed concurrently. Each result
    is an instance of the supplied model, preserving its validation and defaults.
    Records are returned in chunk order; duplicates across chunks are not removed.
    The concurrency limit is shared across calls, while each call owns its record type
    and agent.
    """

    def __init__(
        self,
        *,
        llm: str | Model = "openai:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        chunk_target: int = DEFAULT_TARGET_CHARS,
        chunk_max: int = DEFAULT_MAX_CHARS,
    ) -> None:
        """Initialize the extractor.

        Args:
            llm: LLM identifier or model object used by per-chunk extraction subagents.
            model_settings: Optional pydantic-ai model settings passed to each
                subagent run.
            max_concurrency: Maximum number of chunk subagents to run concurrently
                across all ``extract`` calls on this instance.
            chunk_target: Soft per-chunk size the splitter packs toward — tunes density
                for many-small-entity documents.
            chunk_max: Hard per-chunk ceiling; the only size at which a single block is
                split. A larger entity stays whole up to this.

        Raises:
            ValueError: If a concurrency or chunk size argument is not positive.
        """
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        if chunk_target <= 0 or chunk_max <= 0:
            raise ValueError("chunk_target and chunk_max must be greater than 0")
        self.llm = llm
        self.model_settings = model_settings
        self.chunk_target = chunk_target
        self.chunk_max = chunk_max

        self._semaphore = asyncio.Semaphore(max_concurrency)

    def apply_llm_profile(self, *, llm: str | Model, model_settings: ModelSettings | None) -> None:
        """Apply the LLM profile used by per-chunk extraction subagents."""
        self.llm = llm
        self.model_settings = model_settings

    async def extract(
        self,
        content: str | BinaryContent | Sequence[BinaryContent],
        *,
        record_type: type[_EntityT],
        instruction: str,
        doc_context: str | None = None,
        on_chunk_complete: Callable[[int, AgentRunResult[list[_EntityT]]], None] | None = None,
    ) -> list[_EntityT]:
        """Extract validated records from one document.

        Args:
            content: Document text, validated image/PDF media, or an ordered
                collection of validated image/PDF media.
            record_type: Pydantic model class describing one record. Required values,
                defaults, constraints, and nullability are preserved.
            instruction: Natural-language description of what one entity is and how
                to populate the declared fields.
            doc_context: Optional document-level context (e.g. ``"Source: <title> (<url>)"``)
                surfaced in every chunk's ``<context>`` block, so provenance/framing
                reaches each excerpt without the caller threading it through ``instruction``.
            on_chunk_complete: Optional callback invoked as each chunk finishes, with
                its 1-based index and agent run result (records, messages, and usage).
                Called in completion order. Callback errors propagate to the caller.

        Returns:
            Instances of ``record_type``, in chunk order. Empty if the document is blank
            or contains no matching records.

        Raises:
            TypeError: If ``record_type`` is not a Pydantic model class.
        """
        if not isinstance(record_type, type) or not issubclass(record_type, BaseModel):
            raise TypeError("record_type must be a Pydantic model class")
        prompts: Sequence[str | Sequence[UserContent]]
        if isinstance(content, str):
            if not content.strip():
                return []
            chunks = split_markdown(content, max_chars=self.chunk_max, target=self.chunk_target)
            prompts = [
                f"{instruction}\n\n<document_excerpt>\n{_render_excerpt(c, doc_context)}\n</document_excerpt>"
                for c in chunks
            ]
        elif isinstance(content, BinaryContent):
            prompts = _media_prompts(content, instruction, doc_context)
        else:
            prompts = []
            total = len(content)
            for index, item in enumerate(content, start=1):
                item_context = "\n".join(part for part in (doc_context, f"Media item {index} of {total}") if part)
                prompts.extend(_media_prompts(item, instruction, item_context))

        if not prompts:
            return []
        agent = make_agent(
            self.llm,
            output_type=list[record_type],  # type: ignore[valid-type]
            model_settings=self.model_settings,
            instructions=_EXTRACTION_SYSTEM_PROMPT,
        )

        async def _run(chunk_idx: int, prompt: str | Sequence[UserContent]) -> list[_EntityT]:
            async with self._semaphore:
                result = cast(AgentRunResult[list[_EntityT]], await agent.run(prompt))
            if on_chunk_complete is not None:
                on_chunk_complete(chunk_idx, result)
            return result.output

        tasks = [asyncio.create_task(_run(i, prompt)) for i, prompt in enumerate(prompts, start=1)]
        try:
            chunk_results = await asyncio.gather(*tasks)
            return [entity for chunk in chunk_results for entity in chunk]
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
