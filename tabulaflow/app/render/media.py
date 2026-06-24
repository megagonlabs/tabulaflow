"""Cell and media serialization: magic-byte sniffing, base64 decode, value -> (content, suffix)."""

from __future__ import annotations

import ast
import base64
import binascii
import json
import re
import secrets
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Cell serialization
# ---------------------------------------------------------------------------

_SQL_RE = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|EXPLAIN)\b",
    re.IGNORECASE,
)
_PY_RE = re.compile(r"^\s*(def |class |import |from |if __name__)")


def serialize_cell(value: object) -> tuple[str | bytes, str]:
    """Return ``(content, suffix)`` for writing ``value`` at full fidelity.

    Binary inputs (``bytes``/``bytearray``/``memoryview``) get sniffed for
    a known media extension. String inputs that decode as base64 of a
    recognized media format are returned as the decoded bytes with that
    extension — covers DB columns that store images as base64 text.
    """
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        sniffed = sniff_binary(raw)
        return raw, sniffed[0] if sniffed else ".bin"

    # HuggingFace ``Image``/``Audio`` struct: ``{"bytes": <blob>, "path": ...}``
    # — DuckDB returns ``STRUCT(bytes BLOB, path VARCHAR)`` columns from
    # cached HF parquet as dicts. Surface the blob with its native
    # extension so ``b`` (open in browser) renders the image / plays the
    # audio rather than dumping a JSON tree.
    if isinstance(value, dict):
        inner = value.get("bytes")
        if isinstance(inner, (bytes, bytearray, memoryview)):
            raw = bytes(inner)
            sniffed = sniff_binary(raw)
            return raw, sniffed[0] if sniffed else ".bin"

    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False, default=str), ".json"

    if isinstance(value, str):
        decoded = try_decode_base64(value)
        if decoded is not None:
            sniffed = sniff_binary(decoded)
            if sniffed:
                return decoded, sniffed[0]
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(value)
            except Exception:
                continue
            if isinstance(parsed, (dict, list)):
                return (
                    json.dumps(parsed, indent=2, ensure_ascii=False, default=str),
                    ".json",
                )
        if _SQL_RE.match(value):
            return value, ".sql"
        if _PY_RE.match(value):
            return value, ".py"
        return value, ".txt"

    return str(value), ".txt"


def write_cell_dump(value: object, dumps_dir: Path) -> Path:
    """Serialize ``value`` and write it into ``dumps_dir``; return the path.

    File name is ``C_<6 hex>{suffix}``. Caller is responsible for
    deciding whether to reuse an existing dump.
    """
    content, suffix = serialize_cell(value)
    path = dumps_dir / f"C_{secrets.token_hex(3)}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (bytes, bytearray)):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path
