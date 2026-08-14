"""Interactive tabulaflow agent public API."""

from typing import TYPE_CHECKING

from tabulaflow.agents.chat.events import (
    AnswerDelta,
    ChatEvent,
    ChatResult,
    Finished,
    NarrationDelta,
    ThinkingDelta,
    ToolCallOutcome,
    ToolFinished,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)

if TYPE_CHECKING:
    from tabulaflow.agents.chat.session import SYSTEM_PROMPT, ChatSession


def __getattr__(name: str) -> object:
    if name in ("ChatSession", "SYSTEM_PROMPT"):
        from tabulaflow.agents.chat import session

        return getattr(session, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChatSession",
    "SYSTEM_PROMPT",
    "ChatResult",
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
