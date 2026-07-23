from __future__ import annotations

from pathlib import Path

import pytest

from tabulaflow.toolhub.apply_patch import ApplyPatchTool
from tabulaflow.toolhub.engines.patch_engine import ActionType, Commit, DiffError, process_patch


class FakeIO:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = dict(files)
        self.writes: list[tuple[str, str]] = []
        self.removes: list[str] = []

    def open(self, path: str) -> str:
        try:
            return self.files[path]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc

    def write(self, path: str, content: str) -> None:
        self.files[path] = content
        self.writes.append((path, content))

    def remove(self, path: str) -> None:
        try:
            del self.files[path]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc
        self.removes.append(path)

    def exists(self, path: str) -> bool:
        return path in self.files


def apply_patch_text(
    patch: str, files: dict[str, str], *, check_existing_adds: bool = False
) -> tuple[FakeIO, str, int, Commit]:
    io = FakeIO(files)
    exists_fn = io.exists if check_existing_adds else None
    message, fuzz, commit = process_patch(patch, io.open, io.write, io.remove, exists_fn)
    return io, message, fuzz, commit


def test_add_file() -> None:
    io, message, fuzz, commit = apply_patch_text(
        """*** Begin Patch
*** Add File: new.txt
+hello
+world
*** End Patch
""",
        {},
    )

    assert message == "Done!"
    assert fuzz == 0
    assert io.files["new.txt"] == "hello\nworld\n"
    assert commit.changes["new.txt"].type == ActionType.ADD


def test_update_file_with_bare_header() -> None:
    io, _, fuzz, commit = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
@@
 beta
-gamma
+delta
*** End Patch
""",
        {"a.txt": "alpha\nbeta\ngamma\n"},
    )

    assert fuzz == 0
    assert io.files["a.txt"] == "alpha\nbeta\ndelta\n"
    assert commit.changes["a.txt"].type == ActionType.UPDATE


def test_delete_file() -> None:
    io, _, _, commit = apply_patch_text(
        """*** Begin Patch
*** Delete File: stale.txt
*** End Patch
""",
        {"stale.txt": "old\n"},
    )

    assert "stale.txt" not in io.files
    assert io.removes == ["stale.txt"]
    assert commit.changes["stale.txt"].type == ActionType.DELETE


def test_move_to_file() -> None:
    io, _, _, commit = apply_patch_text(
        """*** Begin Patch
*** Update File: old.txt
*** Move to: new.txt
@@
-old name
+new name
*** End Patch
""",
        {"old.txt": "old name\n"},
    )

    assert "old.txt" not in io.files
    assert io.files["new.txt"] == "new name\n"
    assert io.writes == [("new.txt", "new name\n")]
    assert io.removes == ["old.txt"]
    assert commit.changes["old.txt"].move_path == "new.txt"


def test_multi_file_patch() -> None:
    io, _, _, commit = apply_patch_text(
        """*** Begin Patch
*** Add File: added.txt
+added
*** Update File: existing.txt
@@
-old
+new
*** End Patch
""",
        {"existing.txt": "old\n"},
    )

    assert io.files == {"added.txt": "added\n", "existing.txt": "new\n"}
    assert {path: change.type for path, change in commit.changes.items()} == {
        "added.txt": ActionType.ADD,
        "existing.txt": ActionType.UPDATE,
    }


def test_update_with_context_header() -> None:
    io, _, _, _ = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
@@ beta
-old
+new
*** End Patch
""",
        {"a.txt": "alpha\nbeta\nold\n"},
    )

    assert io.files["a.txt"] == "alpha\nbeta\nnew\n"


def test_update_first_chunk_without_header() -> None:
    io, _, _, _ = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
-old
+new
*** End Patch
""",
        {"a.txt": "old\n"},
    )

    assert io.files["a.txt"] == "new\n"


def test_pure_insert_with_context_header_is_anchored_not_eof() -> None:
    io, _, _, _ = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
@@ anchor
+inserted
*** End Patch
""",
        {"a.txt": "top\nanchor\nbottom\n"},
    )

    assert io.files["a.txt"] == "top\nanchor\ninserted\nbottom\n"


def test_trailing_whitespace_fuzzy_match_preserves_original_context() -> None:
    io, _, fuzz, _ = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
@@
 alpha
-old
+new
 omega
*** End Patch
""",
        {"a.txt": "alpha   \nold\nomega\n"},
    )

    assert fuzz > 0
    assert io.files["a.txt"] == "alpha   \nnew\nomega\n"


def test_indentation_fuzzy_match_preserves_original_context() -> None:
    io, _, fuzz, _ = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
@@
 alpha
-old
+new
 omega
*** End Patch
""",
        {"a.txt": "    alpha\n    old\n    omega\n"},
    )

    assert fuzz > 0
    assert io.files["a.txt"] == "    alpha\nnew\n    omega\n"


