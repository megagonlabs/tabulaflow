import base64

import pytest

from tabulaflow.core.media import (
    Base64DataUri,
    MediaFormat,
    detect_media,
    extract_media_bytes,
    extract_media_items,
    parse_base64_data_uri,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.mark.parametrize(
    ("data", "suffix", "media_type"),
    [
        (PNG, ".png", "image/png"),
        (b"\xff\xd8\xff\xe0" + b"\x00" * 16, ".jpg", "image/jpeg"),
        (b"GIF89a" + b"\x00" * 16, ".gif", "image/gif"),
        (b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 8, ".webp", "image/webp"),
        (b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 8, ".wav", "audio/wav"),
        (b"BM" + b"\x00" * 30, ".bmp", "image/bmp"),
        (b"II*\x00" + b"\x00" * 28, ".tif", "image/tiff"),
        (b"MM\x00*" + b"\x00" * 28, ".tif", "image/tiff"),
        (b"%PDF-1.4\n" + b"\x00" * 16, ".pdf", "application/pdf"),
        (b"ID3\x03\x00" + b"\x00" * 16, ".mp3", "audio/mpeg"),
        (b"\xff\xfb\x90\x00" + b"\x00" * 16, ".mp3", "audio/mpeg"),
        (b"OggS" + b"\x00" * 16, ".ogg", "audio/ogg"),
        (b"fLaC" + b"\x00" * 16, ".flac", "audio/flac"),
        (b"\x00\x00\x00\x1cftypM4A \x00\x00\x02\x00", ".m4a", "audio/mp4"),
        (b"\x00\x00\x00 ftypisom" + b"\x00" * 16, ".mp4", "video/mp4"),
        (b"\x1a\x45\xdf\xa3" + b"\x00" * 16, ".webm", "video/webm"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", ".svg", "image/svg+xml"),
    ],
)
def test_detect_media(data: bytes, suffix: str, media_type: str) -> None:
    assert detect_media(data) == MediaFormat(suffix, media_type)


def test_detect_media_rejects_unknown_and_short_values() -> None:
    assert detect_media(b"\x00\x01\x02\x03\x04\x05") is None
    assert detect_media(b"\x89") is None


def test_extract_media_bytes_handles_binary_values_and_media_structs() -> None:
    assert extract_media_bytes(bytearray(PNG)) == PNG
    assert extract_media_bytes(memoryview(PNG)) == PNG
    assert extract_media_bytes({"bytes": PNG, "path": None}) == PNG
    assert extract_media_bytes({"path": "image.png"}) is None


def test_extract_media_bytes_decodes_data_uri() -> None:
    encoded = base64.b64encode(PNG).decode()

    assert extract_media_bytes(f"data:image/png;base64,{encoded}") == PNG


def test_plain_base64_requires_explicit_opt_in() -> None:
    encoded = base64.b64encode(PNG).decode()

    assert extract_media_bytes(encoded) is None
    assert extract_media_bytes(encoded, decode_plain_base64=True) == PNG


def test_extract_media_bytes_rejects_malformed_encoding() -> None:
    assert extract_media_bytes("data:image/png;base64,not-valid!") is None
    assert extract_media_bytes("not base64 at all !!! " * 5, decode_plain_base64=True) is None


def test_extract_media_items_handles_scalars_and_collections() -> None:
    pdf = b"%PDF-1.7\n" + b"\x00" * 16

    assert extract_media_items({"bytes": PNG, "path": None}) == (PNG,)
    assert extract_media_items([PNG, None, pdf]) == (PNG, pdf)


def test_extract_media_items_rejects_mixed_and_nested_collections() -> None:
    assert extract_media_items([PNG, "caption"]) is None
    assert extract_media_items([[PNG]]) is None


def test_parse_base64_data_uri_without_decoding() -> None:
    encoded = base64.b64encode(PNG).decode()

    assert parse_base64_data_uri(f"data:image/png;charset=utf-8;base64,{encoded}") == Base64DataUri(
        media_type="image/png",
        payload=encoded,
        decoded_size=len(PNG),
    )


@pytest.mark.parametrize(
    "value",
    [
        "not a data URI",
        "data:image/png,AAAA",
        "data:image/png;base64,not-valid!",
        "data:image/png;base64,AAA",
        "data:image/png;base64,AA=A",
    ],
)
def test_parse_base64_data_uri_rejects_invalid_values(value: str) -> None:
    assert parse_base64_data_uri(value) is None
