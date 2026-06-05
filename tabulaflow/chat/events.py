"""The chat ⇄ frontend event contract.

``ChatAgent.run()`` yields a stream of these events; any frontend (the TUI, a
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

The stream is terminated by exactly one of ``Finished`` / ``Errored``.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias, Union

from pydantic import BaseModel, ConfigDict, Field

from tabulaflow.chat.result import ChatResult
from tabulaflow.core.types import Usage


# ---------------------------------------------------------------------------
# Tool outcomes — the structured ``ToolFinished`` payload.
# Tool-AGNOSTIC (keyed by outcome shape, not by tool): the consumer matches the
# outcome and renders / words it however it likes. Rendering is the frontend's
# job — there is deliberately no default summarizer here.
#
# Which tool produces which outcome (every chat tool maps to exactly one):
#   run_query                  -> RowsReturned (on success) | Failed (on error)
#   get_table_schema           -> ColumnsReturned
#   get_db_document            -> Completed
#   get_column_json_schema     -> Completed
#   render_chart               -> Completed
#   transfer_record            -> Completed
#   run_subagent_for_each_row  -> Completed
# Any tool not listed (or with no count to report) -> Completed. Adding a tool
# that returns rows/columns just reuses RowsReturned/ColumnsReturned — the union
# is keyed by outcome shape, so it stays closed as tools grow.
# ---------------------------------------------------------------------------


class _Outcome(BaseModel):
    model_config = ConfigDict(frozen=True)


class RowsReturned(_Outcome):
    kind: Literal["rows"] = "rows"
    count: int


class ColumnsReturned(_Outcome):
    kind: Literal["columns"] = "columns"
    count: int


class Failed(_Outcome):
    kind: Literal["error"] = "error"
    message: str | None = None


class Completed(_Outcome):
    """A tool finished with no count to report."""

    kind: Literal["ok"] = "ok"


ToolOutcome: TypeAlias = Annotated[
    Union[RowsReturned, ColumnsReturned, Failed, Completed], Field(discriminator="kind")
]


# ---------------------------------------------------------------------------
# Streaming events (emitted during a turn)
# ---------------------------------------------------------------------------


class _ChatEvent(BaseModel):
    """Base for all chat events (immutable)."""

    model_config = ConfigDict(frozen=True)


class TextDelta(_ChatEvent):
    """A chunk of the assistant's streaming natural-language answer."""

    kind: Literal["text_delta"] = "text_delta"
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
    the full result (if any) arrives later in ``Finished.result``."""

    kind: Literal["tool_finished"] = "tool_finished"
    tool_call_id: str
    name: str
    outcome: ToolOutcome


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
