"""Tests for the ref-aware browser-snapshot overflow snippet."""

import re

from tabulaflow.agents.tools.web_browser import (
    _SNIPPET_HEAD_CHARS,
    _SNIPPET_REF_BUDGET_CHARS,
    _SNIPPET_TAIL_CHARS,
    _clamp_to_ref,
    snapshot_snippet,
)

H, T, RB = _SNIPPET_HEAD_CHARS, _SNIPPET_TAIL_CHARS, _SNIPPET_REF_BUDGET_CHARS
MAX_SNIPPET = H + T + RB
_REF = re.compile(r"\[ref=e\d+\]")


def _page(middle: str) -> str:
    """A snapshot whose head/tail are pure prose and whose middle is ``middle``."""
    return "h" * H + "\n" + middle + "\n" + "t" * T


def _shown_total(snippet: str) -> tuple[int, int]:
    m = re.search(r"(\d+) of (\d+) interactive refs", snippet)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


class TestBudgetBound:
    def test_single_giant_ref_line_is_bounded(self) -> None:
        # A 2 MB single atom whose ref sits past the budget must not blow up the
        # snippet (regression: whole-line splice + unconditional first ref).
        giant = "[" + "x" * 2_000_000 + "](data:..) [ref=e1]"
        snip = snapshot_snippet("M1", _page(giant))
        assert len(snip) <= MAX_SNIPPET + 256  # + marker/blank-line overhead

    def test_many_atoms_on_one_line_is_bounded_and_clamped(self) -> None:
        one_line = " ".join(f"[paper {i}](u/{i}) [ref=e{i}]" for i in range(20_000))
        snip = snapshot_snippet("M2", _page(one_line))
        assert len(snip) <= MAX_SNIPPET + 256
        # The crammed line is clamped at a whole ref: no dangling ``[ref=e`` partials.
        assert snip.count("[ref=e") > 0
        assert snip.count("[ref=e") == len(_REF.findall(snip))

    def test_refs_after_an_unusable_giant_atom_are_recovered(self) -> None:
        # A leading giant atom (no ref within budget) must be skipped, not block
        # the small refs that follow.
        giant = "[" + "x" * 2_000_000 + "](data:..) [ref=e1]"
        small = "\n".join(f"[a](u) [ref=e{i}]" for i in range(2, 500))
        snip = snapshot_snippet("M3", _page(giant + "\n" + small))
        assert len(snip) <= MAX_SNIPPET + 256
        assert snip.count("[ref=e") > 100  # the trailing small refs came through


class TestSpliceCorrectness:
    def test_middle_refs_spliced_with_label(self) -> None:
        # Filler far from the ref; the heading is the ref's immediate label line.
        middle = "filler " * 5000 + "\n## Section\n[Buy](http://a) [ref=e10]"
        snip = snapshot_snippet("M4", _page(middle))
        assert "[ref=e10]" in snip
        assert "## Section" in snip  # immediate label line attached

    def test_no_refs_in_middle_yields_no_splice(self) -> None:
        snip = snapshot_snippet("M5", _page("prose " * 20_000))
        assert "[ref=e" not in snip
        assert snip.startswith("[message_id=M5]")
        assert snip.endswith("t" * T)

    def test_marker_counts_actual_refs_not_lines(self) -> None:
        # 50 atoms on one middle line -> the marker's total must count atoms.
        one_line = " ".join(f"[x](u) [ref=e{i}]" for i in range(50))
        big_gap = "z" * (H + T)  # force overflow so it truncates
        snip = snapshot_snippet("M6", _page(one_line + "\n" + big_gap))
        _, total = _shown_total(snip)
        assert total == 50


class TestClampToRef:
    def test_clamps_at_whole_ref(self) -> None:
        line = "[a](u) [ref=e1] [b](u) [ref=e2] [c](u) [ref=e3]"
        out = _clamp_to_ref(line, line.index("[ref=e2]") + len("[ref=e2]") + 1)
        assert out.endswith("[ref=e2]")
        assert "[ref=e3]" not in out

    def test_returns_empty_when_no_ref_fits(self) -> None:
        line = "[" + "x" * 5000 + "](u) [ref=e1]"
        assert _clamp_to_ref(line, 100) == ""

    def test_no_dangling_partial_ref(self) -> None:
        line = "[a](u) [ref=e1] [b](u) [ref=e2]"
        # Budget lands in the middle of the second ref marker.
        out = _clamp_to_ref(line, line.index("[ref=e2]") + 4)
        assert out.endswith("[ref=e1]")
