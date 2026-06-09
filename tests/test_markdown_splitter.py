"""Tests for the structure-aware markdown splitter."""

from tabulaflow.toolhub.markdown_splitter import split_markdown


def _strip_breadcrumbs(chunk: str) -> str:
    """Drop a leading ``[Section: ...]`` prefix so chunk bodies can be compared."""
    if chunk.startswith("[Section:"):
        return chunk.split("\n\n", 1)[1] if "\n\n" in chunk else ""
    return chunk


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


class TestHeadingBreadcrumb:
    def test_continuation_chunks_carry_section_breadcrumb(self) -> None:
        body = "\n\n".join(f"Sentence {i} in the history section." for i in range(100))
        text = f"# Python\n\n## History\n\n{body}"
        chunks = split_markdown(text, max_chars=400)
        # The section spans several chunks; every chunk after the first that does not
        # itself begin with the heading must carry the breadcrumb.
        continuation = [c for c in chunks if not c.startswith("# Python") and "## History" not in c]
        assert continuation, "expected at least one continuation chunk"
        assert all(c.startswith("[Section: Python > History]") for c in continuation)

    def test_nested_heading_path(self) -> None:
        body = "\n\n".join(f"Detail line {i} goes here with some words." for i in range(60))
        text = f"# A\n\n## B\n\n### C\n\n{body}"
        chunks = split_markdown(text, max_chars=300)
        assert any(c.startswith("[Section: A > B > C]") for c in chunks)

    def test_breadcrumb_pops_to_sibling_section(self) -> None:
        first = "\n\n".join(f"alpha line {i} of the first subsection." for i in range(40))
        second = "\n\n".join(f"beta line {i} of the second subsection." for i in range(40))
        text = f"# Doc\n\n## First\n\n{first}\n\n## Second\n\n{second}"
        chunks = split_markdown(text, max_chars=300)
        assert any(c.startswith("[Section: Doc > First]") for c in chunks)
        assert any(c.startswith("[Section: Doc > Second]") for c in chunks)
        # "First" must not leak into a "Second" breadcrumb.
        assert not any(c.startswith("[Section: Doc > First > Second]") for c in chunks)


class TestTables:
    def test_rows_kept_whole_and_no_header_duplication(self) -> None:
        # A headerless listing table (the HN case): the first row is data, not a header,
        # and must appear exactly once across all chunks — never re-prepended.
        rows = [f"| {i}. | Item number {i} | value {i} |" for i in range(200)]
        text = "\n".join(rows)
        chunks = split_markdown(text, max_chars=800)
        assert len(chunks) > 1
        # The first row appears in exactly one chunk.
        assert sum("| 0. | Item number 0 |" in c for c in chunks) == 1
        # Every original row is present, and none is split mid-row.
        joined = "\n".join(_strip_breadcrumbs(c) for c in chunks)
        for row in rows:
            assert row in joined


class TestCodeFences:
    def test_hash_inside_code_block_is_not_a_heading(self) -> None:
        body = "\n\n".join(f"Following paragraph {i} with content." for i in range(60))
        text = "# Real Heading\n\n```python\n# not a heading\nx = 1\n```\n\n" + body
        chunks = split_markdown(text, max_chars=400)
        # The code comment must never be tracked as a section (no breadcrumb from it).
        assert not any(c.startswith("[Section: Real Heading > not a heading") for c in chunks)
        assert not any(c.startswith("[Section: not a heading") for c in chunks)
        # The real heading is still tracked as the active section.
        assert any(c.startswith("[Section: Real Heading]") for c in chunks)
