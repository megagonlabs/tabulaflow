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
from tabulaflow.chat.result import (
    ArtifactPlaceholder,
    ChatResult,
    ResolvedArtifact,
    ResolvedChartArtifact,
    ResolvedGraphArtifact,
    ResolvedMapArtifact,
    ResolvedTableArtifact,
    SelectionValue,
)

if TYPE_CHECKING:
    from tabulaflow.chat.agent import SYSTEM_PROMPT, ChatAgent
    from tabulaflow.chat.output_display_resolver import OutputDisplayResolver


def __getattr__(name: str) -> object:
    if name in ("ChatAgent", "SYSTEM_PROMPT"):
        from tabulaflow.chat import agent

        return getattr(agent, name)
    if name == "OutputDisplayResolver":
        from tabulaflow.chat.output_display_resolver import OutputDisplayResolver

        return OutputDisplayResolver
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChatAgent",
    "SYSTEM_PROMPT",
    "OutputDisplayResolver",
    "ArtifactPlaceholder",
    "ChatResult",
    "ResolvedArtifact",
    "ResolvedChartArtifact",
    "ResolvedGraphArtifact",
    "ResolvedMapArtifact",
    "ResolvedTableArtifact",
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
