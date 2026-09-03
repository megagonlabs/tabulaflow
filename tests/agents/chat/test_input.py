from typing import Any, cast

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import BinaryContent, ModelRequest, UserPromptPart
from pydantic_ai.models.test import TestModel

from tabulaflow.agents.chat import ChatSession
from tabulaflow.agents.chat.input import describe_chat_input
from tabulaflow.agents.message_store import MESSAGE_THRESHOLD_CHARS
from tabulaflow.data.registry import DBRegistry


def test_describe_chat_input_preserves_order_without_media_payloads() -> None:
    data = b"secret-media-payload"
    content: list[str | BinaryContent] = [
        "before",
        BinaryContent(data, media_type="image/png", identifier="image-1"),
        "after",
    ]

    description = describe_chat_input(content)

    assert description.splitlines()[0] == "before"
    assert description.splitlines()[1] == f"[Image: image/png, {len(data)} bytes]"
    assert description.splitlines()[2] == "after"
    assert "secret-media-payload" not in description


async def test_chat_session_passes_ordered_multimodal_input_to_pydantic_ai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tabulaflow.agents.trace.compute_api_cost", lambda *args, **kwargs: 0)
    session = ChatSession(registry=DBRegistry(), model="test", reasoning="medium", compaction=None)
    session._pydantic_ai_agent = cast(
        Any,
        Agent(TestModel(custom_output_text="ANSWER:\nok"), output_type=str),
    )
    stored: list[str] = []

    class MessageScope:
        async def add(self, **kwargs: Any) -> str:
            stored.append(kwargs["content"])
            return f"M{len(stored)}"

    session._main_scope = cast(Any, MessageScope())
    media = BinaryContent(b"image", media_type="image/png")
    text = "x" * (MESSAGE_THRESHOLD_CHARS + 1)

    try:
        result = await session.run([text, media])
        follow_up = await session.run("summarize it")
    finally:
        await session.aclose()

    assert result.text == "ok"
    assert follow_up.text == "ok"
    request = next(
        message
        for message in session._context_messages
        if isinstance(message, ModelRequest)
        and any(isinstance(part, UserPromptPart) and not isinstance(part.content, str) for part in message.parts)
    )
    prompt = next(
        part for part in request.parts if isinstance(part, UserPromptPart) and not isinstance(part.content, str)
    )
    assert not isinstance(prompt.content, str)
    assert isinstance(prompt.content[0], str)
    assert prompt.content[0].startswith("[message_id=M1]")
    assert isinstance(prompt.content[1], BinaryContent)
    assert prompt.content[1].data == b"image"
    assert stored == [describe_chat_input([text, media]), "summarize it"]
    assert "b'image'" not in stored[0]
