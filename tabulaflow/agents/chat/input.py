"""Multimodal chat input helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

from pydantic_ai.messages import BinaryContent

ChatInput: TypeAlias = str | Sequence[str | BinaryContent]


def describe_chat_input(value: ChatInput) -> str:
    """Render text and safe media descriptors without embedding media payloads."""
    if isinstance(value, str):
        return value
    return "\n".join(
        item
        if isinstance(item, str)
        else f"[{_media_label(item.media_type)}: {item.media_type}, {len(item.data):,} bytes]"
        for item in value
    )


def _media_label(media_type: str) -> str:
    category = media_type.partition("/")[0]
    return {"image": "Image", "audio": "Audio", "video": "Video"}.get(category, "Document")


__all__ = ["ChatInput"]
