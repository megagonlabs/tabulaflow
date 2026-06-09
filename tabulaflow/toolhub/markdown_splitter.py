"""Structure-aware, non-overlapping splitter for markdown documents.

Serves both :mod:`tabulaflow.toolhub.web_browser` snapshots (markdown from a page's
accessibility tree) and PDF/plain text. It is *source-agnostic*: it cuts on whatever
structure exists and degrades through heading → paragraph → line → sentence → hard
char, so a structureless document still splits cleanly.

Two properties replace the old fixed-window + overlap scheme (overlap only existed so a
boundary-straddling entity was seen whole by one chunk, at the cost of duplicates):

1. **Non-overlapping cuts on natural seams** — headings and paragraph breaks; mid-line
   or mid-sentence only when a single line/sentence already exceeds the budget.
2. **Heading-path context across cuts** — a continuation chunk with no heading of its
   own is prefixed with a ``<context>``-wrapped section breadcrumb. So a title appears
   once as extractable content (its inline heading) and as context elsewhere; the
   generic ``<context>`` marker lets one prompt rule ("don't extract from context")
   cover this and any future context line.

Differs from langchain/llama_index markdown splitters (which we don't depend on — both
target RAG indexing): we bound chunk size *and* keep section context in one pass (theirs
split only on headers, then need a heading-blind size splitter chained after); context
rides inline for an LLM reader, not as vector-store metadata; and the API is plain
``str -> list[str]`` with no node/document classes.

Out of scope by choice: **table-header propagation** — re-prepending a split table's
header to its continuation chunks. ``render_aria_markdown`` now emits a header only for
genuine ``<th>`` tables (layout/listing tables get a blank header row), so the signal is
reliable and this is safe to add; deferred because the high-volume targets are headerless
listings where it does nothing, and tables already split as plain lines that keep rows
whole. Also **ref/cleaning**: ``[ref=eN]`` stripping is source-specific, belongs in
preprocessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Default target chunk size in characters. Kept well within a small model's context; the
# section breadcrumb prefix counts against this budget so chunks never exceed it.
DEFAULT_MAX_CHARS = 12_000

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
# Sentence boundary for the last-resort prose split.
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
# Fenced code-block delimiters. Tracked so a ``#`` comment inside code is not mistaken
# for a heading (matching langchain/llama_index behavior).
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass
class _Heading:
    level: int
    title: str
    text: str  # the original heading line


@dataclass
class _Text:
    text: str


_Block = _Heading | _Text


def _parse_blocks(text: str) -> list[_Block]:
    """Parse ``text`` into a flat sequence of heading and prose blocks.

    Blank lines separate prose paragraphs; a ``#``-prefixed line is a heading; a fenced
    code block is captured intact. Everything else — including table rows — accumulates
    into a prose block (tables are split later on line boundaries, which keeps rows
    whole, rather than via unreliable header detection).
    """
    lines = text.split("\n")
    blocks: list[_Block] = []
    para: list[str] = []

    def flush_para() -> None:
        if para:
            body = "\n".join(para).strip()
            if body:
                blocks.append(_Text(text=body))
            para.clear()

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        fence = _FENCE_RE.match(line)
        if fence:
            # Consume the whole fenced block intact, so a ``#`` inside it is never parsed
            # as a heading. Kept as one prose block (split by line if it later exceeds
            # the budget).
            flush_para()
            start = i
            close = fence.group(1)
            i += 1
            while i < n:
                i += 1
                if _FENCE_RE.match(lines[i - 1]) and close in lines[i - 1]:
                    break
            block = "\n".join(ln.rstrip() for ln in lines[start:i]).strip()
            if block:
                blocks.append(_Text(text=block))
            continue
        m = _HEADING_RE.match(line)
        if m:
            flush_para()
            blocks.append(_Heading(level=len(m.group(1)), title=m.group(2).strip(), text=line.rstrip()))
            i += 1
        elif line.strip() == "":
            flush_para()
            i += 1
        else:
            para.append(line)
            i += 1
    flush_para()
    return blocks


def _breadcrumb(stack: list[tuple[int, str]]) -> str:
    """Render the active heading path as a ``<context>`` prefix block (or "").

    The marker is a generic ``<context>...</context>`` block (not a bespoke
    ``[Section: ...]`` token) so a single prompt rule — "never extract from
    ``<context>``" — covers this and any future context line (e.g. a propagated table
    header) folded into the same block.
    """
    if not stack:
        return ""
    path = " > ".join(title for _, title in stack)
    return f"<context>\nSection: {path}\n</context>\n\n"


def _split_prose(text: str, budget: int) -> list[str]:
    """Greedily pack a too-large block into <= ``budget``-char pieces.

    Packs on line boundaries first, so markdown list/table/line structure is preserved
    (newlines are kept, not collapsed to spaces, and table rows stay whole). A single
    line longer than ``budget`` falls back to a sentence pack, and a single sentence
    longer than ``budget`` is hard-sliced — the only place a cut lands mid-sentence.
    """
    budget = max(1, budget)
    pieces: list[str] = []
    cur: list[str] = []
    cur_len = 0

    def flush_cur() -> None:
        nonlocal cur, cur_len
        if cur:
            pieces.append("\n".join(cur))
            cur, cur_len = [], 0

    for line in text.split("\n"):
        if len(line) > budget:
            flush_cur()
            pieces.extend(_split_long_line(line, budget))
            continue
        if cur and cur_len + len(line) + 1 > budget:
            flush_cur()
        cur.append(line)
        cur_len += len(line) + 1
    flush_cur()
    return pieces


def _split_long_line(line: str, budget: int) -> list[str]:
    """Split a single over-budget line on sentence boundaries, hard-slicing as needed."""
    pieces: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for sentence in _SENTENCE_RE.split(line):
        if not sentence:
            continue
        if len(sentence) > budget:
            if cur:
                pieces.append(" ".join(cur))
                cur, cur_len = [], 0
            for start in range(0, len(sentence), budget):
                pieces.append(sentence[start : start + budget])
            continue
        if cur and cur_len + len(sentence) + 1 > budget:
            pieces.append(" ".join(cur))
            cur, cur_len = [], 0
        cur.append(sentence)
        cur_len += len(sentence) + 1
    if cur:
        pieces.append(" ".join(cur))
    return pieces


@dataclass
class _Buffer:
    """Greedy accumulator for small blocks packed into one chunk.

    ``prefix_len`` reserves room for the breadcrumb that flush() prepends to a
    continuation chunk, so the prepend can't push the chunk over ``max_chars``. It is
    fixed by the first block: a heading-led buffer needs no breadcrumb (the heading is
    inline), so its reservation is zero.
    """

    parts: list[str] = field(default_factory=list)
    length: int = 0
    prefix_len: int = 0
    start_stack: list[tuple[int, str]] = field(default_factory=list)
    starts_with_heading: bool = False

    def add(self, block_text: str, stack: list[tuple[int, str]], *, is_heading: bool) -> None:
        if not self.parts:
            self.start_stack = list(stack)
            self.starts_with_heading = is_heading
            self.prefix_len = 0 if is_heading else len(_breadcrumb(stack))
        self.parts.append(block_text)
        self.length += len(block_text) + 2  # for the "\n\n" join

    def would_exceed(self, addition: int, max_chars: int) -> bool:
        """Whether adding ``addition`` chars would push the prefixed chunk over budget."""
        return bool(self.parts) and self.prefix_len + self.length + addition > max_chars


def split_markdown(text: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Split a markdown document into non-overlapping, context-preserving chunks.

    Args:
        text: The document text. May be richly structured markdown (web_browser
            snapshots) or unstructured prose (PDF/plain text) — both are handled.
        max_chars: Target maximum characters per chunk, inclusive of any prepended
            section breadcrumb.

    Returns:
        Chunks in document order. A chunk that continues a section started in an earlier
        chunk is prefixed with a ``<context>``-wrapped section breadcrumb. Returns ``[]``
        for blank input and ``[text]`` for input already within budget.
    """
    if not text.strip():
        return []
    if len(text) <= max_chars:
        return [text]

    blocks = _parse_blocks(text)
    chunks: list[str] = []
    stack: list[tuple[int, str]] = []  # active heading path: (level, title)
    buf = _Buffer()

    def flush() -> None:
        nonlocal buf
        if not buf.parts:
            return
        body = "\n\n".join(buf.parts).strip()
        if body:
            prefix = "" if buf.starts_with_heading else _breadcrumb(buf.start_stack)
            chunks.append(prefix + body)
        buf = _Buffer()

    for block in blocks:
        if isinstance(block, _Heading):
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.title))
            if buf.would_exceed(len(block.text), max_chars):
                flush()
            buf.add(block.text, stack, is_heading=True)
        else:  # _Text
            # A standalone (non-heading-led) chunk is always breadcrumb-prefixed, so the
            # room a fresh buffer has for the block is reduced by the breadcrumb length.
            prefix = _breadcrumb(stack)
            avail = max_chars - len(prefix)
            if len(block.text) <= avail:
                if buf.would_exceed(len(block.text), max_chars):
                    flush()
                buf.add(block.text, stack, is_heading=False)
            else:
                flush()
                for piece in _split_prose(block.text, avail):
                    chunks.append(prefix + piece)
        if buf.prefix_len + buf.length >= max_chars:
            flush()

    flush()
    return chunks
