"""Interactive tabulaflow agent — the chat lib that frontends (app, webapp) build on.

The chat ⇄ frontend contract is: drive a ``ChatAgent``, and consume the events /
result it produces. All of it is re-exported here so frontends import from
``tabulaflow.chat`` rather than reaching into submodules.
"""

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
    ChatResult,
    ChatResultArtifact,
    ChatResultCard,
    ChatResultChart,
    ChatResultCombination,
    ChatResultGraph,
    ChatResultMap,
    ChatResultPanel,
    ChatResultPlaceholder,
    ChatResultTable,
    ChoiceControl,
    SelectionValue,
    SliderControl,
)

if TYPE_CHECKING:
    from tabulaflow.chat.agent import SYSTEM_PROMPT, ChatAgent


def __getattr__(name: str) -> object:
    # Lazy-load ``ChatAgent`` itself so importing event/result types doesn't build
    # an agent session. The event contract intentionally imports ToolCallOutcome
    # from toolhub, so this module is no longer a toolhub-free import path.
    # The agent itself loads the first time it's accessed (when a session opens,
    # off the UI thread).
    # ``SYSTEM_PROMPT`` (the baseline prompt callers extend via ``extra_instructions``)
    # lives in the same module, so it loads on the same terms.
    if name in ("ChatAgent", "SYSTEM_PROMPT"):
        from tabulaflow.chat import agent

        return getattr(agent, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChatAgent",
    "SYSTEM_PROMPT",
    "AnswerControl",
    "ChatResult",
    "ChatResultArtifact",
    "ChatResultCard",
    "ChatResultChart",
    "ChatResultCombination",
    "ChatResultGraph",
    "ChatResultTable",
    "ChatResultMap",
    "ChatResultPanel",
    "ChatResultPlaceholder",
    "ChoiceControl",
    "SelectionValue",
    "SliderControl",
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
