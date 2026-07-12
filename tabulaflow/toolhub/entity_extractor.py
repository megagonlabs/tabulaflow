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
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import create_model
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings
from tabulaflow.core.llm import make_agent
from tabulaflow.core.types import Trajectory
from tabulaflow.toolhub.column_types import ALLOWED_COLUMN_TYPES, ColumnType
from tabulaflow.toolhub.markdown_splitter import DEFAULT_MAX_CHARS, DEFAULT_TARGET_CHARS, Chunk, split_markdown

logger = logging.getLogger(__name__)

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
    ``output_columns``; each value is typed per ``column_types`` (defaulting to ``str``)
    so the LLM emits a real ``int``/``float``/``bool``/``str`` (or ``None``) rather than a
    string that a typed target column would have to coerce. No deduplication is performed
    — a record whose evidence straddles a chunk boundary may still be reported by
    neighboring chunks, so dedup downstream with full semantic context if needed.

    The pydantic output model, the extraction Agent, and the concurrency semaphore are
    built once at construction and reused across ``extract`` calls, so build one
    instance per ``output_columns`` schema and reuse it for many documents.
    """

    def __init__(
        self,
        output_columns: list[str],
        *,
        column_types: dict[str, ColumnType] | None = None,
        llm: str | Model = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        chunk_target: int = DEFAULT_TARGET_CHARS,
        chunk_max: int = DEFAULT_MAX_CHARS,
        trajectory_log_dir: Path | None = None,
    ) -> None:
        """Initialize the extractor.

        Args:
            output_columns: Fields each extracted entity populates. Must be non-empty.
            column_types: Optional per-column Python type the LLM emits for that field.
                Each value must be one of ``str``, ``int``, ``float``, ``bool``, ``date``,
                or ``datetime``. Columns absent from the mapping default to ``str`` (the
                all-string behavior). Keys not in ``output_columns`` are ignored.
            llm: LLM identifier or model object used by per-chunk extraction subagents.
            model_settings: Optional pydantic-ai model settings passed to each
                subagent run.
            max_concurrency: Maximum number of chunk subagents to run concurrently
                across all ``extract`` calls on this instance.
            chunk_target: Soft per-chunk size the splitter packs toward — tunes density
                for many-small-entity documents.
            chunk_max: Hard per-chunk ceiling; the only size at which a single block is
                split. A larger entity stays whole up to this.
            trajectory_log_dir: If set, each per-chunk subagent trajectory is written
                as ``<dir>/<label>chunk-<N>.md`` (the ``label`` prefix comes from
                ``extract``'s ``trajectory_label``, distinguishing documents). A
                filesystem sink for local debugging; independent of the returned data.

        Raises:
            ValueError: If ``output_columns`` is empty, ``column_types`` contains an
                unsupported type, or a size argument is invalid.
        """
        if not output_columns:
            raise ValueError("output_columns must be non-empty")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        if chunk_target <= 0 or chunk_max <= 0:
            raise ValueError("chunk_target and chunk_max must be greater than 0")
        bad_types = {col: t for col, t in (column_types or {}).items() if t not in ALLOWED_COLUMN_TYPES}
        if bad_types:
            raise ValueError(f"column_types values must be one of str/int/float/bool/date/datetime; got {bad_types}")

        self.output_columns = output_columns
        self.column_types = column_types or {}
        self.llm = llm
        self.model_settings = model_settings
        self.chunk_target = chunk_target
        self.chunk_max = chunk_max
        self.trajectory_log_dir = trajectory_log_dir

        # Dynamic structured-output model: one nullable, per-column-typed field (str by
        # default), wrapped in a list-bearing container for reliable structured extraction.
        # Typing the field lets the LLM emit a real int/float/bool (or null), so a typed
        # target column receives a native value instead of a string it must coerce.
        entity_model = create_model(
            "ExtractedEntity",
            **{col: (self.column_types.get(col, str) | None, None) for col in output_columns},  # type: ignore[call-overload]
        )
        self._result_model = create_model(
            "ExtractionResult",
            entities=(list[entity_model], ...),  # type: ignore[valid-type]
        )
        self._agent = self._build_agent()
        self._semaphore = asyncio.Semaphore(max_concurrency)

    def apply_llm_profile(self, *, llm: str | Model, model_settings: ModelSettings | None) -> None:
        """Apply the LLM profile used by per-chunk extraction subagents."""
        self.llm = llm
        self.model_settings = model_settings
        self._agent = self._build_agent()

    def _build_agent(self) -> Any:
        return make_agent(
            self.llm,
            output_type=self._result_model,
            model_settings=self.model_settings,
            instructions=_EXTRACTION_SYSTEM_PROMPT,
        )

    async def extract(
        self,
        text: str,
        *,
        instruction: str,
        doc_context: str | None = None,
        on_chunk_complete: Callable[[int], None] | None = None,
        trajectory_label: str | None = None,
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
            trajectory_label: Optional prefix for this document's per-chunk trajectory
                filenames (``<label>chunk-<N>.md``), so trajectories from different
                documents don't collide. Only used when ``trajectory_log_dir`` is set.

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
        prefix = f"{trajectory_label}-" if trajectory_label else ""

        async def _run(chunk_idx: int, prompt: str) -> list[dict[str, Any]]:
            entities = await self._extract_chunk(prompt, f"{prefix}chunk-{chunk_idx}")
            if on_chunk_complete is not None:
                on_chunk_complete(len(entities))
            return entities

        chunk_results = await asyncio.gather(*(_run(i, p) for i, p in enumerate(prompts, start=1)))
        return [entity for chunk in chunk_results for entity in chunk]

    async def _extract_chunk(self, prompt: str, traj_name: str) -> list[dict[str, Any]]:
        async with self._semaphore:
            result = await self._agent.run(prompt)
        self._write_trajectory(traj_name, result)
        output: Any = result.output  # dynamic create_model; fields not statically known
        return [e.model_dump() for e in output.entities]

    def _write_trajectory(self, traj_name: str, result: Any) -> None:
        """Persist one chunk subagent's trajectory as ``<trajectory_log_dir>/<traj_name>.md``.

        Best-effort: trajectory capture is a debug sink and must never affect the
        extraction result, so any failure (dir creation, message conversion, write)
        is logged and swallowed.
        """
        if self.trajectory_log_dir is None:
            return
        try:
            self.trajectory_log_dir.mkdir(parents=True, exist_ok=True)
            traj = Trajectory.from_pydantic_ai_messages(result.all_messages())
            (self.trajectory_log_dir / f"{traj_name}.md").write_text(traj.to_markdown(), encoding="utf-8")
        except Exception:
            logger.exception("Failed to write trajectory %s/%s.md", self.trajectory_log_dir, traj_name)
