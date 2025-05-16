import json
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.messages import ModelMessage
from mintq.schema import Trajectory, ToolCall, AssistantMessage, ToolResponse, UserMessage, SystemMessage, Message


def get_pydantic_ai_llm(litellm_id: str):
    provider, model = litellm_id.split("/", 1)
    if provider == "openai":
        return OpenAIModel(model_name=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def pydantic_ai_messages_to_trajectory(messages: list[ModelMessage]) -> Trajectory:
    trajectory = Trajectory(messages=[])
    if messages[0].kind == "request" and messages[0].instructions:
        trajectory.messages.append(SystemMessage(content=messages[0].instructions))
    for msg in messages:
        if msg.kind == "request":
            for part in msg.parts:
                if part.part_kind == "system-prompt":
                    trajectory.messages.append(SystemMessage(content=part.content))
                elif part.part_kind == "user-prompt":
                    if not isinstance(part.content, str):
                        raise ValueError(f"Only string is supported for user prompt, got {type(part.content)}")
                    trajectory.messages.append(UserMessage(content=part.content))
                elif part.part_kind == "tool-return":
                    if not isinstance(part.content, str):
                        raise ValueError(f"Tool return is not a string: {part.content}")
                    trajectory.messages.append(ToolResponse(response=part.content, tool_call_id=part.tool_call_id))
                elif part.part_kind == "retry-prompt":
                    assert isinstance(part.content, str), f"{str(part.content)} is of type {type(part.content)}"
                    trajectory.messages.append(ToolResponse(response=part.content, tool_call_id=part.tool_call_id))
                else:
                    raise ValueError(f"Unknown message part type: {part.part_kind}")
        elif msg.kind == "response":
            new_msg = AssistantMessage(content="", tool_calls=[])
            for part in msg.parts:  # type: ignore
                if part.part_kind == "text":
                    new_msg.content += part.content
                elif part.part_kind == "tool-call":
                    arguments = part.args
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)
                    new_msg.tool_calls.append(
                        ToolCall(tool_call_id=part.tool_call_id, name=part.tool_name, arguments=arguments)
                    )
                else:
                    raise ValueError(f"Unknown message part type: {part.part_kind}")
            trajectory.messages.append(new_msg)
        else:
            raise ValueError(f"Unknown message type: {msg.kind}")
    return trajectory
