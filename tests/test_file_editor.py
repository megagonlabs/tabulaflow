"""Tests for the file editor tool (view / write_file / str_replace)."""

from pathlib import Path

import pytest

from tabulaflow.toolhub.file_editor import FileEditorTool


@pytest.fixture
def editor(tmp_path: Path) -> FileEditorTool:
    return FileEditorTool(str(tmp_path))


class TestView:
    async def test_view_file(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("alpha\nbeta\ngamma\n")
        out = await editor("view", "a.txt")
        assert "alpha" in out and "gamma" in out
        assert "(error" not in out

    async def test_view_range(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("L1\nL2\nL3\nL4\n")
        out = await editor("view", "a.txt", view_range=[2, 3])
        assert "L2" in out and "L3" in out
        assert "L1" not in out and "L4" not in out

    async def test_view_directory(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "f.txt").write_text("x")
        out = await editor("view", ".")
        assert "sub" in out and "f.txt" in out

    async def test_view_missing(self, editor: FileEditorTool) -> None:
        out = await editor("view", "nope.txt")
        assert "(error" in out and "does not exist" in out

    async def test_view_binary_rejected(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "b.bin").write_bytes(b"\xff\xfe\x00\x01")
        out = await editor("view", "b.bin")
        assert "(error" in out and "binary" in out


class TestWriteFile:
    async def test_create(self, editor: FileEditorTool, tmp_path: Path) -> None:
        out = await editor("write_file", "new.txt", file_text="hello\n")
        assert "(error" not in out
        assert (tmp_path / "new.txt").read_text() == "hello\n"

    async def test_create_nested_dirs(self, editor: FileEditorTool, tmp_path: Path) -> None:
        await editor("write_file", "a/b/c.txt", file_text="deep")
        assert (tmp_path / "a" / "b" / "c.txt").read_text() == "deep"

    async def test_overwrite(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("old")
        await editor("write_file", "f.txt", file_text="new")
        assert (tmp_path / "f.txt").read_text() == "new"

    async def test_requires_file_text(self, editor: FileEditorTool) -> None:
        out = await editor("write_file", "f.txt")
        assert "(error" in out and "file_text" in out


class TestStrReplace:
    async def test_unique_replace(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("a\nUNIQUE_TARGET\nc\n")
        out = await editor("str_replace", "f.txt", old_str="UNIQUE_TARGET", new_str="REPLACED")
        assert "(error" not in out
        assert (tmp_path / "f.txt").read_text() == "a\nREPLACED\nc\n"

    async def test_not_found(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("hello\n")
        out = await editor("str_replace", "f.txt", old_str="MISSING", new_str="x")
        assert "(error" in out and "not found" in out
        assert (tmp_path / "f.txt").read_text() == "hello\n"

    async def test_exact_match_no_fuzzy_fallback(self, editor: FileEditorTool, tmp_path: Path) -> None:
        """An old_str padded with whitespace not present in the file must NOT
        fuzzy-match — it errors and leaves the file unchanged (regression for the
        removed strip-and-retry fallback, which would have silently edited)."""
        (tmp_path / "f.txt").write_text("alpha beta\n")
        out = await editor("str_replace", "f.txt", old_str="  alpha beta  ", new_str="x")
        assert "(error" in out and "not found" in out
        assert (tmp_path / "f.txt").read_text() == "alpha beta\n"

    async def test_multiple_without_replace_all_errors(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("dup\ndup\ndup\n")
        out = await editor("str_replace", "f.txt", old_str="dup", new_str="x")
        assert "(error" in out and "3 times" in out
        assert (tmp_path / "f.txt").read_text() == "dup\ndup\ndup\n"

    async def test_replace_all(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("dup\ndup\ndup\n")
        out = await editor("str_replace", "f.txt", old_str="dup", new_str="x", replace_all=True)
        assert "(error" not in out
        assert "3 occurrences" in out
        assert (tmp_path / "f.txt").read_text() == "x\nx\nx\n"

    async def test_identical_old_new_errors(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("same\n")
        out = await editor("str_replace", "f.txt", old_str="same", new_str="same")
        assert "(error" in out and "identical" in out


class TestPathSafety:
    async def test_absolute_path_rejected(self, editor: FileEditorTool) -> None:
        out = await editor("view", "/etc/passwd")
        assert "(error" in out and "absolute" in out

    async def test_traversal_escape_rejected(self, editor: FileEditorTool) -> None:
        out = await editor("view", "../../etc/passwd")
        assert "(error" in out and "escapes" in out

    async def test_write_outside_rejected(self, editor: FileEditorTool, tmp_path: Path) -> None:
        out = await editor("write_file", "../escape.txt", file_text="x")
        assert "(error" in out
        assert not (tmp_path.parent / "escape.txt").exists()


class TestUnknownCommand:
    async def test_unknown_command(self, editor: FileEditorTool) -> None:
        out = await editor("frobnicate", "f.txt")  # type: ignore[arg-type]
        assert "(error" in out
