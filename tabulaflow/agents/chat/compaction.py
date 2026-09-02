"""Simple, provider-agnostic checkpoint compaction for interactive chat sessions.

Rather than combining multiple trimming strategies or sending a flattened transcript
to a separate summarizer, the current agent writes one checkpoint from its native
conversation. This preserves recent tool context, keeps provider-carried reasoning
state available, reuses the existing prompt prefix for the checkpoint request, and
avoids a second model configuration.

The remaining rewrite is deterministic: split history into user turns, reduce old
turns to bounded dialogue, replace recent tool-result payloads, append the checkpoint,
and remove oldest whole turns until the target is met. This single policy is easier to
understand than a tiered strategy pipeline, while whole-turn eviction preserves tool
pairing and makes the resulting context predictable across providers.

The checkpoint and latest user request are never silently truncated. If those alone
cannot fit, compaction fails explicitly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import genai_prices
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)


_CHARS_PER_TOKEN = 4
_OLD_MESSAGE_TOKENS = 100
_CONTEXT_RESERVE_TOKENS = 32_000
_CHECKPOINT_TOKEN_LIMIT = 4_000
_TRUNCATION_MARKER = "\n[... older message truncated ...]\n"
_TOOL_RESULT_PLACEHOLDER = "[tool result omitted after execution during context compaction]"
# Marks synthetic checkpoint messages so a later compaction replaces, rather than
# summarizes and retains, the previous checkpoint exchange.
_CHECKPOINT_METADATA = "tabulaflow.context-checkpoint"
# Host notifications use UserPromptPart for model visibility, but are not user turns.
HOST_EVENT_METADATA_KEY = "tabulaflow.host-event"
_CHECKPOINT_PROMPT = (
    "Create a compact, self-contained checkpoint that will replace the earlier "
    "conversation. Preserve everything needed to continue correctly, including "
    "goals, constraints, decisions, important exact details, current state, and "
    "next steps. Omit filler, superseded information, and raw execution traces."
    "\n\n"
    "Do not use tools unless needed to retrieve referenced content, and do not "
    "change external state. Write at most approximately {checkpoint_tokens:,} "
    "tokens. Return only the checkpoint."
)


@dataclass(frozen=True)
class CompactionConfig:
    """User-facing controls for automatic conversation compaction.

    ``trigger_tokens`` starts checkpointing, ``target_tokens`` bounds the rewritten
    history, and ``keep_recent_turns`` controls how many newest turns initially retain
    their tool-call structure. Hard eviction may retain fewer turns to meet the target.
    """

    trigger_tokens: int = 240_000
    target_tokens: int = 32_000
    keep_recent_turns: int = 10

    def __post_init__(self) -> None:
        if not 0 < self.target_tokens < self.trigger_tokens:
            raise ValueError("expected 0 < target_tokens < trigger_tokens")
        if self.keep_recent_turns < 0:
            raise ValueError("keep_recent_turns must be non-negative")


def checkpoint_prompt(config: CompactionConfig) -> str:
    """Return the internal request, deriving its size from the context target."""
    return _CHECKPOINT_PROMPT.format(checkpoint_tokens=min(_CHECKPOINT_TOKEN_LIMIT, config.target_tokens // 4)).strip()


def effective_trigger_tokens(config: CompactionConfig, model: str) -> int:
    """Return the configured trigger with room reserved in the model window.

    Unknown models use the configured absolute trigger. Known smaller models compact
    earlier so the checkpoint request and response still fit.
    """
    context_window = _context_window(model)
    if context_window is None:
        return config.trigger_tokens
    return min(config.trigger_tokens, max(1, context_window - _CONTEXT_RESERVE_TOKENS))


def estimate_context_tokens(messages: list[ModelMessage], additional_text: str = "") -> int:
    """Estimate a prospective request from its latest provider-usage anchor.

    The latest uncompacted response's provider-reported input plus output usage is
    ground truth for history through that response. Only later messages and pending
    text use the four-characters-per-token estimate. A checkpoint is a rewrite
    boundary, so estimates after one start from the compacted messages instead of an
    obsolete pre-compaction usage anchor.
    """
    additional = _estimate_text_tokens(additional_text)
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, ModelResponse):
            continue
        if message.metadata and message.metadata.get(_CHECKPOINT_METADATA):
            break
        anchored = message.usage.input_tokens + message.usage.output_tokens
        if anchored:
            return anchored + _estimate_messages_tokens(messages[index + 1 :]) + additional
    return _estimate_messages_tokens(messages) + additional


def compact_history(
    messages: list[ModelMessage],
    *,
    checkpoint_request: str,
    checkpoint_text: str,
    config: CompactionConfig,
) -> list[ModelMessage]:
    """Return provider-valid history bounded by ``config.target_tokens``.

    Old turns retain clamped user prompts and final assistant text. Recent turns keep
    their native messages so tool-use behavior remains visible, but tool-result
    payloads are replaced. If those turns are still too large, whole oldest turns are
    removed; the final turn then degrades to dialogue-only and finally latest-user-only.
    """
    turns = _split_turns(messages)
    recent_start = max(0, len(turns) - config.keep_recent_turns)
    compacted = [
        _compact_recent_turn(turn) if index >= recent_start else _dialogue_only(turn, clamp=True)
        for index, turn in enumerate(turns)
    ]
    compacted = [turn for turn in compacted if turn]

    checkpoint_exchange: list[ModelMessage] = [
        ModelRequest(
            parts=[UserPromptPart(content=checkpoint_request)],
            metadata={_CHECKPOINT_METADATA: True},
        ),
        ModelResponse(
            parts=[TextPart(content=checkpoint_text)],
            metadata={_CHECKPOINT_METADATA: True},
        ),
    ]

    while len(compacted) > 1 and _estimate_turns(compacted, checkpoint_exchange) > config.target_tokens:
        compacted.pop(0)

    if compacted and _estimate_turns(compacted, checkpoint_exchange) > config.target_tokens:
        compacted[-1] = _dialogue_only(turns[-1], clamp=False)
    if compacted and _estimate_turns(compacted, checkpoint_exchange) > config.target_tokens:
        compacted[-1] = _latest_user_only(turns[-1])

    rewritten = [message for turn in compacted for message in turn] + checkpoint_exchange
    if _estimate_messages_tokens(rewritten) > config.target_tokens:
        raise ValueError("checkpoint and latest user message exceed the compaction target")
    return rewritten


def _split_turns(messages: list[ModelMessage]) -> list[list[ModelMessage]]:
    """Group messages from each real user request up to the next user request.

    Host notifications do not open turns, and old synthetic checkpoints are discarded
    because the newly generated checkpoint supersedes them.
    """
    turns: list[list[ModelMessage]] = []
    for message in messages:
        if message.metadata and message.metadata.get(_CHECKPOINT_METADATA):
            continue
        if _is_user_request(message):
            turns.append([message])
        elif turns:
            turns[-1].append(message)
    return turns


def _is_user_request(message: ModelMessage) -> bool:
    """Return whether a request is an actual user turn rather than a host event."""
    return (
        isinstance(message, ModelRequest)
        and not (message.metadata and message.metadata.get(HOST_EVENT_METADATA_KEY))
        and any(isinstance(part, UserPromptPart) for part in message.parts)
    )


def _compact_recent_turn(turn: list[ModelMessage]) -> list[ModelMessage]:
    """Keep a recent turn intact except for replaceable tool-result payloads."""
    compacted: list[ModelMessage] = []
    for message in turn:
        if not isinstance(message, ModelRequest):
            compacted.append(message)
            continue
        parts = [
            replace(part, content=_tool_result_placeholder(part)) if isinstance(part, ToolReturnPart) else part
            for part in message.parts
        ]
        compacted.append(replace(message, parts=parts))
    return compacted


def _dialogue_only(turn: list[ModelMessage], *, clamp: bool) -> list[ModelMessage]:
    """Project a turn to user prompts and final assistant text only.

    Responses containing tool calls are execution steps, not final answers. Rebuilt
    text responses intentionally drop provider IDs, signatures, and usage that no
    longer describe the projected history.
    """
    dialogue: list[ModelMessage] = []
    for message in turn:
        if isinstance(message, ModelRequest):
            if message.metadata and message.metadata.get(HOST_EVENT_METADATA_KEY):
                continue
            parts = [part for part in message.parts if isinstance(part, UserPromptPart)]
            if parts:
                dialogue.append(
                    replace(message, parts=[_clamp_user_prompt(part) for part in parts] if clamp else parts)
                )
            continue
        if any(isinstance(part, ToolCallPart) for part in message.parts):
            continue
        text = "".join(part.content for part in message.parts if isinstance(part, TextPart))
        if text:
            dialogue.append(_text_response(message, _clamp_text(text) if clamp else text))
    return dialogue


def _latest_user_only(turn: list[ModelMessage]) -> list[ModelMessage]:
    """Return the turn's user request as the last-resort protected context."""
    for message in turn:
        if isinstance(message, ModelRequest) and _is_user_request(message):
            parts = [part for part in message.parts if isinstance(part, UserPromptPart)]
            return [replace(message, parts=parts)]
    return []


