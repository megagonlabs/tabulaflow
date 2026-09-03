"""Image clipboard access for the TUI."""

from __future__ import annotations

import io

from PIL import Image, ImageGrab
from pydantic_ai.messages import BinaryContent

from tabulaflow.agents.media import to_binary_content


def read_clipboard_image() -> BinaryContent | None:
    """Return the clipboard image as PNG content, or ``None`` when absent."""
    try:
        value = ImageGrab.grabclipboard()
    except (ChildProcessError, NotImplementedError, OSError):
        return None
    if not isinstance(value, Image.Image):
        return None

    try:
        output = io.BytesIO()
        value.save(output, format="PNG")
        return to_binary_content(output.getvalue())
    finally:
        value.close()


__all__ = ["read_clipboard_image"]
