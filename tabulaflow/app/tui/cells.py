"""Shared terminal cell-value interpretation."""

from __future__ import annotations

import json

from tabulaflow.core.media import detect_media, extract_media_items
from tabulaflow.output.formatting import summarize_binary_values


def normalize_cell_value(value: object) -> object:
    """Return a JSON-ready value with nested binary payloads summarized."""
    import numpy as np

    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, dict):
        return {key: normalize_cell_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_cell_value(item) for item in value]
    if isinstance(value, str):
        summarized = summarize_binary_values(value)
        if summarized != value:
            return summarized
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
        if isinstance(parsed, (dict, list)):
            return normalize_cell_value(parsed)
        return value
    return summarize_binary_values(value)


def format_media_cell(value: object) -> str | None:
    """Return a concise terminal summary for a recognized media cell."""
    media_items = extract_media_items(value, decode_plain_base64=True)
    if media_items is None:
        return None

    detected = [detect_media(blob) for blob in media_items]
    if len(media_items) == 1:
        item = detected[0]
        assert item is not None
        return f"<{item.media_type}: {len(media_items[0]):,} bytes>"

    counts: dict[str, int] = {}
    for item in detected:
        assert item is not None
        mime = item.media_type
        kind = "PDF" if mime == "application/pdf" else mime.split("/", 1)[0]
        counts[kind] = counts.get(kind, 0) + 1
    parts = []
    for kind, count in counts.items():
        label = f"PDF{'s' if count != 1 else ''}" if kind == "PDF" else f"{kind}{'s' if count != 1 else ''}"
        parts.append(f"{count} {label}")
    return f"<{len(media_items)} media items: {', '.join(parts)}>"


__all__ = ["format_media_cell", "normalize_cell_value"]
