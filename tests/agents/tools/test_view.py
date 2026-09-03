"""Tests for the filesystem viewer tool."""

import io
from pathlib import Path

from PIL import Image
import pytest
from pydantic_ai import ToolReturn
from pydantic_ai.messages import BinaryContent
from pypdf import PdfReader, PdfWriter

from tabulaflow.agents.tools.filesystem.access import FilesystemRoot
from tabulaflow.agents.tools.filesystem.view import ViewTool


@pytest.fixture
def view(tmp_path: Path) -> ViewTool:
    return ViewTool(str(tmp_path))


async def _view(
    view: ViewTool,
    path: str = ".",
    *,
    view_range: list[int] | None = None,
) -> str:
    result = await view(path, view_range=view_range)
    assert isinstance(result, str)
    return result


def _make_pdf(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=200)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _media_result(result: str | ToolReturn, media_type: str) -> tuple[str, BinaryContent]:
    assert isinstance(result, ToolReturn)
    assert isinstance(result.return_value, str)
    assert result.content is not None
    assert len(result.content) == 1
    content = result.content[0]
    assert isinstance(content, BinaryContent)
    assert content.media_type == media_type
    return result.return_value, content


class TestView:
    async def test_view_file(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("alpha\nbeta\ngamma\n")
        out = await _view(view, "a.txt")
        assert "alpha" in out and "gamma" in out
        assert "(error" not in out

    async def test_view_range(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("L1\nL2\nL3\nL4\n")
        out = await _view(view, "a.txt", view_range=[2, 3])
        assert "L2" in out and "L3" in out
        assert "L1" not in out and "L4" not in out

    async def test_view_directory(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "f.txt").write_text("x")
        out = await _view(view, ".")
        assert "sub" in out and "f.txt" in out

    async def test_view_range_start_past_end_errors(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a\nb\nc\n")
        out = await _view(view, "a.txt", view_range=[10, 20])
        assert "(error" in out and "past the end" in out

    async def test_view_range_end_clamped(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("L1\nL2\nL3\n")
        out = await _view(view, "a.txt", view_range=[2, 999])  # end clamped to 3
        assert "(error" not in out
        assert "L2" in out and "L3" in out and "L1" not in out

    async def test_view_range_negative_end_errors(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("L1\nL2\nL3\n")
        out = await _view(view, "a.txt", view_range=[2, -1])
        assert "(error" in out and "end (-1) must be >= start (2)" in out

    async def test_view_missing(self, view: ViewTool) -> None:
        out = await _view(view, "nope.txt")
        assert "(error" in out and "does not exist" in out

    async def test_view_binary_rejected(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "b.bin").write_bytes(b"\xff\xfe\x00\x01")
        out = await _view(view, "b.bin")
        assert "(error" in out and "binary" in out

    async def test_view_image_returns_native_content(self, view: ViewTool, tmp_path: Path) -> None:
        path = tmp_path / "image.bin"
        Image.new("RGB", (2, 3), "red").save(path, format="PNG")

        result = await view(path.name)

        description, _ = _media_result(result, "image/png")
        assert description.startswith("Image: image.bin (image/png,")

    async def test_content_detection_precedes_pdf_extension(self, view: ViewTool, tmp_path: Path) -> None:
        path = tmp_path / "image.pdf"
        Image.new("RGB", (2, 3), "red").save(path, format="PNG")

        result = await view(path.name)

        description, _ = _media_result(result, "image/png")
        assert description.startswith("Image: image.pdf (image/png,")

    async def test_pdf_extension_does_not_override_text_content(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "text.pdf").write_text("plain text")

        result = await _view(view, "text.pdf")

        assert "plain text" in result

    async def test_view_image_rejects_view_range(self, view: ViewTool, tmp_path: Path) -> None:
        path = tmp_path / "image.png"
        Image.new("RGB", (2, 3), "red").save(path)

        result = await view(path.name, view_range=[1, 1])

        assert isinstance(result, str)
        assert result == "(error: view_range is not supported for images.)"

    async def test_view_image_rejects_oversized_file(
        self,
        view: ViewTool,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from tabulaflow.agents.tools.filesystem import view as view_module

        path = tmp_path / "image.png"
        Image.new("RGB", (2, 3), "red").save(path)
        monkeypatch.setattr(view_module, "MAX_LOCAL_MEDIA_BYTES", 10)

        result = await view(path.name)

        assert isinstance(result, str)
        assert "too large to read as an image" in result


class TestPathSafety:
    async def test_absolute_path_rejected(self, view: ViewTool) -> None:
        out = await _view(view, "/etc/passwd")
        assert "(error" in out and "absolute" in out

    async def test_traversal_escape_rejected(self, view: ViewTool) -> None:
        out = await _view(view, "../../etc/passwd")
        assert "(error" in out and "outside the allowed roots" in out

    async def test_sibling_prefix_escape_rejected(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()
        sibling = tmp_path / "project_secret"
        sibling.mkdir()
        (sibling / "secret.txt").write_text("secret")

        tool = ViewTool(str(project))
        with pytest.raises(ValueError, match="outside the allowed roots"):
            await tool.execute("../project_secret/secret.txt")


class TestAllowedRoots:
    async def test_additional_root_can_be_viewed(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        scratch = tmp_path / "scratch"
        project.mkdir()
        scratch.mkdir()
        (scratch / "existing.txt").write_text("old")
        tool = ViewTool(
            str(project),
            allowed_roots=[
                FilesystemRoot("project", project),
                FilesystemRoot("scratch", scratch),
            ],
        )

        view = await _view(tool, "../scratch/existing.txt")
        assert "old" in view

    async def test_unrestricted_allows_absolute_path(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        outside = tmp_path / "outside"
        project.mkdir()
        outside.mkdir()
        target = outside / "f.txt"
        target.write_text("outside")
        tool = ViewTool(str(project), allowed_roots=None)

        out = await _view(tool, str(target))

        assert "outside" in out

    async def test_unrestricted_relative_paths_still_use_working_dir(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()
        (project / "relative.txt").write_text("relative")
        tool = ViewTool(str(project), allowed_roots=None)

        out = await _view(tool, "relative.txt")

        assert "relative" in out


class TestPdf:
    async def test_view_pdf_returns_native_content(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(_make_pdf(3))

        result = await view("doc.pdf")

        description, content = _media_result(result, "application/pdf")
        assert description.startswith("PDF: doc.pdf (3 pages, application/pdf,")
        assert len(PdfReader(io.BytesIO(content.data)).pages) == 3

    async def test_view_pdf_detected_by_magic_bytes(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "doc.bin").write_bytes(_make_pdf())

        result = await view("doc.bin")

        _media_result(result, "application/pdf")

    async def test_view_pdf_selects_page_range(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(_make_pdf(5))

        result = await view("doc.pdf", view_range=[2, 4])

        description, content = _media_result(result, "application/pdf")
        assert description.startswith("PDF: doc.pdf (pages 2-4 of 5, application/pdf,")
        assert len(PdfReader(io.BytesIO(content.data)).pages) == 3

    async def test_view_pdf_clamps_range_end(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(_make_pdf(3))

        result = await view("doc.pdf", view_range=[2, 99])

        description, _ = _media_result(result, "application/pdf")
        assert description.startswith("PDF: doc.pdf (pages 2-3 of 3, application/pdf,")

    async def test_view_pdf_rejects_invalid_range(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "doc.pdf").write_bytes(_make_pdf(3))

        past_end = await view("doc.pdf", view_range=[4, 5])
        reversed_range = await view("doc.pdf", view_range=[3, 2])

        assert isinstance(past_end, str) and "past the end" in past_end
        assert isinstance(reversed_range, str) and "must be >= start" in reversed_range

    async def test_malformed_pdf(self, view: ViewTool, tmp_path: Path) -> None:
        (tmp_path / "bad.pdf").write_bytes(b"%PDF-1.4\nnot a real pdf")

        result = await view("bad.pdf")

        assert isinstance(result, str)
        assert result == "(error: invalid PDF)"
