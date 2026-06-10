"""Tests for the structure-aware markdown splitter."""

from tabulaflow.toolhub.markdown_splitter import (
    DEFAULT_MAX_CHARS,
    DEFAULT_TARGET_CHARS,
    split_markdown,
)


def _strip_breadcrumbs(chunk: str) -> str:
    """Drop a leading ``<context>...</context>`` prefix so chunk bodies can be compared."""
    if chunk.startswith("<context>"):
        return chunk.split("</context>\n\n", 1)[1] if "</context>\n\n" in chunk else ""
    return chunk


def _context(*sections: str) -> str:
    """The ``<context>`` breadcrumb prefix a continuation chunk in ``sections`` carries."""
    return "<context>\nSection: " + " > ".join(sections) + "\n</context>"


class TestPassthrough:
    def test_blank_returns_empty(self) -> None:
        assert split_markdown("") == []
        assert split_markdown("   \n  ") == []

    def test_small_doc_returns_single_chunk_verbatim(self) -> None:
        text = "# Title\n\nA short paragraph."
        assert split_markdown(text, max_chars=1000) == [text]


class TestBudget:
    def test_no_chunk_exceeds_max_chars(self) -> None:
        # Many short paragraphs that must be packed under a tight budget.
        text = "\n\n".join(f"Paragraph number {i} with a little text." for i in range(200))
        chunks = split_markdown(text, max_chars=300)
        assert len(chunks) > 1
        assert all(len(c) <= 300 for c in chunks)

    def test_oversize_single_line_is_hard_split(self) -> None:
        # One line longer than the budget, no sentence breaks → hard char slices.
        text = "x" * 5000
        chunks = split_markdown(text, max_chars=1000)
        assert all(len(c) <= 1000 for c in chunks)
        assert "".join(chunks) == text


class TestTwoLimitPacking:
    def test_target_packs_many_small_entities_below_target(self) -> None:
        text = "\n\n".join(f"Entity number {i}." for i in range(200))
        chunks = split_markdown(text, max_chars=8000, target=500)
        assert len(chunks) > 1
        # Each chunk fills toward target, overshooting by at most the block that crossed it.
        assert all(len(c) <= 560 for c in chunks)

    def test_block_between_target_and_max_is_kept_whole(self) -> None:
        big = ("word " * 400).strip()  # ~2000 chars: above target, below max → never split
        text = f"alpha.\n\n{big}\n\nomega."
        chunks = split_markdown(text, max_chars=8000, target=500)
        assert any(big in c for c in chunks)  # present intact in a single chunk

    def test_heading_not_orphaned_before_oversize_body(self) -> None:
        body = ("word " * 4000).strip()  # one oversize line that must be split
        text = f"## History\n\n{body}"
        chunks = split_markdown(text, max_chars=500)
        # The heading rides with the first slice of its body, not alone in a tiny chunk.
        assert chunks[0].startswith("## History")
        assert len(chunks[0].strip()) > len("## History") + 20
        assert all(c.strip() != "## History" for c in chunks)

    def test_long_line_wraps_on_word_boundaries(self) -> None:
        text = ("alpha bravo charlie delta echo foxtrot " * 60).strip()  # one long line, > max
        chunks = split_markdown(text, max_chars=200)
        # Reassembling on whitespace yields the exact source words → no mid-word cuts, no loss.
        assert " ".join(chunks).split() == text.split()

    def test_defaults_split_between_target_and_max(self) -> None:
        # A doc above DEFAULT_TARGET_CHARS but below DEFAULT_MAX_CHARS must still split
        # under the defaults — i.e. the soft target is active, not dormant.
        assert DEFAULT_TARGET_CHARS < DEFAULT_MAX_CHARS
        n = (DEFAULT_TARGET_CHARS * 2) // 40
        text = "\n\n".join(f"Paragraph {i} with a little filler body here." for i in range(n))
        assert DEFAULT_TARGET_CHARS < len(text) < DEFAULT_MAX_CHARS
        chunks = split_markdown(text)  # defaults
        assert len(chunks) > 1
        assert all(len(c) <= DEFAULT_MAX_CHARS for c in chunks)

    def test_target_none_packs_to_max(self) -> None:
        text = "\n\n".join(f"Paragraph {i} with a little body text here." for i in range(300))
        chunks = split_markdown(text, max_chars=2000, target=None)
        assert all(len(c) <= 2000 for c in chunks)
        # Greedy-to-ceiling: most chunks should be reasonably full, not target-sized.
        assert max(len(c) for c in chunks) > 1500


