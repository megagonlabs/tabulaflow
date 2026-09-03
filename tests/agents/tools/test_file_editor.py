"""Tests for the file editor tool (view / write_file / str_replace)."""

from pathlib import Path
from typing import Any, cast

from PIL import Image
import pytest
from pydantic_ai import ToolReturn
from pydantic_ai.messages import BinaryContent

from tabulaflow.agents.tools.filesystem.editor import FileEditorRoot, FileEditorTool


@pytest.fixture
def editor(tmp_path: Path) -> FileEditorTool:
    return FileEditorTool(str(tmp_path))


async def _view(
    editor: FileEditorTool,
    path: str = ".",
    *,
    view_range: list[int] | None = None,
) -> str:
    result = await editor("view", path, view_range=view_range)
    assert isinstance(result, str)
    return result


def _make_pdf(text: str) -> bytes:
    """Build a minimal valid single-page PDF with the given text in a content stream."""
    stream = f"BT /F1 24 Tf 20 100 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, body)
    xref_off = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref_off)
    return bytes(out)


class TestView:
    async def test_view_file(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("alpha\nbeta\ngamma\n")
        out = await _view(editor, "a.txt")
        assert "alpha" in out and "gamma" in out
        assert "(error" not in out

    async def test_view_range(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("L1\nL2\nL3\nL4\n")
        out = await _view(editor, "a.txt", view_range=[2, 3])
        assert "L2" in out and "L3" in out
        assert "L1" not in out and "L4" not in out

    async def test_view_directory(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "f.txt").write_text("x")
        out = await _view(editor, ".")
        assert "sub" in out and "f.txt" in out

    async def test_view_range_start_past_end_errors(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a\nb\nc\n")
        out = await _view(editor, "a.txt", view_range=[10, 20])
        assert "(error" in out and "past the end" in out

    async def test_view_range_end_clamped(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("L1\nL2\nL3\n")
        out = await _view(editor, "a.txt", view_range=[2, 999])  # end clamped to 3
        assert "(error" not in out
        assert "L2" in out and "L3" in out and "L1" not in out

    async def test_view_range_negative_end_errors(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("L1\nL2\nL3\n")
        out = await _view(editor, "a.txt", view_range=[2, -1])
        assert "(error" in out and "end (-1) must be >= start (2)" in out

    async def test_view_missing(self, editor: FileEditorTool) -> None:
        out = await _view(editor, "nope.txt")
        assert "(error" in out and "does not exist" in out

    async def test_view_binary_rejected(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "b.bin").write_bytes(b"\xff\xfe\x00\x01")
        out = await _view(editor, "b.bin")
        assert "(error" in out and "binary" in out

    async def test_view_image_returns_native_content(self, editor: FileEditorTool, tmp_path: Path) -> None:
        path = tmp_path / "image.bin"
        Image.new("RGB", (2, 3), "red").save(path, format="PNG")

        result = await editor("view", path.name)

        assert isinstance(result, ToolReturn)
        assert isinstance(result.return_value, str)
        assert result.return_value.startswith("Image: image.bin (image/png,")
        assert result.content is not None
        assert len(result.content) == 1
        image = result.content[0]
        assert isinstance(image, BinaryContent)
        assert image.media_type == "image/png"

    async def test_view_image_rejects_view_range(self, editor: FileEditorTool, tmp_path: Path) -> None:
        path = tmp_path / "image.png"
        Image.new("RGB", (2, 3), "red").save(path)

        result = await editor("view", path.name, view_range=[1, 1])

        assert isinstance(result, str)
        assert result == "(error: view_range is not supported for images.)"

    async def test_view_image_rejects_oversized_file(
        self,
        editor: FileEditorTool,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from tabulaflow.agents.tools.filesystem import editor as editor_module

        path = tmp_path / "image.png"
        Image.new("RGB", (2, 3), "red").save(path)
        monkeypatch.setattr(editor_module, "MAX_LOCAL_IMAGE_BYTES", 10)

        result = await editor("view", path.name)

        assert isinstance(result, str)
        assert "too large to read as an image" in result


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
        out = await _view(editor, "/etc/passwd")
        assert "(error" in out and "absolute" in out

    async def test_traversal_escape_rejected(self, editor: FileEditorTool) -> None:
        out = await _view(editor, "../../etc/passwd")
        assert "(error" in out and "outside the allowed roots" in out

    async def test_write_outside_rejected(self, editor: FileEditorTool, tmp_path: Path) -> None:
        out = await editor("write_file", "../escape.txt", file_text="x")
        assert "(error" in out
        assert not (tmp_path.parent / "escape.txt").exists()

    async def test_sibling_prefix_escape_rejected(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()
        sibling = tmp_path / "project_secret"
        sibling.mkdir()
        (sibling / "secret.txt").write_text("secret")

        tool = FileEditorTool(str(project))
        with pytest.raises(ValueError, match="outside the allowed roots"):
            await tool.execute("view", "../project_secret/secret.txt")


class TestAllowedRoots:
    async def test_additional_root_can_be_viewed_and_written(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        scratch = tmp_path / "scratch"
        project.mkdir()
        scratch.mkdir()
        (scratch / "existing.txt").write_text("old")
        tool = FileEditorTool(
            str(project),
            allowed_roots=[
                FileEditorRoot("project", project),
                FileEditorRoot("scratch", scratch),
            ],
        )

        view = await _view(tool, "../scratch/existing.txt")
        write = await tool("write_file", "../scratch/new.txt", file_text="new")

        assert "old" in view
        assert "(error" not in write
        assert (scratch / "new.txt").read_text() == "new"

    async def test_read_only_root_rejects_write(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        data = tmp_path / "data"
        project.mkdir()
        data.mkdir()
        (data / "source.csv").write_text("x\n")
        tool = FileEditorTool(
            str(project),
            allowed_roots=[
                FileEditorRoot("project", project),
                FileEditorRoot("data", data, writable=False),
            ],
        )

        view = await _view(tool, "../data/source.csv")
        write = await tool("write_file", "../data/source.csv", file_text="y\n")

        assert "x" in view
        assert "(error" in write and "read-only root 'data'" in write
        assert (data / "source.csv").read_text() == "x\n"

    async def test_unrestricted_allows_absolute_path(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        outside = tmp_path / "outside"
        project.mkdir()
        outside.mkdir()
        target = outside / "f.txt"
        target.write_text("outside")
        tool = FileEditorTool(str(project), allowed_roots=None)

        out = await _view(tool, str(target))

        assert "outside" in out

    async def test_unrestricted_relative_paths_still_use_working_dir(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()
        (project / "relative.txt").write_text("relative")
        tool = FileEditorTool(str(project), allowed_roots=None)

        out = await _view(tool, "relative.txt")

        assert "relative" in out


class TestPdf:
    async def test_view_pdf_extracts_text(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(_make_pdf("HELLO_PDF_TEST"))
        out = await _view(editor, "doc.pdf")
        assert "(error" not in out
        assert "PDF: doc.pdf" in out
        assert "--- Page 1 ---" in out
        assert "HELLO_PDF_TEST" in out

    async def test_view_pdf_detected_by_magic_bytes(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "doc.bin").write_bytes(_make_pdf("MAGIC_DETECTED"))
        out = await _view(editor, "doc.bin")
        assert "MAGIC_DETECTED" in out

    async def test_view_pdf_returns_full_text(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(_make_pdf("ONLY_PAGE"))
        out = await _view(editor, "doc.pdf")
        assert "(error" not in out
        assert "1 page(s) with text" in out and "ONLY_PAGE" in out

    async def test_view_pdf_view_range_rejected(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(_make_pdf("ONLY_PAGE"))
        out = await _view(editor, "doc.pdf", view_range=[1, 2])
        assert "(error" in out and "not supported for PDFs" in out

    async def test_write_pdf_rejected(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(_make_pdf("X"))
        out = await editor("write_file", "doc.pdf", file_text="hi")
        assert "(error" in out and "read-only" in out

    async def test_str_replace_pdf_rejected(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(_make_pdf("X"))
        out = await editor("str_replace", "doc.pdf", old_str="a", new_str="b")
        assert "(error" in out and "read-only" in out

    async def test_no_text_layer_notice(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "blank.pdf").write_bytes(_make_pdf(""))
        out = await _view(editor, "blank.pdf")
        assert "(error" in out and "no extractable text" in out

    async def test_malformed_pdf(self, editor: FileEditorTool, tmp_path: Path) -> None:
        (tmp_path / "bad.pdf").write_bytes(b"%PDF-1.4\nnot a real pdf")
        out = await _view(editor, "bad.pdf")
        assert "(error" in out

    async def test_pdf_view_stays_inline_without_storage(self, tmp_path: Path) -> None:
        from tabulaflow.agents.message_store import MessageStore

        tool = FileEditorTool(str(tmp_path), message_store=MessageStore().scoped("test"))
        (tmp_path / "doc.pdf").write_bytes(_make_pdf("OFFLOAD_ME"))
        out = await _view(tool, "doc.pdf")
        assert "message_id" not in out
        assert "OFFLOAD_ME" in out

    async def test_non_pdf_view_not_offloaded(self, tmp_path: Path) -> None:
        from tabulaflow.agents.message_store import MessageStore

        tool = FileEditorTool(str(tmp_path), message_store=MessageStore().scoped("test"))
        (tmp_path / "f.txt").write_text("plain text\n")
        out = await _view(tool, "f.txt")
        assert "message_id" not in out  # only PDFs are mirrored


class TestUnknownCommand:
    async def test_unknown_command(self, editor: FileEditorTool) -> None:
        out = await editor(cast(Any, "frobnicate"), "f.txt")
        assert isinstance(out, str)
        assert "(error" in out
