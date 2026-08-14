"""Tests for the structure-aware markdown splitter."""

from tabulaflow.agents.tools.engines.markdown_splitter import (
    DEFAULT_MAX_CHARS,
    DEFAULT_TARGET_CHARS,
    split_markdown,
)


class TestPassthrough:
    def test_blank_returns_empty(self) -> None:
        assert split_markdown("") == []
        assert split_markdown("   \n  ") == []

    def test_small_doc_returns_single_chunk_verbatim(self) -> None:
        text = "# Title\n\nA short paragraph."
        chunks = split_markdown(text, max_chars=1000)
        assert len(chunks) == 1
        assert chunks[0].body == text
        assert chunks[0].section == []
        assert chunks[0].table_header is None


class TestBudget:
    def test_no_chunk_body_exceeds_max_chars(self) -> None:
        # Many short paragraphs that must be packed under a tight budget.
        text = "\n\n".join(f"Paragraph number {i} with a little text." for i in range(200))
        chunks = split_markdown(text, max_chars=300)
        assert len(chunks) > 1
        assert all(len(c.body) <= 300 for c in chunks)

    def test_oversize_single_line_is_hard_split(self) -> None:
        # One line longer than the budget, no sentence breaks → hard char slices.
        text = "x" * 5000
        chunks = split_markdown(text, max_chars=1000)
        assert all(len(c.body) <= 1000 for c in chunks)
        assert "".join(c.body for c in chunks) == text


class TestTwoLimitPacking:
    def test_target_packs_many_small_entities_below_target(self) -> None:
        text = "\n\n".join(f"Entity number {i}." for i in range(200))
        chunks = split_markdown(text, max_chars=8000, target=500)
        assert len(chunks) > 1
        # Each chunk fills toward target, overshooting by at most the block that crossed it.
        assert all(len(c.body) <= 560 for c in chunks)

    def test_block_between_target_and_max_is_kept_whole(self) -> None:
        big = ("word " * 400).strip()  # ~2000 chars: above target, below max → never split
        text = f"alpha.\n\n{big}\n\nomega."
        chunks = split_markdown(text, max_chars=8000, target=500)
        assert any(big in c.body for c in chunks)  # present intact in a single chunk

    def test_heading_not_orphaned_before_oversize_body(self) -> None:
        # One oversize block (many newline-separated lines, no blank lines), as real prose
        # arrives. The heading rides with the first slice of its body via lazy fill.
        body = "\n".join(f"line {i} of the history body text here" for i in range(2000))
        text = f"## History\n\n{body}"
        chunks = split_markdown(text, max_chars=500)
        assert chunks[0].body.startswith("## History")
        assert len(chunks[0].body.strip()) > len("## History") + 20  # body rode along, not orphaned
        # And the section context is preserved as data on the continuation chunks.
        assert any(c.section == ["History"] for c in chunks)

    def test_long_line_wraps_on_word_boundaries(self) -> None:
        text = ("alpha bravo charlie delta echo foxtrot " * 60).strip()  # one long line, > max
        chunks = split_markdown(text, max_chars=200)
        # Reassembling on whitespace yields the exact source words → no mid-word cuts, no loss.
        assert " ".join(c.body for c in chunks).split() == text.split()

    def test_defaults_split_between_target_and_max(self) -> None:
        # A doc above DEFAULT_TARGET_CHARS but below DEFAULT_MAX_CHARS must still split
        # under the defaults — i.e. the soft target is active, not dormant.
        assert DEFAULT_TARGET_CHARS < DEFAULT_MAX_CHARS
        n = (DEFAULT_TARGET_CHARS * 2) // 40
        text = "\n\n".join(f"Paragraph {i} with a little filler body here." for i in range(n))
        assert DEFAULT_TARGET_CHARS < len(text) < DEFAULT_MAX_CHARS
        chunks = split_markdown(text)  # defaults
        assert len(chunks) > 1
        assert all(len(c.body) <= DEFAULT_MAX_CHARS for c in chunks)

    def test_list_item_with_nested_children_is_not_split(self) -> None:
        # A list entity is a non-indented line plus its indented sub-items (e.g. a flight
        # row with price/baggage/details bullets). Cuts must land between items, never
        # inside one, even when the whole list is one oversize block. Each flight's lines
        # carry a unique id so co-location is verifiable.
        item = (
            "- flight-{i} departs 7:50 AM arrives 9:25 PM Delta 1 stop\n"
            '  - button "carbon emissions for flight-{i}"\n'
            '  - button "baggage allowance for flight-{i}"\n'
            "  - price-{i} $309 per passenger\n"
            '  - button "details for flight-{i}"'
        )
        text = "\n".join(item.format(i=i) for i in range(80))
        chunks = split_markdown(text, max_chars=4000, target=1500)
        assert len(chunks) > 1
        for i in range(80):
            parent = f"- flight-{i} departs"
            home = next(c for c in chunks if parent in c.body)
            # the parent and ALL of this flight's children live in the same chunk
            assert f"price-{i} $309" in home.body
            assert f"details for flight-{i}" in home.body
            assert sum(parent in c.body for c in chunks) == 1

    def test_target_none_packs_to_max(self) -> None:
        text = "\n\n".join(f"Paragraph {i} with a little body text here." for i in range(300))
        chunks = split_markdown(text, max_chars=2000, target=None)
        assert all(len(c.body) <= 2000 for c in chunks)
        # Greedy-to-ceiling: most chunks should be reasonably full, not target-sized.
        assert max(len(c.body) for c in chunks) > 1500


