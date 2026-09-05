"""Safe conversion of media sources to Pydantic AI content."""

from __future__ import annotations

import io
import warnings
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic_ai.messages import BinaryContent
from pypdf import PdfReader, PdfWriter

from tabulaflow.core.media import detect_media, extract_media_bytes

_MODEL_IMAGE_TYPES = {"image/gif", "image/jpeg", "image/png", "image/webp"}
_CONVERTIBLE_IMAGE_TYPES = {"image/bmp", "image/tiff"}


@dataclass(frozen=True)
class PdfSelection:
    """A validated PDF containing a selected range of physical pages."""

    data: bytes
    first_page: int
    last_page: int
    total_pages: int


@dataclass(frozen=True)
class InlineMediaCandidate:
    """A binary-like value inspected without decoding its contents."""

    value: object
    declared_type: str | None
    estimated_size: int | None


@dataclass(frozen=True)
class InlineMediaItem:
    """One scalar item found in an inline media value or collection."""

    candidate: InlineMediaCandidate
    index: int | None = None


class UnrecognizedMediaError(ValueError):
    """Raised when an inline binary value has no identifiable media type."""


def _inspect_inline_media_item(value: object) -> InlineMediaCandidate | None:
    """Inspect an inline binary value without decoding a Data URI."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        size = value.nbytes if isinstance(value, memoryview) else len(value)
        return InlineMediaCandidate(value, None, size)

    if isinstance(value, dict) and "bytes" in value:
        raw = value.get("bytes")
        media_type = value.get("media_type") or value.get("mime_type")
        declared_type = media_type.split(";", 1)[0].strip().lower() if isinstance(media_type, str) else None
        if isinstance(raw, (bytes, bytearray, memoryview)):
            size = raw.nbytes if isinstance(raw, memoryview) else len(raw)
            return InlineMediaCandidate(value, declared_type, size)
        return InlineMediaCandidate(value, declared_type, None)

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped.startswith("data:"):
        return None
    header, marker, payload = stripped.partition(";base64,")
    declared_type = header[5:].split(";", 1)[0].strip().lower() or None
    if not marker:
        return InlineMediaCandidate(stripped, declared_type, None)
    compact = "".join(payload.split())
    padding = len(compact) - len(compact.rstrip("="))
    estimated_size = max(0, len(compact) * 3 // 4 - padding)
    return InlineMediaCandidate(stripped, declared_type, estimated_size)


def inspect_inline_media(value: object) -> tuple[InlineMediaItem, ...] | None:
    """Inspect a scalar media value or a top-level collection of media values.

    Collections may mix supported media representations and retain their source
    order. Arbitrary nested structures are intentionally not traversed.
    """
    candidate = _inspect_inline_media_item(value)
    if candidate is not None:
        return (InlineMediaItem(candidate),)

    values: Sequence[object]
    if isinstance(value, np.ndarray):
        if value.ndim != 1:
            return None
        values = value.tolist()
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        return None

    items: list[InlineMediaItem] = []
    non_media_indices: list[int] = []
    for index, item in enumerate(values):
        if item is None:
            continue
        item_candidate = _inspect_inline_media_item(item)
        if item_candidate is None:
            non_media_indices.append(index)
        else:
            items.append(InlineMediaItem(item_candidate, index))

    if not items:
        return None
    if non_media_indices:
        indices = ", ".join(str(index) for index in non_media_indices)
        raise ValueError(f"media collection contains non-media values at indices {indices}")
    return tuple(items)


def materialize_inline_media(candidate: InlineMediaCandidate, *, max_bytes: int) -> BinaryContent:
    """Convert a bounded inline candidate into a validated image or PDF."""
    if candidate.estimated_size is None:
        if isinstance(candidate.value, dict):
            path = candidate.value.get("path")
            if isinstance(path, str) and path:
                raise ValueError(
                    f"path-backed media {path!r} has no inline bytes; "
                    "download the referenced file and import its bytes before attaching it"
                )
            raise ValueError("inline media value has no usable bytes")
        if isinstance(candidate.value, str):
            raise ValueError("invalid inline media data URI")
        raise ValueError("inline media value has no usable bytes")
    if candidate.estimated_size > max_bytes:
        raise ValueError(f"{candidate.estimated_size} bytes exceeds {max_bytes}-byte limit")
    try:
        content = to_binary_content(candidate.value, media_type=candidate.declared_type)
    except ValueError as exc:
        if candidate.declared_type is None:
            raise UnrecognizedMediaError("media type could not be determined") from exc
        raise ValueError(f"invalid or unsupported {candidate.declared_type}") from exc
    if not (content.media_type.startswith("image/") or content.media_type == "application/pdf"):
        raise ValueError(f"invalid or unsupported {content.media_type}")
    if content.media_type == "application/pdf":
        try:
            select_pdf_pages(content.data)
        except ValueError as exc:
            raise ValueError(f"invalid or unsupported {content.media_type}") from exc
    if len(content.data) > max_bytes:
        raise ValueError(f"normalized {content.media_type} exceeds {max_bytes}-byte limit")
    return content


def select_pdf_pages(data: bytes, page_range: tuple[int, int] | None = None) -> PdfSelection:
    """Validate a PDF and optionally select a 1-indexed inclusive page range."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("encrypted PDFs are not supported")
        total = len(reader.pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid PDF") from exc
    if total == 0:
        raise ValueError("PDF has no pages")

    first, last = page_range or (1, total)
    if first < 1:
        raise ValueError(f"start must be >= 1, got {first}")
    if first > total:
        raise ValueError(f"start ({first}) is past the end (only {total} available)")
    last = min(last, total)
    if last < first:
        raise ValueError(f"end ({last}) must be >= start ({first})")
    if first == 1 and last == total:
        return PdfSelection(data, first, last, total)

    writer = PdfWriter()
    for page in reader.pages[first - 1 : last]:
        writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    return PdfSelection(output.getvalue(), first, last, total)


def to_binary_content(
    value: object,
    *,
    media_type: str | None = None,
    decode_base64: bool = False,
) -> BinaryContent:
    """Convert a binary-like value into validated Pydantic AI content."""
    data: bytes | None
    if isinstance(value, str) and value.startswith("data:"):
        try:
            parsed = BinaryContent.from_data_uri(value)
        except ValueError as exc:
            raise ValueError("value does not contain a valid media data URI") from exc
        data = parsed.data
        media_type = media_type or parsed.media_type
    else:
        data = extract_media_bytes(value, decode_base64=decode_base64)
    if data is None:
        raise ValueError("value does not contain media bytes")

    detected = detect_media(data)
    resolved_type = detected.media_type if detected is not None else media_type
    if resolved_type is None:
        raise ValueError("media type could not be determined")

    if resolved_type.startswith("image/"):
        data, resolved_type = _normalize_image(data, resolved_type)

    content = BinaryContent.narrow_type(BinaryContent(data=data, media_type=resolved_type))
    _validate_format(content)
    return content


def _validate_format(content: BinaryContent) -> None:
    try:
        _ = content.format
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported media type: {content.media_type}") from exc


def _normalize_image(data: bytes, media_type: str) -> tuple[bytes, str]:
    if media_type not in _MODEL_IMAGE_TYPES | _CONVERTIBLE_IMAGE_TYPES:
        raise ValueError(f"unsupported image type: {media_type}")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            if media_type in _CONVERTIBLE_IMAGE_TYPES:
                with Image.open(io.BytesIO(data)) as image:
                    output = io.BytesIO()
                    image.save(output, format="PNG")
                return output.getvalue(), "image/png"
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"invalid {media_type} image") from exc
    return data, media_type


__all__ = [
    "InlineMediaCandidate",
    "InlineMediaItem",
    "PdfSelection",
    "UnrecognizedMediaError",
    "inspect_inline_media",
    "materialize_inline_media",
    "select_pdf_pages",
    "to_binary_content",
]
