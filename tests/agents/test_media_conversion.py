import io
import base64

import pytest
import numpy as np
from PIL import Image
from pydantic_ai.messages import BinaryImage

from tabulaflow.agents.media import (
    UnsupportedModelMediaError,
    inspect_inline_media,
    materialize_inline_media,
    to_binary_content,
)


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
    with pytest.raises(UnsupportedModelMediaError, match="not supported as a model attachment"):
        to_binary_content(b"unknown", media_type="application/zip")


def test_to_binary_content_rejects_decompression_bombs(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _image_bytes("PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 4)

    with pytest.raises(ValueError, match="invalid image/png image"):
        to_binary_content(data)


def test_inspect_inline_media_supports_ordered_mixed_collections() -> None:
    image = _image_bytes("PNG")
    values = np.array(
        [
            {"bytes": image, "media_type": "image/png"},
            None,
            {"bytes": b"pdf", "media_type": "application/pdf"},
        ],
        dtype=object,
    )

    items = inspect_inline_media(values)

    assert items is not None
    assert [item.index for item in items] == [0, 2]
    assert [item.candidate.declared_type for item in items] == ["image/png", "application/pdf"]


def test_inspect_inline_media_rejects_partially_media_collections() -> None:
    with pytest.raises(ValueError, match="non-media values at indices 1"):
        inspect_inline_media([_image_bytes("PNG"), "caption"])


def test_materialize_inline_media_explains_path_backed_values() -> None:
    items = inspect_inline_media({"bytes": None, "path": "images/example.jpg"})
    assert items is not None

    with pytest.raises(
        ValueError,
        match="path-backed media 'images/example.jpg' has no inline bytes.*download the referenced file",
    ):
        materialize_inline_media(items[0].candidate, max_bytes=1024)


@pytest.mark.parametrize(
    "data",
    [
        b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 8,
        b"ID3\x03\x00" + b"\x00" * 16,
    ],
)
def test_materialize_inline_media_distinguishes_unsupported_audio(data: bytes) -> None:
    items = inspect_inline_media(data)
    assert items is not None

    with pytest.raises(UnsupportedModelMediaError, match="recognized audio/.+not supported as a model attachment"):
        materialize_inline_media(items[0].candidate, max_bytes=1024)
