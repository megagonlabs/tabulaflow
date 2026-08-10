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
    AnswerControl,
    AnswerPanel,
    ArtifactPlaceholder,
    ChatResult,
    ChoiceControl,
    ControlChoice,
    ResolvedArtifact,
    ResolvedChartArtifact,
    ResolvedGraphArtifact,
    ResolvedMapArtifact,
    ResolvedTableArtifact,
    SelectionValue,
    SliderControl,
)
from tabulaflow.core.legacy_outputs import (
    ArtifactDef,
    ChartArtifactDef,
    GraphArtifactDef,
    MapArtifactDef,
    TableArtifactDef,
)

if TYPE_CHECKING:
    from tabulaflow.chat.agent import SYSTEM_PROMPT, ChatAgent
    from tabulaflow.chat.artifact_resolver import ArtifactResolver


def __getattr__(name: str) -> object:
    if name in ("ChatAgent", "SYSTEM_PROMPT"):
        from tabulaflow.chat import agent

        return getattr(agent, name)
    if name == "ArtifactResolver":
        from tabulaflow.chat.artifact_resolver import ArtifactResolver

        return ArtifactResolver
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChatAgent",
    "SYSTEM_PROMPT",
    "ArtifactResolver",
    "AnswerControl",
    "AnswerPanel",
    "ArtifactDef",
    "ArtifactPlaceholder",
    "ChartArtifactDef",
    "ChatResult",
    "ChoiceControl",
    "ControlChoice",
    "GraphArtifactDef",
    "MapArtifactDef",
    "ResolvedArtifact",
    "ResolvedChartArtifact",
    "ResolvedGraphArtifact",
    "ResolvedMapArtifact",
    "ResolvedTableArtifact",
    "SelectionValue",
    "SliderControl",
    "TableArtifactDef",
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
