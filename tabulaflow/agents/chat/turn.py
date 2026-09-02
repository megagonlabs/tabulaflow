"""Turn-level adaptation from Pydantic AI events to the chat contract."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic_ai.messages import ModelMessage, ToolReturnPart

from tabulaflow.agents.chat.compaction import HOST_EVENT_METADATA_KEY
from tabulaflow.agents.chat.events import (
    AnswerDelta,
    ChatEvent,
    ChatResult,
    NarrationDelta,
    ThinkingDelta,
    ToolFinished,
    ToolStarted,
)
from tabulaflow.output.specs import (
    ArtifactSpec,
    OutputSpec,
    ParameterSpec,
    SourceSpec,
    TableArtifactSpec,
    artifact_source_ids,
)
from tabulaflow.output.store import OutputStore

if TYPE_CHECKING:
    from tabulaflow.agents.tools.show_artifacts import ArtifactBundle


async def _build_chat_result(
    answer_text: str,
    bundle: ArtifactBundle | None,
    output_store: OutputStore,
) -> ChatResult:
    output = _output_spec_from_bundle(bundle, output_store) if bundle is not None else OutputSpec()
    return ChatResult(
        text=_strip_answer_prefix(answer_text),
        output=output,
    )


def _output_spec_from_bundle(bundle: "ArtifactBundle", output_store: OutputStore) -> OutputSpec:
    sources: dict[str, SourceSpec] = {}
    artifacts: list[ArtifactSpec] = []
    parameters: dict[str, ParameterSpec] = {}

    def ensure_source(source_id: str) -> None:
        if source_id in sources:
            return
        if source_id.startswith("S"):
            sources[source_id] = output_store.get_source(source_id)
        else:
            raise KeyError(f"No source with id {source_id}")

    for ref in bundle.artifacts:
        artifact = _artifact_from_ref(ref.id, ref.label, output_store)
        if artifact is None:
            continue
        for source_id in artifact_source_ids(artifact):
            ensure_source(source_id)
        artifacts.append(artifact)

    for source in sources.values():
        for parameter in output_store.source_parameters(source.id):
            parameters.setdefault(parameter.id, parameter)

    return OutputSpec(parameters=list(parameters.values()), sources=list(sources.values()), artifacts=artifacts)


def _artifact_from_ref(ref_id: str, label: str | None, output_store: OutputStore) -> ArtifactSpec | None:
    if ref_id.startswith("CHART"):
        try:
            chart = output_store.get_artifact(ref_id)
        except (KeyError, ValueError):
            return None
        return chart.model_copy(update={"label": label})
    if ref_id.startswith("MAP"):
        try:
            stored_map = output_store.get_artifact(ref_id)
        except (KeyError, ValueError):
            return None
        return stored_map.model_copy(update={"label": label})
    if ref_id.startswith("GRAPH"):
        try:
            graph = output_store.get_artifact(ref_id)
        except (KeyError, ValueError):
            return None
        return graph.model_copy(update={"label": label})
    if ref_id.startswith("S"):
        try:
            output_store.get_source(ref_id)
        except (KeyError, ValueError):
            return None
        return TableArtifactSpec(id=ref_id, label=label, source_id=ref_id)
    return None


def _declared_bundle(completed_results: dict[str, ToolReturnPart]) -> "ArtifactBundle | None":
    """The bundle from the turn's last successful ``show_artifacts`` call, if any."""
    from tabulaflow.agents.tools.show_artifacts import ArtifactBundle, ShowArtifactsTool

    for part in reversed(list(completed_results.values())):
        if part.tool_name == ShowArtifactsTool.name and isinstance(part.metadata, ArtifactBundle):
            return part.metadata
    return None


def _patch_incomplete_messages(
    messages: list[ModelMessage],
    completed_results: dict[str, ToolReturnPart],
    *,
    interrupted: bool,
) -> list[ModelMessage]:
    """Make ``messages`` valid as ``message_history`` for the next agent run.

    A run that ends before completing — the user interrupts it, or it raises
    (an LLM API failure, a tool error) — leaves the trailing ``ModelResponse``
    with unanswered ``ToolCallPart``s, because pydantic-ai's ``CallToolsNode``
    only appends the aggregated tool-return ``ModelRequest`` once all tools
    finish. Every provider rejects a tool call with no matching result, so each
    pending call must be answered: with its real ``ToolReturnPart`` if the result
    event reached us before the break, otherwise a synthetic placeholder. A
    trailing system turn records why the run stopped. ``interrupted`` selects
    the wording (user cancel vs. error).
    """
    from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart, UserPromptPart

    cause = "was interrupted by the user" if interrupted else "failed with an error"

    out = list(messages)
    last = out[-1] if out else None
    pending = [p for p in last.parts if isinstance(p, ToolCallPart)] if isinstance(last, ModelResponse) else []

    if pending:
        out.append(
            ModelRequest(
                parts=[
                    completed_results.get(p.tool_call_id)
                    or ToolReturnPart(
                        tool_name=p.tool_name,
                        tool_call_id=p.tool_call_id,
                        content=(
                            f"[system: the run {cause} before this result was captured. "
                            "The tool may have completed first — any side effects "
                            "(e.g. writes) may or may not have taken effect.]"
                        ),
                    )
                    for p in pending
                ]
            )
        )
    out.append(
        ModelRequest(
            parts=[UserPromptPart(content=f"[system: the previous run {cause}.]")],
            metadata={HOST_EVENT_METADATA_KEY: True},
        )
    )
    return out


