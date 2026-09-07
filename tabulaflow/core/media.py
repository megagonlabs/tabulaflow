"""Provider-independent media detection and value extraction."""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MediaFormat:
    """File format identified from media contents."""

    suffix: str
    media_type: str


@dataclass(frozen=True)
class Base64DataUri:
    """Parsed metadata and payload for a base64 data URI."""

    media_type: str
    payload: str
    decoded_size: int


def detect_media(data: bytes) -> MediaFormat | None:
    """Identify a common media format from its file signature."""
    if len(data) < 4:
        return None
    head = data[:16]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return MediaFormat(".png", "image/png")
    if head.startswith(b"\xff\xd8\xff"):
        return MediaFormat(".jpg", "image/jpeg")
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return MediaFormat(".gif", "image/gif")
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return MediaFormat(".webp", "image/webp")
    if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
        return MediaFormat(".wav", "audio/wav")
    if head.startswith(b"BM"):
        return MediaFormat(".bmp", "image/bmp")
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return MediaFormat(".tif", "image/tiff")
    if head.startswith(b"%PDF-"):
        return MediaFormat(".pdf", "application/pdf")
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return MediaFormat(".mp3", "audio/mpeg")
    if head.startswith(b"OggS"):
        return MediaFormat(".ogg", "audio/ogg")
    if head.startswith(b"fLaC"):
        return MediaFormat(".flac", "audio/flac")
    if head[4:8] == b"ftyp":
        return MediaFormat(".mp4", "video/mp4")
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return MediaFormat(".webm", "video/webm")
    head_lower = data[:256].lstrip().lower()
    if head_lower.startswith(b"<svg") or (head_lower.startswith(b"<?xml") and b"<svg" in head_lower):
        return MediaFormat(".svg", "image/svg+xml")
    return None


_DATA_URI_RE = re.compile(
    r"^data:(?P<media_type>[^;,]+)(?:;[^,]*)*;base64,(?P<payload>.*)$",
    re.DOTALL,
)
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]*={0,2}$")
_BASE64_MIN_CHARS = 64


def _parse_base64(value: str) -> tuple[str, int] | None:
    payload = "".join(value.split())
    if len(payload) % 4 or _BASE64_RE.fullmatch(payload) is None:
        return None
    padding = len(payload) - len(payload.rstrip("="))
    return payload, max(0, len(payload) * 3 // 4 - padding)


def parse_base64_data_uri(value: str) -> Base64DataUri | None:
    """Parse a syntactically valid base64 data URI without decoding it."""
    match = _DATA_URI_RE.fullmatch(value.strip())
    if match is None or (parsed := _parse_base64(match.group("payload"))) is None:
        return None
    payload, decoded_size = parsed
    return Base64DataUri(match.group("media_type").strip().lower(), payload, decoded_size)


def extract_media_bytes(value: object, *, decode_plain_base64: bool = False) -> bytes | None:
    """Extract bytes from a binary value, media struct, or encoded string."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, dict):
        data = value.get("bytes")
        if isinstance(data, (bytes, bytearray, memoryview)):
            return bytes(data)
        return None
    if not isinstance(value, str):
        return None

    if data_uri := parse_base64_data_uri(value):
        return _decode_base64(data_uri.payload)
    if decode_plain_base64 and len(value) >= _BASE64_MIN_CHARS and (parsed := _parse_base64(value)) is not None:
        return _decode_base64(parsed[0])
    return None


def extract_media_items(value: object, *, decode_plain_base64: bool = False) -> tuple[bytes, ...] | None:
    """Extract recognized media from one scalar or one-dimensional collection."""
    import numpy as np
    import pandas as pd

    if isinstance(value, np.ndarray):
        if value.ndim != 1:
            return None
        values = value.tolist()
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        blob = extract_media_bytes(value, decode_plain_base64=decode_plain_base64)
        if blob is None or detect_media(blob) is None:
            return None
        return (blob,)

    blobs: list[bytes] = []
    for item in values:
        try:
            if item is None or bool(pd.isna(item)):
                continue
        except (TypeError, ValueError):
            pass
        blob = extract_media_bytes(item, decode_plain_base64=decode_plain_base64)
        if blob is None or detect_media(blob) is None:
            return None
        blobs.append(blob)
    return tuple(blobs) or None


def _decode_base64(value: str) -> bytes | None:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None


__all__ = [
    "Base64DataUri",
    "MediaFormat",
    "detect_media",
    "extract_media_bytes",
    "extract_media_items",
    "parse_base64_data_uri",
]
