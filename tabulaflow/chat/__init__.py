"""Interactive tabulaflow agent public API."""

from typing import TYPE_CHECKING

from tabulaflow.chat.events import (
    AnswerDelta,
    ChatEvent,
    Finished,
    NarrationDelta,
    ThinkingDelta,
    ToolCallOutcome,
    ToolFinished,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)
from tabulaflow.chat.result import ChatResult, SelectionValue

if TYPE_CHECKING:
    from tabulaflow.chat.agent import SYSTEM_PROMPT, ChatAgent


def __getattr__(name: str) -> object:
    if name in ("ChatAgent", "SYSTEM_PROMPT"):
        from tabulaflow.chat import agent

        return getattr(agent, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChatAgent",
    "SYSTEM_PROMPT",
    "ChatResult",
    "SelectionValue",
    "ChatEvent",
    "AnswerDelta",
    "NarrationDelta",
    "ThinkingDelta",
    "ToolStarted",
    "ToolFinished",
    "ToolProgress",
    "UsageUpdated",
    "Finished",
    "ToolCallOutcome",
]
