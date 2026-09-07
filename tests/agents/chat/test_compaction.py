from __future__ import annotations

from typing import Any, cast

from pydantic_ai import RunUsage
from pydantic_ai.messages import (
    BinaryContent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import RequestUsage

from tabulaflow.agents.chat.compaction import (
    CompactionConfig,
    compact_history,
    estimate_context_tokens,
)
from tabulaflow.agents.chat.events import ChatEvent, CompactionFinished, CompactionStarted
from tabulaflow.agents.chat.session import ChatSession
from tabulaflow.data.registry import DataConnectorRegistry


def test_estimate_context_tokens_uses_latest_usage_anchor() -> None:
    messages: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content="old" * 10_000)]),
        ModelResponse(parts=[TextPart(content="answer")], usage=RequestUsage(input_tokens=100, output_tokens=20)),
        ModelRequest(parts=[UserPromptPart(content="x" * 400)]),
    ]

    estimate = estimate_context_tokens(messages, "y" * 400)

    assert 320 <= estimate <= 380


def test_estimate_context_tokens_does_not_reuse_anchor_before_checkpoint() -> None:
    messages: list[ModelMessage] = [
        ModelResponse(parts=[TextPart(content="old")], usage=RequestUsage(input_tokens=200_000)),
    ]
    compacted = compact_history(
        messages,
        checkpoint_request="checkpoint request",
        checkpoint_text="checkpoint response",
        config=CompactionConfig(),
    )

    assert estimate_context_tokens(compacted) < 1_000


def test_estimate_context_tokens_does_not_serialize_media_bytes() -> None:
    messages: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content=["inspect", BinaryContent(b"x" * 100_000, media_type="image/png")])])
    ]

    assert estimate_context_tokens(messages) < 200


def test_estimate_context_tokens_ignores_message_bookkeeping() -> None:
    plain: list[ModelMessage] = [ModelResponse(parts=[TextPart(content="answer")])]
    decorated: list[ModelMessage] = [
        ModelResponse(
            parts=[TextPart(content="answer", provider_details={"diagnostic": "x" * 10_000})],
            usage=RequestUsage(input_tokens=0, details={"diagnostic": 10_000}),
            provider_details={"diagnostic": "x" * 10_000},
            provider_response_id="response-123",
            run_id="run-123",
            conversation_id="conversation-123",
            metadata={"diagnostic": "x" * 10_000},
        )
    ]

    assert estimate_context_tokens(decorated) == estimate_context_tokens(plain)


def test_estimate_context_tokens_counts_tool_arguments_and_reasoning_signatures() -> None:
    small: list[ModelMessage] = [
        ModelResponse(
            parts=[
                ThinkingPart(content="thinking", signature="signature"),
                ToolCallPart("run_query", {"query": "select 1"}, "call-1"),
            ]
        )
    ]
    large: list[ModelMessage] = [
        ModelResponse(
            parts=[
                ThinkingPart(content="thinking", signature="x" * 1_000),
                ToolCallPart("run_query", {"query": "x" * 1_000}, "call-1"),
            ]
        )
    ]

    assert estimate_context_tokens(large) > estimate_context_tokens(small) + 400


def test_compact_history_keeps_execution_and_pairs_tools_when_it_fits() -> None:
    messages: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content="a" * 1_000)]),
        ModelResponse(parts=[TextPart(content="b" * 1_000)]),
        ModelRequest(parts=[UserPromptPart(content="recent question")]),
        ModelResponse(parts=[ToolCallPart("run_query", {"query": "select 1"}, "call-1")]),
        ModelRequest(parts=[ToolReturnPart("run_query", "large result", "call-1")]),
        ModelResponse(parts=[TextPart(content="recent answer")]),
    ]

    compacted = compact_history(
        messages,
        checkpoint_request="make checkpoint",
        checkpoint_text="checkpoint text",
        config=CompactionConfig(trigger_tokens=10_000, target_tokens=2_000),
    )

    first_part = compacted[0].parts[0]
    assert isinstance(first_part, UserPromptPart)
    assert first_part.content == "a" * 1_000
    calls = [
        part
        for message in compacted
        if isinstance(message, ModelResponse)
        for part in message.parts
        if isinstance(part, ToolCallPart)
    ]
    returns = [
        part
        for message in compacted
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]
    assert [part.tool_call_id for part in calls] == ["call-1"]
    assert [part.tool_call_id for part in returns] == ["call-1"]
    assert returns[0].content == "[tool result omitted after execution during context compaction]"
    assert isinstance(compacted[-2], ModelRequest)
    assert isinstance(compacted[-2].parts[0], UserPromptPart)
    assert compacted[-2].parts[0].content == "make checkpoint"
    assert isinstance(compacted[-1], ModelResponse)
    assert isinstance(compacted[-1].parts[0], TextPart)
    assert compacted[-1].parts[0].content == "checkpoint text"


