"""The chat ⇄ frontend event contract.

``ChatAgent.run()`` yields a stream of these events; any frontend (the TUI, a
future webapp, a CLI logger, a test harness) consumes the stream and decides how
to render each one. Events are **semantic** — they describe what the agent did,
never how to display it — so the same stream drives every frontend.

They're pydantic models forming a **discriminated union** on ``kind`` (consistent
with the rest of the data layer), which gives a frontend free, robust, two-way
wire (de)serialization:

    raw = event.model_dump_json()                       # produce (server)
    event = TypeAdapter(ChatEvent).validate_json(raw)    # consume (client)

The stream is terminated by exactly one of ``Finished`` / ``Errored``.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias, Union

from pydantic import BaseModel, ConfigDict, Field

from tabulaflow.chat.result import ChatResult
from tabulaflow.core.types import Usage


class _ChatEvent(BaseModel):
    """Base for all chat events (immutable)."""

    model_config = ConfigDict(frozen=True)


# ---------------------------------------------------------------------------
# Streaming events (emitted during a turn)
# ---------------------------------------------------------------------------


class TextDelta(_ChatEvent):
    """A chunk of the assistant's streaming natural-language answer."""

    kind: Literal["text_delta"] = "text_delta"
    content: str


class ToolStarted(_ChatEvent):
    """The agent invoked a tool."""

    kind: Literal["tool_started"] = "tool_started"
    tool_call_id: str
    name: str
    args_summary: str


class ToolFinished(_ChatEvent):
    """A tool call returned (``result_summary`` is a short human-readable outcome)."""

    kind: Literal["tool_finished"] = "tool_finished"
    tool_call_id: str
    name: str
    result_summary: str


class ToolProgress(_ChatEvent):
    """Progress within a long-running / fan-out tool (e.g. per-row subagents).

    ``tool_call_id`` identifies which in-flight tool when several run at once;
    ``None`` means "the current fan-out" for simple single-tool cases.
    """

    kind: Literal["tool_progress"] = "tool_progress"
    completed: int
    total: int
    stage: str | None = None
    tool_call_id: str | None = None


class StatusChanged(_ChatEvent):
    """A high-level status line for the frontend (e.g. 'thinking', 'querying')."""

    kind: Literal["status_changed"] = "status_changed"
    text: str


class UsageUpdated(_ChatEvent):
    """Cumulative token/cost usage so far this turn (for a live cost readout)."""

    kind: Literal["usage_updated"] = "usage_updated"
    usage: Usage


# ---------------------------------------------------------------------------
# Terminal events (exactly one ends the stream)
# ---------------------------------------------------------------------------


class Finished(_ChatEvent):
    """The turn completed; carries the full result. ``result.interrupted`` (if
    added) flags an early stop from a graceful (in-band) stop request."""

    kind: Literal["finished"] = "finished"
    result: ChatResult


class Errored(_ChatEvent):
    """The turn failed; carries a human-readable message. Emitted instead of
    propagating an exception so every frontend handles failure uniformly."""

    kind: Literal["errored"] = "errored"
    message: str


ChatEvent: TypeAlias = Annotated[
    Union[
        TextDelta,
        ToolStarted,
        ToolFinished,
        ToolProgress,
        StatusChanged,
        UsageUpdated,
        Finished,
        Errored,
    ],
    Field(discriminator="kind"),
]
