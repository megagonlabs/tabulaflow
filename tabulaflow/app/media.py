"""Media helpers for browser-pane table payloads and TUI cell inspection."""

from __future__ import annotations

import base64
import binascii
import re

# ---------------------------------------------------------------------------
# Magic-byte sniffing
# ---------------------------------------------------------------------------


def sniff_binary(raw: bytes) -> tuple[str, str] | None:
    """Return ``(suffix, mime)`` for recognized media signatures, else ``None``.

    Covers common image/audio/video/document formats observed in DB BLOB
    columns. Suffix includes the leading dot so callers can append it to
    file names directly.
    """
    if len(raw) < 4:
        return None
    head = bytes(raw[:16])
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif", "image/gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
        return ".wav", "audio/wav"
    if head.startswith(b"BM"):
        return ".bmp", "image/bmp"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tif", "image/tiff"
    if head.startswith(b"%PDF-"):
        return ".pdf", "application/pdf"
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return ".mp3", "audio/mpeg"
    if head.startswith(b"OggS"):
        return ".ogg", "audio/ogg"
    if head.startswith(b"fLaC"):
        return ".flac", "audio/flac"
    if head[4:8] == b"ftyp":
        return ".mp4", "video/mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm", "video/webm"
    # SVG is text-mode XML; peek at a slightly longer window
    head_lower = raw[:256].lstrip().lower()
    if head_lower.startswith(b"<svg") or (head_lower.startswith(b"<?xml") and b"<svg" in head_lower):
        return ".svg", "image/svg+xml"
    return None


# ---------------------------------------------------------------------------
# Base64 detection
# ---------------------------------------------------------------------------

_DATA_URI_RE = re.compile(r"^data:(?P<mime>[^;,]+)?(?:;[^,]*)*,(?P<payload>.*)$", re.DOTALL)
_BASE64_CHARS_RE = re.compile(r"^[A-Za-z0-9+/=\s]+$")
_BASE64_MIN_LEN = 64


def try_decode_base64(s: str) -> bytes | None:
    """Try to decode ``s`` as base64 (plain or ``data:...;base64,...`` URI).

    Returns the decoded bytes, or ``None`` if the input doesn't look like
    base64 or is shorter than ``_BASE64_MIN_LEN`` (guards against false
    positives on short strings that happen to be base64-alphabet).
    """
    if len(s) < _BASE64_MIN_LEN:
        return None
    payload = s.strip()
    m = _DATA_URI_RE.match(payload)
    if m:
        payload = m.group("payload")
    if not _BASE64_CHARS_RE.match(payload):
        return None
    try:
        return base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError):
        return None

