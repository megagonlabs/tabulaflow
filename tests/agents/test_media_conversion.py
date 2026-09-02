import io
import base64

import pytest
from PIL import Image
from pydantic_ai.messages import BinaryImage

from tabulaflow.agents.media import to_binary_content


def _image_bytes(format: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 3), "red").save(output, format=format)
    return output.getvalue()


def test_to_binary_content_detects_images() -> None:
    data = _image_bytes("PNG")

    content = to_binary_content(data)

    assert isinstance(content, BinaryImage)
    assert content.data == data
    assert content.media_type == "image/png"


def test_to_binary_content_prefers_detected_type() -> None:
    content = to_binary_content(_image_bytes("PNG"), media_type="application/pdf")

    assert content.media_type == "image/png"


def test_to_binary_content_reads_data_uri_media_type() -> None:
    data = _image_bytes("PNG")
    encoded = base64.b64encode(data).decode()

    content = to_binary_content(f"data:image/png;base64,{encoded}")

    assert content.data == data
    assert content.media_type == "image/png"


@pytest.mark.parametrize("format", ["BMP", "TIFF"])
def test_to_binary_content_converts_supported_images_to_png(format: str) -> None:
    content = to_binary_content(_image_bytes(format))

    assert content.media_type == "image/png"
    assert content.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_to_binary_content_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="could not be determined"):
        to_binary_content(b"unknown")
    with pytest.raises(ValueError, match="unsupported media type"):
        to_binary_content(b"unknown", media_type="application/zip")


def test_to_binary_content_rejects_decompression_bombs(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _image_bytes("PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 4)

    with pytest.raises(ValueError, match="invalid image/png image"):
        to_binary_content(data)
