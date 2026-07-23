from __future__ import annotations

import pytest

from tabulaflow.toolhub.apply_patch import ActionType, Commit, DiffError, process_patch


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


def apply_patch_text(patch: str, files: dict[str, str]) -> tuple[FakeIO, str, int, Commit]:
    io = FakeIO(files)
    message, fuzz, commit = process_patch(patch, io.open, io.write, io.remove)
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
    assert io.files["new.txt"] == "hello\nworld"
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

    assert io.files == {"added.txt": "added", "existing.txt": "new\n"}
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


def test_openhands_eof_fallback_matches_away_from_eof() -> None:
    io, _, fuzz, _ = apply_patch_text(
        """*** Begin Patch
*** Update File: a.txt
@@
 target
-middle
+MIDDLE
*** End of File
*** End Patch
""",
        {"a.txt": "target\nmiddle\nend\n"},
    )

    assert fuzz >= 10000
    assert io.files["a.txt"] == "target\nMIDDLE\nend\n"


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