def test_unicode_fuzzy_match_preserves_original_context() -> None:
    io, _, fuzz, _ = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
@@
 title = "Hello-world"
-old
+new
*** End Patch
""",
        {
            "a.txt": 'title = "Hello-world"\nold\n'.replace('"', "\u201c", 1)
            .replace('"', "\u201d", 1)
            .replace("-", "\u2014")
        },
    )

    assert fuzz >= 1000
    assert io.files["a.txt"] == "title = \u201cHello\u2014world\u201d\nnew\n"


def test_strict_eof_context_matches_at_end_before_trailing_newline() -> None:
    io, _, fuzz, _ = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
@@
 end
+tail
*** End of File
*** End Patch
""",
        {"a.txt": "start\nend\n"},
    )

    assert fuzz == 0
    assert io.files["a.txt"] == "start\nend\ntail\n"


def test_strict_eof_context_away_from_eof_raises() -> None:
    io = FakeIO({"a.txt": "target\nmiddle\nend\n"})

    with pytest.raises(DiffError, match=r"Invalid EOF Context"):
        process_patch(
            """*** Begin Patch
*** Update File: a.txt
@@
 target
-middle
+MIDDLE
*** End of File
*** End Patch
""",
            io.open,
            io.write,
            io.remove,
        )

    assert io.files == {"a.txt": "target\nmiddle\nend\n"}
    assert io.writes == []


def test_empty_body_line_without_leading_space_is_empty_context_line() -> None:
    io, _, _, _ = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
@@

-old
+new
 after
*** End Patch
""",
        {"a.txt": "before\n\nold\nafter\n"},
    )

    assert io.files["a.txt"] == "before\n\nnew\nafter\n"


def test_bad_envelope_raises_diff_error() -> None:
    io = FakeIO({})

    with pytest.raises(DiffError, match=r"line 1: Invalid patch text"):
        process_patch("not a patch", io.open, io.write, io.remove)


def test_unknown_marker_line_raises_diff_error() -> None:
    io = FakeIO({})

    with pytest.raises(DiffError, match=r"Unknown Line"):
        process_patch(
            """*** Begin Patch
*** Nope: file.txt
*** End Patch
""",
            io.open,
            io.write,
            io.remove,
        )


def test_update_missing_file_raises_diff_error() -> None:
    io = FakeIO({})

    with pytest.raises(DiffError, match=r"Missing File: missing.txt"):
        process_patch(
            """*** Begin Patch
*** Update File: missing.txt
@@
-old
+new
*** End Patch
""",
            io.open,
            io.write,
            io.remove,
        )


def test_add_over_existing_raises_before_write() -> None:
    io = FakeIO({"a.txt": "old\n"})

    with pytest.raises(DiffError, match=r"File already exists: a.txt"):
        process_patch(
            """*** Begin Patch
*** Add File: a.txt
+new
*** End Patch
""",
            io.open,
            io.write,
            io.remove,
            io.exists,
        )

    assert io.files == {"a.txt": "old\n"}
    assert io.writes == []


def test_trailing_newline_is_normalized_on_add_and_update() -> None:
    io, _, _, _ = apply_patch_text(
        """*** Begin Patch
*** Add File: added.txt
+hello
+
*** Update File: existing.txt
-old
+new
*** End Patch
""",
        {"existing.txt": "old"},
    )

    assert io.files["added.txt"] == "hello\n"
    assert io.files["existing.txt"] == "new\n"


def test_semantic_error_is_atomic_before_writes() -> None:
    io = FakeIO({"first.txt": "one\n", "second.txt": "actual\n"})

    with pytest.raises(DiffError, match=r"Invalid Context"):
        process_patch(
            """*** Begin Patch
*** Update File: first.txt
@@
-one
+two
*** Update File: second.txt
@@
-missing
+new
*** End Patch
""",
            io.open,
            io.write,
            io.remove,
        )

    assert io.files == {"first.txt": "one\n", "second.txt": "actual\n"}
    assert io.writes == []


def test_duplicate_path_raises_diff_error() -> None:
    io = FakeIO({"a.txt": "one\n"})

    with pytest.raises(DiffError, match=r"Duplicate Path: a.txt"):
        process_patch(
            """*** Begin Patch
*** Update File: a.txt
@@
-one
+two
*** Update File: a.txt
@@
-two
+three
*** End Patch
""",
            io.open,
            io.write,
            io.remove,
        )


def test_context_not_found_raises_diff_error() -> None:
    io = FakeIO({"a.txt": "actual\n"})

    with pytest.raises(DiffError, match=r"Invalid Context"):
        process_patch(
            """*** Begin Patch
*** Update File: a.txt
@@
-missing
+new
*** End Patch
""",
            io.open,
            io.write,
            io.remove,
        )


class TestApplyPatchTool:
    async def test_tool_round_trip_and_result_format(self, tmp_path: Path) -> None:
        (tmp_path / "existing.txt").write_text("old\n")
        (tmp_path / "delete.txt").write_text("stale\n")
        tool = ApplyPatchTool(str(tmp_path))

        out = await tool(
            """*** Begin Patch