class TestSectionContext:
    def test_continuation_chunks_carry_section_path(self) -> None:
        body = "\n\n".join(f"Sentence {i} in the history section." for i in range(100))
        text = f"# Python\n\n## History\n\n{body}"
        chunks = split_markdown(text, max_chars=400)
        # Continuation chunks (no inline heading of their own) name the section as data.
        continuation = [c for c in chunks if "## History" not in c.body and not c.body.startswith("# Python")]
        assert continuation, "expected at least one continuation chunk"
        assert all(c.section == ["Python", "History"] for c in continuation)

    def test_nested_heading_path(self) -> None:
        body = "\n\n".join(f"Detail line {i} goes here with some words." for i in range(60))
        text = f"# A\n\n## B\n\n### C\n\n{body}"
        chunks = split_markdown(text, max_chars=300)
        assert any(c.section == ["A", "B", "C"] for c in chunks)

    def test_heading_led_chunk_carries_ancestor_path(self) -> None:
        # A chunk that opens with an inline ### heading still names its h1>h2 ancestors,
        # without including the ### heading itself (it's inline content here).
        a_body = ("x " * 400).strip()  # fills the # Doc / ## A chunk so ### C starts fresh
        c_body = "\n\n".join(f"c line {i} of subsection body." for i in range(120))
        text = f"# Doc\n\n## A\n\n{a_body}\n\n### C\n\n{c_body}"
        chunks = split_markdown(text, max_chars=3000, target=600)
        c_lead = next(c for c in chunks if "### C" in c.body)
        assert c_lead.section == ["Doc", "A"]  # ancestors only — C is inline, not in section
        # Continuation chunks of C carry the full path including C.
        cont = [c for c in chunks if "### C" not in c.body and "c line" in c.body]
        assert cont and all(c.section == ["Doc", "A", "C"] for c in cont)

    def test_section_pops_to_sibling(self) -> None:
        first = "\n\n".join(f"alpha line {i} of the first subsection." for i in range(40))
        second = "\n\n".join(f"beta line {i} of the second subsection." for i in range(40))
        text = f"# Doc\n\n## First\n\n{first}\n\n## Second\n\n{second}"
        chunks = split_markdown(text, max_chars=300)
        assert any(c.section == ["Doc", "First"] for c in chunks)
        assert any(c.section == ["Doc", "Second"] for c in chunks)
        # "First" must not leak into a "Second" path.
        assert not any(c.section == ["Doc", "First", "Second"] for c in chunks)


class TestTables:
    def test_headerless_listing_rows_kept_whole_no_duplication(self) -> None:
        # A blank-header listing table (the HN case): the first row is data, not a header,
        # so it must appear exactly once and never be propagated.
        rows = [f"| {i}. | Item number {i} | value {i} |" for i in range(200)]
        text = "|  |  |  |\n| --- | --- | --- |\n" + "\n".join(rows)
        chunks = split_markdown(text, max_chars=800)
        assert len(chunks) > 1
        assert sum("| 0. | Item number 0 |" in c.body for c in chunks) == 1
        assert all(c.table_header is None for c in chunks)  # blank header → nothing propagated
        joined = "\n".join(c.body for c in chunks)
        for row in rows:
            assert row in joined

    def test_real_header_propagated_as_table_header_to_continuations(self) -> None:
        header = "| Rank | Country | Population |\n| --- | --- | --- |"
        rows = [f"| {i} | Country{i} | {i * 1000} |" for i in range(300)]
        text = header + "\n" + "\n".join(rows)
        chunks = split_markdown(text, max_chars=1000)
        assert len(chunks) > 2
        # First chunk renders the header inline (extractable once); no propagated header.
        assert chunks[0].table_header is None
        assert "| Rank | Country | Population |" in chunks[0].body
        # Every continuation chunk carries the header as data, not in the body.
        for c in chunks[1:]:
            assert c.table_header == header
            assert "| Rank | Country | Population |" not in c.body
        assert all(len(c.body) <= 1000 for c in chunks)

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
            assert c.table_header == header

    def test_headerless_rows_pack_toward_target_and_drop_noise_header(self) -> None:
        rows = [f"| {i}. | Item {i} |" for i in range(100)]
        text = "|  |  |\n| --- | --- |\n" + "\n".join(rows)
        assert len(text) < 8000
        chunks = split_markdown(text, max_chars=8000, target=600)
        assert len(chunks) > 1  # rows packed toward target, not one whole block
        assert all(c.table_header is None for c in chunks)
        assert not any("| --- | --- |" in c.body for c in chunks)  # blank header + separator dropped
        assert sum("| 0. | Item 0 |" in c.body for c in chunks) == 1

    def test_real_header_table_carries_section_and_header(self) -> None:
        header = "| A | B |\n| --- | --- |"
        rows = [f"| {i} | {i} |" for i in range(300)]
        text = f"# Doc\n\n## Stats\n\n{header}\n" + "\n".join(rows)
        chunks = split_markdown(text, max_chars=600)
        # A continuation chunk carries both the section path and the table header as data.
        assert any(c.section == ["Doc", "Stats"] and c.table_header == header for c in chunks)


class TestCodeFences:
    def test_hash_inside_code_block_is_not_a_heading(self) -> None:
        body = "\n\n".join(f"Following paragraph {i} with content." for i in range(60))
        text = "# Real Heading\n\n```python\n# not a heading\nx = 1\n```\n\n" + body
        chunks = split_markdown(text, max_chars=400)
        # The code comment must never be tracked as a section.
        assert not any("not a heading" in c.section for c in chunks)
        # The real heading is tracked as the active section on continuation chunks.
        assert any(c.section == ["Real Heading"] for c in chunks)
