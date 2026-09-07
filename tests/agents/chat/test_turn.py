from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from tabulaflow.agents.chat.compaction import HOST_EVENT_METADATA_KEY
from tabulaflow.agents.chat.turn import _patch_incomplete_messages


def test_patch_incomplete_messages_makes_only_trailing_response_portable() -> None:
    completed_response = ModelResponse(
        parts=[TextPart(content="earlier", id="msg_complete", provider_name="openai")],
        provider_name="openai",
        provider_response_id="resp_complete",
    )
    incomplete_response = ModelResponse(
        parts=[
            ThinkingPart(
                content="summary",
                id="rs_incomplete",
                signature="encrypted",
                provider_name="openai",
                provider_details={"encrypted_content": "encrypted"},
            ),
            TextPart(
                content="partial answer",
                id="msg_incomplete",
                provider_name="openai",
                provider_details={"phase": "final_answer"},
            ),
            ToolCallPart(
                tool_name="lookup",
                args={"key": "value"},
                tool_call_id="call_1",
                id="fc_incomplete",
                provider_name="openai",
                provider_details={"namespace": "lookup"},
            ),
        ],
        provider_name="openai",
        provider_url="https://api.openai.com/v1",
        provider_details={"conversation_id": "conv_incomplete"},
        provider_response_id="resp_incomplete",
        conversation_id="conv_incomplete",
    )

    patched = _patch_incomplete_messages(
        [completed_response, ModelRequest(parts=[UserPromptPart(content="question")]), incomplete_response],
        {},
        interrupted=True,
    )

    assert patched[0] is completed_response
    assert completed_response.provider_response_id == "resp_complete"

    portable = patched[2]
    assert isinstance(portable, ModelResponse)
    assert portable.provider_name is None
    assert portable.provider_url is None
    assert portable.provider_details is None
    assert portable.provider_response_id is None
    assert portable.conversation_id is None

    thinking, text, tool_call = portable.parts
    assert isinstance(thinking, ThinkingPart)
    assert thinking.content == "summary"
    assert thinking.id is None
    assert thinking.signature is None
    assert thinking.provider_name is None
    assert thinking.provider_details is None
    assert isinstance(text, TextPart)
    assert text.content == "partial answer"
    assert text.id is None
    assert text.provider_name is None
    assert text.provider_details is None
    assert isinstance(tool_call, ToolCallPart)
    assert tool_call.tool_name == "lookup"
    assert tool_call.args == {"key": "value"}
    assert tool_call.tool_call_id == "call_1"
    assert tool_call.id is None
    assert tool_call.provider_name is None
    assert tool_call.provider_details is None

    assert incomplete_response.provider_response_id == "resp_incomplete"
    original_thinking = incomplete_response.parts[0]
    assert isinstance(original_thinking, ThinkingPart)
    assert original_thinking.id == "rs_incomplete"


def test_patch_incomplete_messages_pairs_tool_calls_and_records_cause() -> None:
    response = ModelResponse(
        parts=[
            ToolCallPart(tool_name="finished", args={}, tool_call_id="call_1"),
            ToolCallPart(tool_name="pending", args={}, tool_call_id="call_2"),
        ]
    )
    completed = ToolReturnPart(tool_name="finished", tool_call_id="call_1", content="result")

    patched = _patch_incomplete_messages(
        [response],
        {"call_1": completed},
        interrupted=False,
    )

    tool_results = patched[1]
    assert isinstance(tool_results, ModelRequest)
    assert tool_results.parts[0] is completed
    synthetic = tool_results.parts[1]
    assert isinstance(synthetic, ToolReturnPart)
    assert synthetic.tool_call_id == "call_2"
    assert isinstance(synthetic.content, str)
    assert "failed with an error" in synthetic.content

    host_event = patched[2]
    assert isinstance(host_event, ModelRequest)
    assert host_event.metadata == {HOST_EVENT_METADATA_KEY: True}
    assert isinstance(host_event.parts[0], UserPromptPart)
    assert host_event.parts[0].content == "[system: the previous run failed with an error.]"
