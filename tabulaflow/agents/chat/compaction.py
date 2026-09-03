"""Simple, provider-agnostic checkpoint compaction for interactive chat sessions.

Rather than combining multiple trimming strategies or sending a flattened transcript
to a separate summarizer, the current agent writes one checkpoint from its native
conversation. This preserves recent tool context, keeps provider-carried reasoning
state available, reuses the existing prompt prefix for the checkpoint request, and
avoids a second model configuration.

The remaining rewrite is deterministic: retain only turns after the previous
checkpoint, replace tool-result payloads, append the new checkpoint, then progressively
remove execution details and assistant dialogue before evicting oldest user prompts.
Tool structure is removed as a whole, preserving provider-valid pairing while keeping
the user's recent requests for as long as the budget permits.

The checkpoint and latest user request are never silently truncated. If those alone
cannot fit, compaction fails explicitly.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from typing import Any, cast

import genai_prices
from pydantic_ai.messages import (
    BinaryContent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from tabulaflow.agents.chat.input import ChatInput, describe_chat_input


_CHARS_PER_TOKEN = 4
_MESSAGE_OVERHEAD_CHARS = 16
_PART_OVERHEAD_CHARS = 8
_CONTEXT_RESERVE_TOKENS = 32_000
_CHECKPOINT_TOKEN_LIMIT = 4_000
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

    ``trigger_tokens`` starts checkpointing and ``target_tokens`` bounds the rewritten
    history.
    """

    trigger_tokens: int = 240_000
    target_tokens: int = 32_000

    def __post_init__(self) -> None:
        if not 0 < self.target_tokens < self.trigger_tokens:
            raise ValueError("expected 0 < target_tokens < trigger_tokens")


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


def estimate_context_tokens(messages: list[ModelMessage], additional_content: ChatInput = "") -> int:
    """Estimate a prospective request from its latest provider-usage anchor.

    The latest uncompacted response's provider-reported input plus output usage is
    ground truth for history through that response. Only later messages and pending
    content use the four-characters-per-token estimate. A checkpoint is a rewrite
    boundary, so estimates after one start from the compacted messages instead of an
    obsolete pre-compaction usage anchor.
    """
    additional = _estimate_text_tokens(describe_chat_input(additional_content))
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

    The previous checkpoint supersedes every raw turn before it. Newer turns initially
    retain their native messages with tool-result payloads replaced. If the result is
    too large, turns degrade oldest-first to dialogue-only and then user-only before
    oldest turns are evicted.
    """
    turns = _group_turns_since_checkpoint(messages)
    compacted = [_project_execution(turn) for turn in turns]
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

    for index in range(len(compacted)):
        if _estimate_turns(compacted, checkpoint_exchange) <= config.target_tokens:
            break
        compacted[index] = _project_dialogue(turns[index])

    for index in range(len(compacted)):
        if _estimate_turns(compacted, checkpoint_exchange) <= config.target_tokens:
            break
        compacted[index] = _project_user(turns[index])

    while len(compacted) > 1 and _estimate_turns(compacted, checkpoint_exchange) > config.target_tokens:
        compacted.pop(0)

    rewritten = [message for turn in compacted for message in turn] + checkpoint_exchange
    if _estimate_messages_tokens(rewritten) > config.target_tokens:
        raise ValueError("checkpoint and latest user message exceed the compaction target")
    return rewritten


def _group_turns_since_checkpoint(messages: list[ModelMessage]) -> list[list[ModelMessage]]:
    """Group real user turns completed after the previous checkpoint.

    The new checkpoint summarizes the whole supplied context, so the previous checkpoint
    and every raw turn it already covered are superseded. Host notifications do not open
    turns.
    """
    start = max(
        (
            index + 1
            for index, message in enumerate(messages)
            if message.metadata and message.metadata.get(_CHECKPOINT_METADATA)
        ),
        default=0,
    )
    turns: list[list[ModelMessage]] = []
    for message in messages[start:]:
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


def _project_execution(turn: list[ModelMessage]) -> list[ModelMessage]:
    """Keep a turn's execution structure while replacing tool-result payloads."""
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


def _project_dialogue(turn: list[ModelMessage]) -> list[ModelMessage]:
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
                dialogue.append(replace(message, parts=parts))
            continue
        if any(isinstance(part, ToolCallPart) for part in message.parts):
            continue
        text = "".join(part.content for part in message.parts if isinstance(part, TextPart))
        if text:
            dialogue.append(_text_response(message, text))
    return dialogue


def _project_user(turn: list[ModelMessage]) -> list[ModelMessage]:
    """Project a turn to its user request."""
    for message in turn:
        if isinstance(message, ModelRequest) and _is_user_request(message):
            parts = [part for part in message.parts if isinstance(part, UserPromptPart)]
            return [replace(message, parts=parts)]
    return []


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
    """Estimate model-visible content without counting internal bookkeeping."""
    chars = 0
    for message in messages:
        chars += _MESSAGE_OVERHEAD_CHARS
        if isinstance(message, ModelRequest) and message.instructions:
            chars += len(message.instructions)
        for part in message.parts:
            chars += _PART_OVERHEAD_CHARS
            if isinstance(part, UserPromptPart):
                chars += len(describe_chat_input(cast(ChatInput, part.content)))
                continue
            for field in ("tool_name", "args", "content", "transcript", "signature", "tools_added"):
                chars += _estimate_value_chars(getattr(part, field, None))
    return math.ceil(chars / _CHARS_PER_TOKEN)


def _estimate_value_chars(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value)
    if isinstance(value, BinaryContent):
        return len(describe_chat_input([value]))
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str))


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