def _clamp_user_prompt(part: UserPromptPart) -> UserPromptPart:
    if not isinstance(part.content, str):
        return part
    return replace(part, content=_clamp_text(part.content))


def _clamp_text(text: str) -> str:
    """Bound old dialogue to 100 estimated tokens while retaining head and tail."""
    max_chars = _OLD_MESSAGE_TOKENS * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    available = max_chars - len(_TRUNCATION_MARKER)
    head = available * 7 // 10
    return text[:head] + _TRUNCATION_MARKER + text[-(available - head) :]


def _tool_result_placeholder(part: ToolReturnPart) -> str:
    """Return an omission marker, retaining a stored-message pointer when present."""
    if isinstance(part.metadata, dict) and (message_id := part.metadata.get("message_id")):
        return f"{_TOOL_RESULT_PLACEHOLDER}; full result: {message_id}"
    return _TOOL_RESULT_PLACEHOLDER


def _text_response(message: ModelResponse, content: str) -> ModelResponse:
    """Build a clean text-only projection of an assistant response."""
    return ModelResponse(
        parts=[TextPart(content=content)],
        model_name=message.model_name,
        timestamp=message.timestamp,
        run_id=message.run_id,
        conversation_id=message.conversation_id,
    )


def _estimate_turns(turns: list[list[ModelMessage]], checkpoint: list[ModelMessage]) -> int:
    """Estimate flattened turns together with their protected checkpoint."""
    return _estimate_messages_tokens([message for turn in turns for message in turn] + checkpoint)


def _estimate_messages_tokens(messages: list[ModelMessage]) -> int:
    """Estimate serialized message size at four characters per token."""
    if not messages:
        return 0
    return _estimate_text_tokens(ModelMessagesTypeAdapter.dump_json(messages).decode())


def _estimate_text_tokens(text: str) -> int:
    return math.ceil(len(text) / _CHARS_PER_TOKEN)


def _context_window(model: str) -> int | None:
    """Resolve the model context window from genai-prices when known."""
    model_ref = model.partition(":")[2] or model
    try:
        calculation = genai_prices.calc_price(
            genai_prices.Usage(input_tokens=0, output_tokens=0),
            model_ref,
        )
    except LookupError:
        return None
    return calculation.model.context_window
