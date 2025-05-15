import json
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.messages import ModelMessage
from mintq.schema import Trajectory, ToolCall, AssistantMessage, ToolResponse, UserMessage, SystemMessage


def get_pydantic_ai_llm(litellm_id: str):
    provider, model = litellm_id.split("/", 1)
    if provider == "openai":
        return OpenAIModel(model_name=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def pydantic_ai_messages_to_trajectory(messages: list[ModelMessage]) -> Trajectory:
    new_msgs = []
    for msg in messages:
        if msg.kind == "request":
            for part in msg.parts:
                if part.part_kind == "system-prompt":
                    new_msgs.append(SystemMessage(content=part.content))
                elif part.part_kind == "user-prompt":
                    new_msgs.append(UserMessage(content=part.content))
                elif part.part_kind == "tool-return":
                    new_msgs.append(ToolResponse(response=part.content, tool_call_id=part.tool_call_id))
                elif part.part_kind == "retry-prompt":
                    assert isinstance(part.content, str), f"{str(part.content)} is of type {type(part.content)}"
                    new_msgs.append(ToolResponse(response=part.content, tool_call_id=part.tool_call_id))
                else:
                    raise ValueError(f"Unknown message part type: {part.part_kind}")
        elif msg.kind == "response":
            new_msg = AssistantMessage(content="", tool_calls=[])
            for part in msg.parts:
                if part.part_kind == "text":
                    new_msg.content += part.content
                elif part.part_kind == "tool-call":
                    arguments = part.args
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)
                    new_msg.tool_calls.append(
                        ToolCall(tool_call_id=part.tool_call_id, name=part.tool_name, arguments=arguments)
                    )
            new_msgs.append(new_msg)
        else:
            raise ValueError(f"Unknown message type: {msg.kind}")
    return Trajectory(messages=new_msgs)
