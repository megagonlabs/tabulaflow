"""Provider-independent media detection and value extraction."""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedMedia:
    """A media type identified from a value's contents."""

    suffix: str
    media_type: str


def detect_media(data: bytes) -> DetectedMedia | None:
    """Identify a common media format from its file signature."""
    if len(data) < 4:
        return None
    head = data[:16]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return DetectedMedia(".png", "image/png")
    if head.startswith(b"\xff\xd8\xff"):
        return DetectedMedia(".jpg", "image/jpeg")
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return DetectedMedia(".gif", "image/gif")
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return DetectedMedia(".webp", "image/webp")
    if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
        return DetectedMedia(".wav", "audio/wav")
    if head.startswith(b"BM"):
        return DetectedMedia(".bmp", "image/bmp")
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return DetectedMedia(".tif", "image/tiff")
    if head.startswith(b"%PDF-"):
        return DetectedMedia(".pdf", "application/pdf")
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return DetectedMedia(".mp3", "audio/mpeg")
    if head.startswith(b"OggS"):
        return DetectedMedia(".ogg", "audio/ogg")
    if head.startswith(b"fLaC"):
        return DetectedMedia(".flac", "audio/flac")
    if head[4:8] == b"ftyp":
        return DetectedMedia(".mp4", "video/mp4")
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return DetectedMedia(".webm", "video/webm")
    head_lower = data[:256].lstrip().lower()
    if head_lower.startswith(b"<svg") or (head_lower.startswith(b"<?xml") and b"<svg" in head_lower):
        return DetectedMedia(".svg", "image/svg+xml")
    return None


_DATA_URI_RE = re.compile(r"^data:[^;,]+(?:;[^,]*)*;base64,(?P<payload>.*)$", re.DOTALL)
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/=\s]+$")
_BASE64_MIN_CHARS = 64


def extract_media_bytes(value: object, *, decode_base64: bool = False) -> bytes | None:
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

    match = _DATA_URI_RE.fullmatch(value.strip())
    if match is not None:
        return _decode_base64(match.group("payload"))
    if decode_base64 and len(value) >= _BASE64_MIN_CHARS and _BASE64_RE.fullmatch(value):
        return _decode_base64(value)
    return None


def _decode_base64(value: str) -> bytes | None:
    try:
        return base64.b64decode("".join(value.split()), validate=True)
    except (binascii.Error, ValueError):
        return None


__all__ = ["DetectedMedia", "detect_media", "extract_media_bytes"]
