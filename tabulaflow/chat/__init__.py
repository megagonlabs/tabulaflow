"""Interactive tabulaflow agent — the chat lib that frontends (app, webapp) build on.

The chat ⇄ frontend contract is: drive a ``ChatAgent``, and consume the events /
result it produces. All of it is re-exported here so frontends import from
``tabulaflow.chat`` rather than reaching into submodules.
"""

from typing import TYPE_CHECKING

from tabulaflow.chat.events import (
    ChatEvent,
    ColumnsReturned,
    Completed,
    Failed,
    AnswerDelta,
    Finished,
    NarrationDelta,
    RowsReturned,
    ThinkingDelta,
    ToolFinished,
    ToolOutcome,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)
from tabulaflow.chat.result import ChatResult, ChatResultRecord

if TYPE_CHECKING:
    from tabulaflow.chat.agent import SYSTEM_PROMPT, ChatAgent


def __getattr__(name: str) -> object:
    # Lazy-load the heavy ``ChatAgent`` (which pulls in toolhub → sqlalchemy/duckdb +
    # pydantic-ai, ~3s) so that importing the lightweight event/result types — as the
    # TUI's widgets do — doesn't drag in the full agent stack. The agent itself loads
    # the first time it's accessed (when a session opens, off the UI thread).
    # ``SYSTEM_PROMPT`` (the baseline prompt callers extend via ``extra_instructions``)
    # lives in the same module, so it loads on the same terms.
    if name in ("ChatAgent", "SYSTEM_PROMPT"):
        from tabulaflow.chat import agent

        return getattr(agent, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChatAgent",
    "SYSTEM_PROMPT",
    "ChatResult",
    "ChatResultRecord",
    "ChatEvent",
    "AnswerDelta",
    "NarrationDelta",
    "ThinkingDelta",
    "ToolStarted",
    "ToolFinished",
    "ToolProgress",
    "UsageUpdated",
    "Finished",
    "ToolOutcome",
    "RowsReturned",
    "ColumnsReturned",
    "Failed",
    "Completed",
]
