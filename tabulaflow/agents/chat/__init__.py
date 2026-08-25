"""Interactive TabulaFlow agent public API."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.agents.chat.events import (
        AnswerDelta,
        ChatEvent,
        ChatResult,
        TurnFinished,
        NarrationDelta,
        ThinkingDelta,
        ToolCallOutcome,
        ToolFinished,
        ToolProgress,
        ToolStarted,
        UsageUpdated,
    )
    from tabulaflow.agents.chat.session import ChatSession

_LAZY_EXPORTS = {
    "AnswerDelta": ("tabulaflow.agents.chat.events", "AnswerDelta"),
    "ChatEvent": ("tabulaflow.agents.chat.events", "ChatEvent"),
    "ChatResult": ("tabulaflow.agents.chat.events", "ChatResult"),
    "ChatSession": ("tabulaflow.agents.chat.session", "ChatSession"),
    "TurnFinished": ("tabulaflow.agents.chat.events", "TurnFinished"),
    "NarrationDelta": ("tabulaflow.agents.chat.events", "NarrationDelta"),
    "ThinkingDelta": ("tabulaflow.agents.chat.events", "ThinkingDelta"),
    "ToolCallOutcome": ("tabulaflow.agents.chat.events", "ToolCallOutcome"),
    "ToolFinished": ("tabulaflow.agents.chat.events", "ToolFinished"),
    "ToolProgress": ("tabulaflow.agents.chat.events", "ToolProgress"),
    "ToolStarted": ("tabulaflow.agents.chat.events", "ToolStarted"),
    "UsageUpdated": ("tabulaflow.agents.chat.events", "UsageUpdated"),
}

__all__ = [
    "AnswerDelta",
    "ChatEvent",
    "ChatResult",
    "ChatSession",
    "TurnFinished",
    "NarrationDelta",
    "ThinkingDelta",
    "ToolCallOutcome",
    "ToolFinished",
    "ToolProgress",
    "ToolStarted",
    "UsageUpdated",
]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_EXPORTS})
