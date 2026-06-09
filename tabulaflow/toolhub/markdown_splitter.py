"""Structure-aware, non-overlapping splitter for markdown documents.

Serves both :mod:`tabulaflow.toolhub.web_browser` snapshots (markdown from a page's
accessibility tree) and PDF/plain text. It is *source-agnostic*: it cuts on whatever
structure exists and degrades through heading → paragraph → line → sentence → hard
char, so a structureless document still splits cleanly.

Two properties replace the old fixed-window + overlap scheme (overlap only existed so a
boundary-straddling entity was seen whole by one chunk, at the cost of duplicates):

1. **Two-limit packing on natural seams.** Whole blocks (entities — paragraphs, list
   items, table rows) pack into a chunk until it reaches a soft ``target``; a block is
   split only if it alone exceeds the hard ``max_chars``. This covers both regimes: many
   small entities pack densely up to ``target``, while a larger entity stays whole up to
   ``max_chars``. A split *fills the current chunk first* (lazy fill), so a heading rides
   with the first slice of its oversize body instead of being orphaned, and cuts land on
   line → sentence → word boundaries (mid-word only for a single over-long word).
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
from dataclasses import dataclass

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


def _atomize(text: str, limit: int) -> list[str]:
    """Break ``text`` into pieces each ``<= limit`` for lazy fill.

    Splits on line boundaries (preserving markdown structure); an over-long line falls
    back to sentence, then word, then — only when a single word exceeds ``limit`` — a
    hard character cut. Pieces are reassembled by the packer with ``\\n`` joins.
    """
    limit = max(1, limit)
    out: list[str] = []
    for line in text.split("\n"):
        if len(line) <= limit:
            out.append(line)
            continue
        for sentence in _SENTENCE_RE.split(line):
            if not sentence:
                continue
            if len(sentence) <= limit:
                out.append(sentence)
            else:
                out.extend(_wrap_words(sentence, limit))
    return out


def _wrap_words(s: str, limit: int) -> list[str]:
    """Wrap ``s`` at the last space before ``limit``; hard-cut a single over-long word."""
    out: list[str] = []
    while len(s) > limit:
        cut = s.rfind(" ", 1, limit)
        if cut <= 0:
            cut = limit  # a single word longer than the budget: hard char cut
        out.append(s[:cut])
        s = s[cut:].lstrip(" ")
    if s:
        out.append(s)
    return out


class _Packer:
    """Packs markdown blocks into chunks under two limits, with lazy-fill splitting.

    One rule: append whole blocks (entities) to the current chunk until it reaches
    ``target``, then flush. A block is split only if it alone exceeds ``max_chars``, and
    when split its pieces *fill the current chunk first* before spilling into new ones —
    so a heading rides with the first slice of its oversize body instead of being
    orphaned. ``target == max_chars`` degrades to plain greedy-to-ceiling packing.

    Continuation chunks (those not opening with their section's heading) are prefixed
    with a ``<context>`` block naming the section path and, while a real-header table is
    spilling, that table's header — so columns survive the split.
    """

    def __init__(self, target: int, max_chars: int) -> None:
        self.target = target
        self.max_chars = max_chars
        self.chunks: list[str] = []
        self.stack: list[tuple[int, str]] = []  # active heading path
        self.body = ""
        self.start_stack: list[tuple[int, str]] = []  # heading path at this chunk's start
        self.starts_with_heading = False
        self.cont_header: str | None = None  # table header shown in THIS chunk's <context>
        self.table_header: str | None = None  # header of the table currently spilling

    # --- chunk-state helpers ------------------------------------------------

    def _prefix(self) -> str:
        section = "" if self.starts_with_heading else _section_path(self.start_stack)
        return _context_block(section=section, header=self.cont_header)

    def _flush(self) -> None:
        if self.body.strip():
            self.chunks.append(self._prefix() + self.body)
        self.body = ""
        # The next chunk starts as a continuation: it inherits the current section and,
        # if a table is mid-spill, carries that table's header as context.
        self.start_stack = list(self.stack)
        self.starts_with_heading = False
        self.cont_header = self.table_header

    def _fits(self, seg: str, sep: int) -> bool:
        used = len(self._prefix()) + len(self.body) + (sep if self.body else 0)
        return used + len(seg) <= self.max_chars

    def _fits_fresh(self, seg: str) -> bool:
        prefix = _context_block(section=_section_path(self.stack), header=self.table_header)
        return len(prefix) + len(seg) <= self.max_chars

    def _append(self, seg: str, sep: str) -> None:
        self.body = seg if not self.body else self.body + sep + seg

    def _maybe_flush_target(self) -> None:
        if len(self._prefix()) + len(self.body) >= self.target:
            self._flush()

    # --- block handlers -----------------------------------------------------

    def add(self, block: _Block) -> None:
        if isinstance(block, _Heading):
            self._add_heading(block)
        elif isinstance(block, _Table):
            self._add_table(block)
        else:
            self._add_text(block.text)

    def _add_heading(self, block: _Heading) -> None:
        while self.stack and self.stack[-1][0] >= block.level:
            self.stack.pop()
        self.stack.append((block.level, block.title))
        if self.body and not self._fits(block.text, sep=2):
            self._flush()
        if not self.body:
            self.start_stack = list(self.stack)
            self.starts_with_heading = True
        self._append(block.text, "\n\n")
        # No target flush after a heading: keep it with the content that follows.

    def _add_text(self, text: str) -> None:
        if self._fits(text, sep=2):
            self._append(text, "\n\n")
        elif self._fits_fresh(text):
            self._flush()
            self._append(text, "\n\n")
        else:
            self._spill_lines(text, block_sep="\n\n")
        self._maybe_flush_target()

    def _add_table(self, block: _Table) -> None:
        if self._fits(block.text, sep=2):
            self._append(block.text, "\n\n")
            self._maybe_flush_target()
            return
        if self._fits_fresh(block.text):
            self._flush()
            self._append(block.text, "\n\n")
            self._maybe_flush_target()
            return
        # Spill: header inline in the first chunk, then carried in every continuation's
        # <context> so columns survive the row split.
        header = "\n".join(block.header_lines)
        if self.body and not self._fits(header, sep=2):
            self._flush()
        self._append(header, "\n\n")
        self.table_header = header
        for row in block.rows:
            if self.body and not self._fits(row, sep=1):
                self._flush()  # new chunk inherits cont_header = table_header
            self._append(row, "\n")
            self._maybe_flush_target()
        self.table_header = None
        self._flush()  # end the table so the next block doesn't inherit its header context

    def _spill_lines(self, text: str, *, block_sep: str) -> None:
        """Lazy-fill an oversize block: top up the current chunk, then spill into new ones."""
        avail_fresh = self.max_chars - len(_context_block(section=_section_path(self.stack), header=self.table_header))
        atoms = _atomize(text, avail_fresh)
        first = True
        for atom in atoms:
            sep = block_sep if first else "\n"
            if self.body and not self._fits(atom, sep=len(sep)):
                self._flush()
            self._append(atom, sep if self.body else "")
            self._maybe_flush_target()  # honor target within the split, like the table path
            first = False

    def finish(self) -> None:
        self._flush()


def split_markdown(text: str, *, max_chars: int = DEFAULT_MAX_CHARS, target: int | None = None) -> list[str]:
    """Split a markdown document into non-overlapping, context-preserving chunks.

    Whole blocks (entities — paragraphs, list items, table rows) pack into a chunk until
    it reaches ``target``; a block is split only if it alone exceeds ``max_chars``, and a
    split fills the current chunk before spilling, so nothing is orphaned. ``target``
    therefore tunes density for many-small-entity inputs while ``max_chars`` keeps a
    larger entity whole; ``target is None`` packs greedily up to ``max_chars``.

    Args:
        text: The document text. Richly structured markdown (web_browser snapshots) or
            unstructured prose (PDF/plain text) — both are handled.
        max_chars: Hard ceiling per chunk, inclusive of any ``<context>`` prefix. The
            only threshold at which a single block is split.
        target: Soft size to pack toward before flushing. Defaults to ``max_chars``.
            Clamped to ``max_chars``.

    Returns:
        Chunks in document order. A continuation chunk is prefixed with a ``<context>``
        block naming its section path and, when it continues a split table, that table's
        header. Returns ``[]`` for blank input and ``[text]`` for input within budget.
    """
    if not text.strip():
        return []
    eff_target = max_chars if target is None else max(1, min(target, max_chars))
    if len(text) <= eff_target:
        return [text]
    packer = _Packer(target=eff_target, max_chars=max_chars)
    for block in _parse_blocks(text):
        packer.add(block)
    packer.finish()
    return packer.chunks
