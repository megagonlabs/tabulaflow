"""Safe conversion of media sources to Pydantic AI content."""

from __future__ import annotations

import io
import warnings
from dataclasses import dataclass

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
    "PdfSelection",
    "select_pdf_pages",
    "to_binary_content",
]