class TestHeadingBreadcrumb:
    def test_continuation_chunks_carry_section_breadcrumb(self) -> None:
        body = "\n\n".join(f"Sentence {i} in the history section." for i in range(100))
        text = f"# Python\n\n## History\n\n{body}"
        chunks = split_markdown(text, max_chars=400)
        # The section spans several chunks; every chunk after the first that does not
        # itself begin with the heading must carry the breadcrumb.
        continuation = [c for c in chunks if not c.startswith("# Python") and "## History" not in c]
        assert continuation, "expected at least one continuation chunk"
        assert all(c.startswith(_context("Python", "History")) for c in continuation)

    def test_nested_heading_path(self) -> None:
        body = "\n\n".join(f"Detail line {i} goes here with some words." for i in range(60))
        text = f"# A\n\n## B\n\n### C\n\n{body}"
        chunks = split_markdown(text, max_chars=300)
        assert any(c.startswith(_context("A", "B", "C")) for c in chunks)

    def test_breadcrumb_pops_to_sibling_section(self) -> None:
        first = "\n\n".join(f"alpha line {i} of the first subsection." for i in range(40))
        second = "\n\n".join(f"beta line {i} of the second subsection." for i in range(40))
        text = f"# Doc\n\n## First\n\n{first}\n\n## Second\n\n{second}"
        chunks = split_markdown(text, max_chars=300)
        assert any(c.startswith(_context("Doc", "First")) for c in chunks)
        assert any(c.startswith(_context("Doc", "Second")) for c in chunks)
        # "First" must not leak into a "Second" breadcrumb.
        assert not any(c.startswith(_context("Doc", "First", "Second")) for c in chunks)


class TestTables:
    def test_headerless_listing_rows_kept_whole_no_duplication(self) -> None:
        # A blank-header listing table (the HN case): the first row is data, not a header,
        # so it must appear exactly once and never be propagated.
        rows = [f"| {i}. | Item number {i} | value {i} |" for i in range(200)]
        text = "|  |  |  |\n| --- | --- | --- |\n" + "\n".join(rows)
        chunks = split_markdown(text, max_chars=800)
        assert len(chunks) > 1
        assert sum("| 0. | Item number 0 |" in c for c in chunks) == 1
        # No chunk re-prepends the blank header as context (it's not a real header).
        assert not any(c.startswith("<context>") and "| 0. |" in c.split("</context>")[0] for c in chunks)
        joined = "\n".join(_strip_breadcrumbs(c) for c in chunks)
        for row in rows:
            assert row in joined

    def test_real_header_propagated_as_context_to_continuations(self) -> None:
        # A genuine <th> data table too long for one chunk: the header rides in the
        # <context> of every continuation chunk, and once inline in the first chunk.
        header = "| Rank | Country | Population |\n| --- | --- | --- |"
        rows = [f"| {i} | Country{i} | {i * 1000} |" for i in range(300)]
        text = header + "\n" + "\n".join(rows)
        chunks = split_markdown(text, max_chars=1000)
        assert len(chunks) > 2
        # First chunk renders the header inline (extractable once), no <context>.
        assert not chunks[0].startswith("<context>")
        assert "| Rank | Country | Population |" in chunks[0]
        # Every continuation chunk carries the header inside its <context> block.
        for c in chunks[1:]:
            assert c.startswith("<context>")
            ctx = c.split("</context>")[0]
            assert "| Rank | Country | Population |" in ctx
            assert "| --- | --- | --- |" in ctx
        assert all(len(c) <= 1000 for c in chunks)

    def test_table_rows_pack_toward_target_even_under_max(self) -> None:
        # One row = one entity: a real-header table that fits under max but exceeds target
        # is split by rows toward target, not kept whole.
        header = "| Rank | Country | Pop |\n| --- | --- | --- |"
        rows = [f"| {i} | Country{i} | {i * 1000} |" for i in range(60)]
        text = header + "\n" + "\n".join(rows)
        assert len(text) < 8000  # comfortably under max
        chunks = split_markdown(text, max_chars=8000, target=800)
        assert len(chunks) > 1
        for c in chunks[1:]:
            assert c.startswith("<context>") and "| Rank | Country | Pop |" in c.split("</context>")[0]

    def test_headerless_rows_pack_toward_target_and_drop_noise_header(self) -> None:
        rows = [f"| {i}. | Item {i} |" for i in range(100)]
        text = "|  |  |\n| --- | --- |\n" + "\n".join(rows)
        assert len(text) < 8000
        chunks = split_markdown(text, max_chars=8000, target=600)
        assert len(chunks) > 1  # rows packed toward target, not one whole block
        assert not any("| --- | --- |" in c for c in chunks)  # blank header + separator dropped
        assert sum("| 0. | Item 0 |" in c for c in chunks) == 1

    def test_real_header_table_carries_section_path_too(self) -> None:
        header = "| A | B |\n| --- | --- |"
        rows = [f"| {i} | {i} |" for i in range(300)]
        text = f"# Doc\n\n## Stats\n\n{header}\n" + "\n".join(rows)
        chunks = split_markdown(text, max_chars=600)
        cont = [c for c in chunks if c.startswith("<context>")]
        assert cont, "expected continuation chunks"
        # The <context> block names both the section and the table header.
        assert any(
            "Section: Doc > Stats" in c.split("</context>")[0] and "| A | B |" in c.split("</context>")[0] for c in cont
        )


class TestCodeFences:
    def test_hash_inside_code_block_is_not_a_heading(self) -> None:
        body = "\n\n".join(f"Following paragraph {i} with content." for i in range(60))
        text = "# Real Heading\n\n```python\n# not a heading\nx = 1\n```\n\n" + body
        chunks = split_markdown(text, max_chars=400)
        # The code comment must never be tracked as a section (no breadcrumb from it).
        assert not any(c.startswith(_context("Real Heading", "not a heading")) for c in chunks)
        assert not any(c.startswith(_context("not a heading")) for c in chunks)
        # The real heading is still tracked as the active section.
        assert any(c.startswith(_context("Real Heading")) for c in chunks)
