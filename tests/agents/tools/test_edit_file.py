from pathlib import Path
from typing import Any, cast

import pytest

from tabulaflow.agents.tools.filesystem.access import FilesystemRoot
from tabulaflow.agents.tools.filesystem.edit import EditFileTool


@pytest.fixture
def edit_file(tmp_path: Path) -> EditFileTool:
    return EditFileTool(str(tmp_path))


class TestWrite:
    async def test_create(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        out = await edit_file("write", "new.txt", "hello\n")
        assert "(error" not in out
        assert (tmp_path / "new.txt").read_text() == "hello\n"

    async def test_create_nested_dirs(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        await edit_file("write", "a/b/c.txt", "deep")
        assert (tmp_path / "a/b/c.txt").read_text() == "deep"

    async def test_overwrite(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("old")
        await edit_file("write", "f.txt", "new")
        assert (tmp_path / "f.txt").read_text() == "new"

    async def test_rejects_replace_parameters(self, edit_file: EditFileTool) -> None:
        old_text = await edit_file("write", "f.txt", "new", old_text="old")
        replace_all = await edit_file("write", "f.txt", "new", replace_all=True)
        assert "old_text is not valid" in old_text
        assert "replace_all is not valid" in replace_all


class TestReplace:
    async def test_unique_replace(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("a\nUNIQUE_TARGET\nc\n")
        out = await edit_file("replace", "f.txt", "REPLACED", old_text="UNIQUE_TARGET")
        assert "(error" not in out
        assert (tmp_path / "f.txt").read_text() == "a\nREPLACED\nc\n"

    async def test_requires_old_text(self, edit_file: EditFileTool) -> None:
        out = await edit_file("replace", "f.txt", "new")
        assert "old_text is required" in out

    async def test_not_found(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("hello\n")
        out = await edit_file("replace", "f.txt", "x", old_text="MISSING")
        assert "not found" in out
        assert (tmp_path / "f.txt").read_text() == "hello\n"

    async def test_exact_match_no_fuzzy_fallback(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("alpha beta\n")
        out = await edit_file("replace", "f.txt", "x", old_text="  alpha beta  ")
        assert "not found" in out
        assert (tmp_path / "f.txt").read_text() == "alpha beta\n"

    async def test_multiple_without_replace_all_errors(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("dup\ndup\ndup\n")
        out = await edit_file("replace", "f.txt", "x", old_text="dup")
        assert "3 times" in out
        assert (tmp_path / "f.txt").read_text() == "dup\ndup\ndup\n"

    async def test_replace_all(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("dup\ndup\ndup\n")
        out = await edit_file("replace", "f.txt", "x", old_text="dup", replace_all=True)
        assert "3 occurrences" in out
        assert (tmp_path / "f.txt").read_text() == "x\nx\nx\n"

    async def test_identical_old_new_errors(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("same\n")
        out = await edit_file("replace", "f.txt", "same", old_text="same")
        assert "identical" in out


class TestSafety:
    async def test_write_outside_rejected(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        out = await edit_file("write", "../escape.txt", "x")
        assert "(error" in out
        assert not (tmp_path.parent / "escape.txt").exists()

    async def test_read_only_root_rejects_write(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        data = tmp_path / "data"
        project.mkdir()
        data.mkdir()
        target = data / "source.csv"
        target.write_text("x\n")
        tool = EditFileTool(
            str(project),
            allowed_roots=[
                FilesystemRoot("project", project),
                FilesystemRoot("data", data, writable=False),
            ],
        )
        out = await tool("write", "../data/source.csv", "y\n")
        assert "read-only root 'data'" in out
        assert target.read_text() == "x\n"

    async def test_pdf_rejected(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4\n")
        out = await edit_file("write", "doc.pdf", "text")
        assert "PDF" in out

    async def test_binary_replace_rejected(self, edit_file: EditFileTool, tmp_path: Path) -> None:
        (tmp_path / "binary").write_bytes(b"\xff\xfe")
        out = await edit_file("replace", "binary", "x", old_text="y")
        assert "binary" in out

    async def test_unknown_command(self, edit_file: EditFileTool) -> None:
        out = await edit_file(cast(Any, "frobnicate"), "f.txt", "x")
        assert "unknown command" in out
