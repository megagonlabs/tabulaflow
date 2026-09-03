import io

import pytest
from PIL import Image, ImageGrab
from pydantic_ai.messages import BinaryContent

from tabulaflow.app.tui import clipboard


def test_read_clipboard_image_returns_png_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ImageGrab, "grabclipboard", lambda: Image.new("RGB", (2, 3), "red"))

    content = clipboard.read_clipboard_image()

    assert isinstance(content, BinaryContent)
    assert content.media_type == "image/png"
    with Image.open(io.BytesIO(content.data)) as image:
        assert image.size == (2, 3)


def test_read_clipboard_image_returns_none_without_an_image(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ImageGrab, "grabclipboard", lambda: ["file.png"])

    assert clipboard.read_clipboard_image() is None