_ANSWER_PREFIX = "ANSWER:"


def _strip_answer_prefix(text: str) -> str:
    """Drop the leading answer prefix from a final answer."""
    stripped = text.lstrip()
    return stripped[len(_ANSWER_PREFIX) :].strip() if stripped.startswith(_ANSWER_PREFIX) else stripped


class _TextStreamRouter:
    """Routes a streamed text run into the final answer vs. mid-turn narration.

    A run opening with ``ANSWER:`` is the **answer**: held back only until that
    prefix is complete, then streamed without it. Any other run is **narration** and
    streams live. After the first chunk that yields text, :attr:`is_answer` says which
    it is. Reset via :meth:`reset` per text part.

    Kept here (not the frontend) so the prefix convention — owned by this agent's
    prompt — never crosses the layer boundary.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._raw = ""
        self._open = False  # True once text has begun streaming
        self.is_answer = False  # whether the opened run is the final answer

    def feed(self, chunk: str) -> str:
        """Accumulate ``chunk``; return its newly emittable text (``""`` until known).
        Once non-empty, :attr:`is_answer` is set for the run."""
        self._raw += chunk
        if self._open:
            return chunk

        stripped = self._raw.lstrip()
        if stripped.startswith(_ANSWER_PREFIX):
            answer = stripped[len(_ANSWER_PREFIX) :].lstrip("\n")
            if not answer:
                return ""  # prefix complete but the answer hasn't started yet
            self._open = True
            self.is_answer = True
            return answer
        if _ANSWER_PREFIX.startswith(stripped):
            return ""  # could still become the prefix
        if stripped:
            self._open = True
            self.is_answer = False
            return self._raw  # narration (or an answer the model failed to mark)
        return ""


# ---------------------------------------------------------------------------
# Stream event handlers
# ---------------------------------------------------------------------------


async def _emit_stream_event(
    event: object,
    emit: Callable[[ChatEvent], None],
    text_router: "_TextStreamRouter",
) -> None:
    """Map one pydantic-ai stream event to ``ChatEvent``s and emit them.

    Events carry structured data only: ``ToolStarted.args`` is the raw call args
    (a frontend renders them); ``ToolFinished.outcome`` is the typed
    ``ToolCallOutcome`` from the finished call's own return part, or ``None``
    for plain completion.

    Text and reasoning each arrive as a ``PartStartEvent`` (the first chunk — its
    content is non-empty on content-bearing streaming providers) followed by
    ``PartDeltaEvent``s. Both points must be handled or the first chunk is dropped.
    """
    from pydantic_ai.messages import (
        FunctionToolCallEvent,
        FunctionToolResultEvent,
        PartDeltaEvent,
        PartStartEvent,
        TextPart,
        TextPartDelta,
        ThinkingPart,
        ThinkingPartDelta,
        ToolReturnPart,
    )

    if isinstance(event, FunctionToolCallEvent):
        emit(
            ToolStarted(tool_call_id=event.tool_call_id, name=event.part.tool_name, args=_coerce_args(event.part.args))
        )

    elif isinstance(event, FunctionToolResultEvent):
        from tabulaflow.agents.tools.protocols import ToolCallOutcome

        tool_name = (event.part.tool_name if event.part is not None else "") or ""
        result_part = event.part if isinstance(event.part, ToolReturnPart) else None
        outcome = result_part.metadata if result_part is not None else None
        if not isinstance(outcome, ToolCallOutcome):
            outcome = None
        if outcome is None:
            content = result_part.content if result_part is not None else None
            if isinstance(content, str) and content.startswith("(error:"):
                outcome = ToolCallOutcome(error=True)
        emit(ToolFinished(tool_call_id=event.tool_call_id, name=tool_name, outcome=outcome))

    elif isinstance(event, PartStartEvent):
        part = event.part
        if isinstance(part, ThinkingPart) and part.content:
            emit(ThinkingDelta(content=part.content))
        elif isinstance(part, TextPart):
            text_router.reset()  # a new text part begins a fresh run
            visible = text_router.feed(part.content) if part.content else ""
            if visible:
                emit((AnswerDelta if text_router.is_answer else NarrationDelta)(content=visible))

    elif isinstance(event, PartDeltaEvent):
        delta = event.delta
        if isinstance(delta, ThinkingPartDelta) and delta.content_delta:
            emit(ThinkingDelta(content=delta.content_delta))
        elif isinstance(delta, TextPartDelta) and delta.content_delta:
            visible = text_router.feed(delta.content_delta)
            if visible:
                emit((AnswerDelta if text_router.is_answer else NarrationDelta)(content=visible))


def _coerce_args(args: object) -> dict[str, Any]:
    """Normalize a tool call's ``args`` (pydantic-ai gives a JSON string or dict) to a dict."""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, TypeError):
            return {}
    return args if isinstance(args, dict) else {}
