"""Interactive tabulaflow agent — the chat lib that frontends (app, webapp) build on.

The chat ⇄ frontend contract is: drive a ``ChatAgent``, and consume the events /
result it produces. All of it is re-exported here so frontends import from
``tabulaflow.chat`` rather than reaching into submodules.
"""

from tabulaflow.chat.agent import ChatAgent, ProgressSink
from tabulaflow.chat.events import (
    ChatEvent,
    Errored,
    Finished,
    StatusChanged,
    TextDelta,
    ToolFinished,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)
from tabulaflow.chat.result import ChatResult, ChatResultRecord

__all__ = [
    "ChatAgent",
    "ProgressSink",
    "ChatResult",
    "ChatResultRecord",
    "ChatEvent",
    "TextDelta",
    "ToolStarted",
    "ToolFinished",
    "ToolProgress",
    "StatusChanged",
    "UsageUpdated",
    "Finished",
    "Errored",
]
