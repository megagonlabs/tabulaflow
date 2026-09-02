"""Safe conversion of media sources to Pydantic AI content."""

from __future__ import annotations

import io
import warnings

from PIL import Image, UnidentifiedImageError
from pydantic_ai.messages import BinaryContent

from tabulaflow.core.media import detect_media, extract_media_bytes

_MAX_MEDIA_BYTES = 20 * 1024 * 1024
_MAX_IMAGE_PIXELS = 50_000_000

_MODEL_IMAGE_TYPES = {"image/gif", "image/jpeg", "image/png", "image/webp"}
_CONVERTIBLE_IMAGE_TYPES = {"image/bmp", "image/tiff"}


def to_binary_content(
    value: object,
    *,
    media_type: str | None = None,
    max_bytes: int = _MAX_MEDIA_BYTES,
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
    _check_size(len(data), max_bytes)

    detected = detect_media(data)
    resolved_type = detected.media_type if detected is not None else media_type
    if resolved_type is None:
        raise ValueError("media type could not be determined")

    if resolved_type.startswith("image/"):
        data, resolved_type = _normalize_image(data, resolved_type)
        _check_size(len(data), max_bytes)

    content = BinaryContent.narrow_type(BinaryContent(data=data, media_type=resolved_type))
    _validate_format(content)
    return content


def _check_size(size: int, max_bytes: int) -> None:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if size > max_bytes:
        raise ValueError(f"media is {size:,} bytes; maximum is {max_bytes:,} bytes")


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
                if image.width * image.height > _MAX_IMAGE_PIXELS:
                    raise ValueError(
                        f"image has {image.width * image.height:,} pixels; maximum is {_MAX_IMAGE_PIXELS:,}"
                    )
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
    "to_binary_content",
]
