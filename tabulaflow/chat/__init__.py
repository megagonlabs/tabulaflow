"""Interactive tabulaflow agent — the chat lib that frontends (app, webapp) build on.

The chat ⇄ frontend contract is: drive a ``ChatAgent``, and consume the events /
result it produces. All of it is re-exported here so frontends import from
``tabulaflow.chat`` rather than reaching into submodules.
"""

from tabulaflow.chat.agent import ChatAgent
from tabulaflow.chat.events import (
    ChatEvent,
    ColumnsReturned,
    Completed,
    Failed,
    Finished,
    RowsReturned,
    TextDelta,
    ThinkingDelta,
    ToolFinished,
    ToolOutcome,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)
from tabulaflow.chat.result import ChatResult, ChatResultRecord

__all__ = [
    "ChatAgent",
    "ChatResult",
    "ChatResultRecord",
    "ChatEvent",
    "TextDelta",
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
