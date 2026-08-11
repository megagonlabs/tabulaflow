"""Serializable chat-turn result models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from tabulaflow.core.outputs import OutputSpec
from tabulaflow.core.types import Usage


SelectionValue = str | int | float | bool


class ChatResult(BaseModel):
    """Logical result of one chat turn."""

    text: str
    output: OutputSpec = Field(default_factory=OutputSpec)
    usage: Usage | None = None
