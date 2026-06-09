"""Structure-aware, non-overlapping splitter for markdown documents.

Serves both :mod:`tabulaflow.toolhub.web_browser` snapshots (markdown from a page's
accessibility tree) and PDF/plain text. It is *source-agnostic*: it cuts on whatever
structure exists and degrades through heading → paragraph → line → sentence → hard
char, so a structureless document still splits cleanly.

Two properties replace the old fixed-window + overlap scheme (overlap only existed so a
boundary-straddling entity was seen whole by one chunk, at the cost of duplicates):

1. **Non-overlapping cuts on natural seams** — headings and paragraph breaks; mid-line
   or mid-sentence only when a single line/sentence already exceeds the budget.
2. **Context across cuts**, carried in a ``<context>``-wrapped prefix on any continuation
   chunk (one prompt rule covers it: "don't extract from context"):

   * *Section path* — a continuation chunk with no heading of its own names the section
     it's in. A title thus appears once as extractable content (its inline heading) and
     as context elsewhere.
   * *Table header* — when a real ``<th>`` table is split, its header row + separator
     ride in the ``<context>`` of every continuation chunk so columns aren't lost (the
     header still appears once inline, in the table's first chunk). Layout/listing tables
     have no real header — ``render_aria_markdown`` gives them a blank header row — so
     they don't trigger this and just split as plain lines (rows kept whole).

Differs from langchain/llama_index markdown splitters (which we don't depend on — both
target RAG indexing): we bound chunk size *and* keep section/table context in one pass
(theirs split only on headers, then need a heading-blind size splitter chained after);
context rides inline for an LLM reader, not as vector-store metadata; and the API is
plain ``str -> list[str]`` with no node/document classes.

Out of scope by choice: **ref/cleaning** — ``[ref=eN]`` stripping is source-specific and
belongs in preprocessing, not this generic splitter.
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
# A markdown table separator row, e.g. ``| --- | :--: |`` (only pipes, dashes, colons, ws).
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


@dataclass
class _Heading:
    level: int
    title: str
    text: str  # the original heading line


@dataclass
class _Table:
    """A pipe table with a *real* (non-blank) header — its header row + separator are
    re-prepended as context to every continuation chunk so columns aren't lost on a
    split. Layout/listing tables (blank header) never become a ``_Table``; they stay
    prose and split as plain lines."""

    header_lines: list[str]  # header row + ``| --- |`` separator
    rows: list[str]  # data rows, kept whole
    text: str  # the full table, for the fits-whole fast path


@dataclass
class _Text:
    text: str


_Block = _Heading | _Table | _Text


def _parse_blocks(text: str) -> list[_Block]:
    """Parse ``text`` into a flat sequence of heading, table, and prose blocks.

    Blank lines separate prose paragraphs; a ``#``-prefixed line is a heading; a fenced
    code block is captured intact. A run of ``|`` lines becomes a ``_Table`` only if it
    has a real (non-blank) header row + separator; a layout/listing table (blank header,
    as the renderer emits for headerless tables) stays prose and splits as plain lines.
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
        elif _is_table_row(line):
            start = i
            while i < n and _is_table_row(lines[i]):
                i += 1
            run = [ln.rstrip() for ln in lines[start:i]]
            if _has_real_header(run):
                flush_para()
                blocks.append(_Table(header_lines=run[:2], rows=run[2:], text="\n".join(run)))
            else:
                para.extend(run)  # layout/listing table → plain prose
        elif line.strip() == "":
            flush_para()
            i += 1
        else:
            para.append(line)
            i += 1
    flush_para()
    return blocks


def _is_table_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def _has_real_header(run: list[str]) -> bool:
    """True if a ``|``-run opens with a non-blank header row over a ``| --- |`` separator.

    The renderer emits a blank header (all-empty cells) for headerless layout/listing
    tables, so a non-blank header reliably marks a genuine ``<th>`` data table.
    """
    if len(run) < 2 or not _TABLE_SEP_RE.match(run[1]):
        return False
    cells = [c.strip() for c in run[0].strip().strip("|").split("|")]
    return any(cells)


def _context_block(*, section: str, header: str | None) -> str:
    """Build the generic ``<context>...</context>`` prefix (or "" if there's nothing).

    Holds whatever context a continuation chunk needs — the section path and/or a split
    table's header — so a single prompt rule ("never extract from ``<context>``") covers
    all of it. Lines: ``Section: A > B`` and/or the table ``header`` (row + separator).
    """
    lines = []
    if section:
        lines.append(f"Section: {section}")
    if header:
        lines.append(header)
    if not lines:
        return ""
    return "<context>\n" + "\n".join(lines) + "\n</context>\n\n"


def _section_path(stack: list[tuple[int, str]]) -> str:
    return " > ".join(title for _, title in stack)


def _breadcrumb(stack: list[tuple[int, str]]) -> str:
    """The section-only ``<context>`` prefix for a continuation chunk (or "")."""
    return _context_block(section=_section_path(stack), header=None)


def _emit_table_chunks(table: _Table, stack: list[tuple[int, str]], max_chars: int) -> list[str]:
    """Split an oversize real-header table on row boundaries (rows kept whole).

    The header appears once as inline content (the first chunk renders the table
    normally); every continuation chunk carries it inside ``<context>`` instead, so
    column meaning survives the split without re-extracting the header as a record.
    """
    section = _section_path(stack)
    header = "\n".join(table.header_lines)
    # Reserve room for the larger of the two per-chunk overheads (first chunk: section
    # context + inline header; continuation: section + header inside context) so neither
    # can exceed the budget.
    first_overhead = len(_context_block(section=section, header=None)) + len(header) + 1
    cont_overhead = len(_context_block(section=section, header=header))
    body_budget = max(1, max_chars - max(first_overhead, cont_overhead))

    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0

    def emit() -> None:
        nonlocal cur, cur_len
        if not cur:
            return
        if not chunks:  # first chunk: header inline as content, section-only context
            chunks.append(_context_block(section=section, header=None) + header + "\n" + "\n".join(cur))
        else:  # continuation: header carried as context
            chunks.append(_context_block(section=section, header=header) + "\n".join(cur))
        cur, cur_len = [], 0

    for row in table.rows:
        if cur and cur_len + len(row) + 1 > body_budget:
            emit()
        cur.append(row)
        cur_len += len(row) + 1
    emit()
    return chunks


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
        Chunks in document order. A continuation chunk is prefixed with a ``<context>``
        block naming its section path and, when it continues a split table, that table's
        header. Returns ``[]`` for blank input and ``[text]`` for input within budget.
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
            continue

        # _Table and _Text share the standalone path: a non-heading-led chunk is always
        # breadcrumb-prefixed, so a fresh buffer's room for the block is reduced by it.
        prefix = _breadcrumb(stack)
        avail = max_chars - len(prefix)
        if len(block.text) <= avail:
            if buf.would_exceed(len(block.text), max_chars):
                flush()
            buf.add(block.text, stack, is_heading=False)
        elif isinstance(block, _Table):
            flush()
            chunks.extend(_emit_table_chunks(block, stack, max_chars))
        else:  # oversize _Text
            flush()
            for piece in _split_prose(block.text, avail):
                chunks.append(prefix + piece)
        if buf.prefix_len + buf.length >= max_chars:
            flush()

    flush()
    return chunks