*** Update File: existing.txt
@@
-old
+new
*** Add File: added.txt
+added
*** Delete File: delete.txt
*** End Patch
"""
        )

        assert out.splitlines() == ["M existing.txt", "A added.txt", "D delete.txt"]
        assert (tmp_path / "existing.txt").read_text() == "new\n"
        assert (tmp_path / "added.txt").read_text() == "added\n"
        assert not (tmp_path / "delete.txt").exists()

    async def test_tool_reports_fuzzy_match(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("alpha   \nold\n")
        tool = ApplyPatchTool(str(tmp_path))

        out = await tool(
            """*** Begin Patch
*** Update File: a.txt
@@
 alpha
-old
+new
*** End Patch
"""
        )

        assert "M a.txt" in out
        assert "(fuzzy-matched, fuzz=" in out
        assert (tmp_path / "a.txt").read_text() == "alpha   \nnew\n"

    async def test_tool_rejects_relative_path_escape(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("outside\n")
        tool = ApplyPatchTool(str(project))

        out = await tool(
            """*** Begin Patch
*** Update File: ../outside.txt
@@
-outside
+edited
*** End Patch
"""
        )

        assert "(error:" in out and "outside the allowed roots" in out
        assert outside.read_text() == "outside\n"

    async def test_tool_rejects_absolute_path_outside_root(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("outside\n")
        tool = ApplyPatchTool(str(project))

        out = await tool(
            f"""*** Begin Patch
*** Update File: {outside}
@@
-outside
+edited
*** End Patch
"""
        )

        assert "(error:" in out and "outside the allowed roots" in out
        assert outside.read_text() == "outside\n"

    async def test_tool_unrestricted_allows_absolute_path(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("outside\n")
        tool = ApplyPatchTool(str(project), allowed_roots=None)

        out = await tool(
            f"""*** Begin Patch
*** Update File: {outside}
@@
-outside
+edited
*** End Patch
"""
        )

        assert out == f"M {outside}"
        assert outside.read_text() == "edited\n"

    async def test_tool_semantic_error_is_atomic(self, tmp_path: Path) -> None:
        (tmp_path / "first.txt").write_text("one\n")
        (tmp_path / "second.txt").write_text("actual\n")
        tool = ApplyPatchTool(str(tmp_path))

        out = await tool(
            """*** Begin Patch
*** Update File: first.txt
@@
-one
+two
*** Update File: second.txt
@@
-missing
+new
*** End Patch
"""
        )

        assert "(error:" in out and "Invalid Context" in out
        assert (tmp_path / "first.txt").read_text() == "one\n"
        assert (tmp_path / "second.txt").read_text() == "actual\n"

    async def test_tool_metrics_counts_calls_and_errors(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("old\n")
        tool = ApplyPatchTool(str(tmp_path))

        ok = await tool(
            """*** Begin Patch
*** Update File: a.txt
@@
-old
+new
*** End Patch
"""
        )
        err = await tool("not a patch")

        metrics = tool.metrics()
        assert ok == "M a.txt"
        assert "(error:" in err
        assert metrics.num_apply_patch == 2
        assert metrics.error_count == 1

    async def test_tool_creates_missing_parent_dirs_for_add_and_move(self, tmp_path: Path) -> None:
        (tmp_path / "old.txt").write_text("old\n")
        tool = ApplyPatchTool(str(tmp_path))

        out = await tool(
            """*** Begin Patch
*** Add File: nested/add/new.txt
+new file
*** Update File: old.txt
*** Move to: nested/move/moved.txt
@@
-old
+moved
*** End Patch
"""
        )

        assert out.splitlines() == ["A nested/add/new.txt", "M old.txt -> nested/move/moved.txt"]
        assert (tmp_path / "nested" / "add" / "new.txt").read_text() == "new file\n"
        assert (tmp_path / "nested" / "move" / "moved.txt").read_text() == "moved\n"
        assert not (tmp_path / "old.txt").exists()

    async def test_tool_add_over_existing_returns_error(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("old\n")
        tool = ApplyPatchTool(str(tmp_path))

        out = await tool(
            """*** Begin Patch
*** Add File: a.txt
+new
*** End Patch
"""
        )

        assert "(error:" in out and "File already exists: a.txt" in out
        assert (tmp_path / "a.txt").read_text() == "old\n"

    async def test_tool_rejects_pdf_paths(self, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_text("old\n")
        tool = ApplyPatchTool(str(tmp_path))

        out = await tool(
            """*** Begin Patch
*** Update File: doc.pdf
@@
-old
+new
*** End Patch
"""
        )

        assert "(error:" in out and "PDF" in out
        assert (tmp_path / "doc.pdf").read_text() == "old\n"