def test_compact_history_drops_oldest_dialogue_to_fit_budget() -> None:
    messages: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content=f"old-{index}-" + "x" * 300)]) for index in range(20)
    ]
    messages.append(ModelRequest(parts=[UserPromptPart(content="latest user")]))

    compacted = compact_history(
        messages,
        checkpoint_request="checkpoint request",
        checkpoint_text="checkpoint response",
        config=CompactionConfig(trigger_tokens=1_000, target_tokens=500),
    )

    contents = [part.content for message in compacted for part in message.parts if isinstance(part, UserPromptPart)]
    assert "old-0-" not in "\n".join(str(content) for content in contents)
    assert "latest user" in contents
    assert contents[-1] == "checkpoint request"


def test_compact_history_drops_raw_turns_before_previous_checkpoint() -> None:
    media = BinaryContent(b"secret payload", media_type="image/png")
    original: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content=["old question", media])]),
        ModelResponse(parts=[TextPart(content="old answer")]),
    ]
    first_generation = compact_history(
        original,
        checkpoint_request="first checkpoint request",
        checkpoint_text="first checkpoint response",
        config=CompactionConfig(trigger_tokens=2_000, target_tokens=1_000),
    )
    first_generation.extend(
        [
            ModelRequest(parts=[UserPromptPart(content="recent question")]),
            ModelResponse(parts=[TextPart(content="recent answer")]),
        ]
    )

    second_generation = compact_history(
        first_generation,
        checkpoint_request="second checkpoint request",
        checkpoint_text="second checkpoint response",
        config=CompactionConfig(trigger_tokens=2_000, target_tokens=1_000),
    )

    user_contents = [
        part.content for message in second_generation for part in message.parts if isinstance(part, UserPromptPart)
    ]
    assert user_contents == ["recent question", "second checkpoint request"]
    assert not any(
        isinstance(item, BinaryContent)
        for message in second_generation
        for request_part in message.parts
        if isinstance(request_part, UserPromptPart)
        if not isinstance(request_part.content, str)
        for item in request_part.content
    )


def test_compact_history_drops_recent_tools_when_they_exceed_budget() -> None:
    messages: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content="latest user")]),
        ModelResponse(parts=[ToolCallPart("run_query", {"query": "x" * 4_000}, "call-1")]),
        ModelRequest(parts=[ToolReturnPart("run_query", "result", "call-1")]),
        ModelResponse(parts=[TextPart(content="latest answer")]),
    ]

    compacted = compact_history(
        messages,
        checkpoint_request="checkpoint request",
        checkpoint_text="checkpoint response",
        config=CompactionConfig(trigger_tokens=2_000, target_tokens=700),
    )

    assert not any(isinstance(part, (ToolCallPart, ToolReturnPart)) for message in compacted for part in message.parts)
    assert any(
        isinstance(part, UserPromptPart) and part.content == "latest user"
        for message in compacted
        for part in message.parts
    )


def test_compact_history_keeps_user_prompts_before_evicting_turns() -> None:
    messages: list[ModelMessage] = []
    for index in range(3):
        messages.extend(
            [
                ModelRequest(parts=[UserPromptPart(content=f"user-{index}")]),
                ModelResponse(parts=[ToolCallPart("run_query", {"query": "x" * 2_000}, f"call-{index}")]),
                ModelRequest(parts=[ToolReturnPart("run_query", "result", f"call-{index}")]),
                ModelResponse(parts=[TextPart(content="answer" * 300)]),
            ]
        )

    compacted = compact_history(
        messages,
        checkpoint_request="checkpoint request",
        checkpoint_text="checkpoint response",
        config=CompactionConfig(trigger_tokens=3_000, target_tokens=700),
    )

    user_prompts = [
        part.content
        for message in compacted
        for part in message.parts
        if isinstance(part, UserPromptPart) and not message.metadata
    ]
    assert user_prompts == ["user-0", "user-1", "user-2"]
    assert not any(
        isinstance(part, (ToolCallPart, ToolReturnPart)) for message in compacted[:-2] for part in message.parts
    )


async def test_chat_session_compacts_before_pending_question() -> None:
    session = ChatSession(
        registry=DataConnectorRegistry(),
        model="test",
        reasoning="medium",
        compaction=CompactionConfig(trigger_tokens=1_000, target_tokens=800),
    )
    old_history: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content="old question")]),
        ModelResponse(
            parts=[TextPart(content="old answer")],
            usage=RequestUsage(input_tokens=1_500, output_tokens=100),
        ),
    ]
    session._context_messages = old_history
    checkpoint_messages: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content="internal request")]),
        ModelResponse(parts=[TextPart(content="checkpoint")], finish_reason="stop"),
    ]

    class StubAgent:
        async def run(self, prompt: str, **kwargs: Any) -> Any:
            assert kwargs["message_history"] is old_history
            assert "pending question" not in prompt

            class Result:
                output = "ANSWER:\ncheckpoint"

                @staticmethod
                def new_messages() -> list[ModelMessage]:
                    return checkpoint_messages

            return Result()

    session._pydantic_ai_agent = cast(Any, StubAgent())

    events: list[ChatEvent] = []
    session._active_emit = events.append

    await session._compact_before_turn("pending question", RunUsage())

    assert session._context_messages is not old_history
    assert isinstance(session._context_messages[-1], ModelResponse)
    assert session._context_messages[-1].parts[0].content == "checkpoint"  # type: ignore[union-attr]
    assert session._transcript_messages[-2:] == checkpoint_messages
    assert [type(event) for event in events] == [CompactionStarted, CompactionFinished]
