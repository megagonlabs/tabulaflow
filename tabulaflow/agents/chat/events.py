"""The chat ⇄ frontend event contract.

``ChatSession.run_stream()`` yields a stream of these events; any frontend (the TUI, a
future webapp, a CLI logger, a test harness) consumes the stream and decides how
to render each one. Events are **semantic** — they carry the data of what the
agent did, never pre-rendered presentation — so a frontend renders / words /
truncates however it wants. Rendering is deliberately the frontend's job; this
module ships no summarizers.

They're pydantic models forming a **discriminated union** on ``kind`` (consistent
with the rest of the data layer), which gives a frontend free, robust, two-way
wire (de)serialization:

    raw = event.model_dump_json()                       # produce (server)
    event = TypeAdapter(ChatEvent).validate_json(raw)    # consume (client)

The stream ends with exactly one ``TurnFinished`` (carrying the result) on normal
completion. Failures propagate as exceptions; an interrupted run raises
``CancelledError`` and the agent's message history / usage reflect the partial run.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias, Union

from pydantic import BaseModel, ConfigDict, Field

from tabulaflow.output.specs import OutputSpec
from tabulaflow.agents.trace import Usage
from tabulaflow.agents.tools.protocols import ToolCallOutcome as ToolCallOutcome


# ---------------------------------------------------------------------------
# Streaming events (emitted during a turn)
# ---------------------------------------------------------------------------


class _ChatEvent(BaseModel):
    """Base for all chat events (immutable)."""

    model_config = ConfigDict(frozen=True)


class AnswerDelta(_ChatEvent):
    """A chunk of the assistant's streaming final answer (the user-facing reply)."""

    kind: Literal["answer_delta"] = "answer_delta"
    content: str


class NarrationDelta(_ChatEvent):
    """A chunk of mid-turn narration — text the model emits while working, before its
    final answer. Distinct from ``AnswerDelta`` so a frontend can drop or dim it
    separately (the TUI drops it; a webapp might show it greyed)."""

    kind: Literal["narration_delta"] = "narration_delta"
    content: str


class ThinkingDelta(_ChatEvent):
    """A chunk of the model's reasoning summary (reasoning models only). Distinct
    from ``AnswerDelta`` so a frontend can show / collapse it separately from the answer."""

    kind: Literal["thinking_delta"] = "thinking_delta"
    content: str


class ToolStarted(_ChatEvent):
    """The agent invoked a tool. ``args`` is the raw tool-call arguments (lossless,
    so a frontend can show the full query / spec, or render its own compact line)."""

    kind: Literal["tool_started"] = "tool_started"
    tool_call_id: str
    name: str
    args: dict[str, Any]


class ToolFinished(_ChatEvent):
    """A tool call returned. ``outcome`` is structured so a frontend can reword it;
    ``None`` means plain completion with no suffix-worthy fact. The full result
    (if any) arrives later in ``TurnFinished.result``."""

    kind: Literal["tool_finished"] = "tool_finished"
    tool_call_id: str
    name: str
    outcome: ToolCallOutcome | None = None


class ToolProgress(_ChatEvent):
    """Progress within a long-running / fan-out tool (e.g. per-row subagents).

    ``tool_call_id`` identifies which in-flight tool when several run at once;
    ``None`` means "the current fan-out" for simple single-tool cases.
    """

    kind: Literal["tool_progress"] = "tool_progress"
    completed: int
    # ``None`` total means an open-ended running count with no known denominator
    # (e.g. entities extracted so far) — rendered as a bare count, not a fraction.
    total: int | None
    # Optional noun for the open-ended count, e.g. ``"rows"`` -> ``"47 rows"``.
    unit: str | None = None
    stage: str | None = None
    tool_call_id: str | None = None


class UsageUpdated(_ChatEvent):
    """Cumulative token/cost usage so far this turn (for a live cost readout)."""

    kind: Literal["usage_updated"] = "usage_updated"
    usage: Usage


# ---------------------------------------------------------------------------
# Terminal event (ends the stream on normal completion)
# ---------------------------------------------------------------------------


class ChatResult(BaseModel):
    """Logical result of one chat turn."""

    text: str
    output: OutputSpec = Field(default_factory=OutputSpec)
    usage: Usage | None = None


class TurnFinished(_ChatEvent):
    """The turn completed normally; carries the full result. The only terminal
    event — failures and interrupts surface as exceptions on the iterator, not here."""

    kind: Literal["turn_finished"] = "turn_finished"
    result: ChatResult


ChatEvent: TypeAlias = Annotated[
    Union[
        AnswerDelta,
        NarrationDelta,
        ThinkingDelta,
        ToolStarted,
        ToolFinished,
        ToolProgress,
        UsageUpdated,
        TurnFinished,
    ],
    Field(discriminator="kind"),
]
