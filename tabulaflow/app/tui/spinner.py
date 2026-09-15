"""Shared spinner styling for the terminal UI."""

from __future__ import annotations

from rich.console import RenderableType
from rich.spinner import Spinner


def tool_arrow_spinner(text: RenderableType = "", *, style: str | None = None) -> Spinner:
    """Create the tool-arrow spinner selected for TUI activity states."""
    spinner = Spinner("dots", text=text, style=style)
    spinner.name = "toolArrow"
    spinner.frames = ["·", "›", "→", "›"]
    spinner.interval = 180
    return spinner
