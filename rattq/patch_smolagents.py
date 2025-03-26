from smolagents.models import MessageRole
from smolagents.memory import ActionStep
from typing import List, Dict
import json
from copy import deepcopy


def ActionStep__to_messages(
    self, summary_mode: bool = False, show_model_input_messages: bool = False
) -> List[dict]:
    messages = []
    if self.model_input_messages is not None and show_model_input_messages:
        raise NotImplementedError("Model input messages are not implemented")
        messages.append(
            Message(role=MessageRole.SYSTEM, content=self.model_input_messages)
        )
    if self.model_output is not None and not summary_mode:
        messages.append(
            dict(
                role=MessageRole.ASSISTANT,
                content=self.model_output.strip(),
            )
        )

    if self.tool_calls is not None:
        messages.append(
            dict(
                role=MessageRole.TOOL_CALL,
                tool_calls=[
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in self.tool_calls
                ],
            )
        )

    if self.observations is not None:
        messages.append(
            dict(
                role=MessageRole.TOOL_RESPONSE,
                tool_call_id=self.tool_calls[0].id,
                content=f"Observation:\n{self.observations}",
            )
        )
    if self.error is not None:
        messages.append(
            dict(
                role=MessageRole.TOOL_RESPONSE,
                tool_call_id=self.tool_calls[0].id,
                content="Error:\n" + str(self.error),
            )
        )

    if self.observations_images:
        raise NotImplementedError("Observations images are not implemented")
        messages.append(
            dict(
                role=MessageRole.USER,
                content=[{"type": "text", "text": "Here are the observed images:"}]
                + [
                    {
                        "type": "image",
                        "image": image,
                    }
                    for image in self.observations_images
                ],
            )
        )
    return messages


def get_clean_message_list(
    message_list: List[Dict[str, str]],
    role_conversions: Dict[MessageRole, MessageRole] = {},
    convert_images_to_image_urls: bool = False,
    flatten_messages_as_text: bool = False,
) -> List[Dict[str, str]]:
    """
    Subsequent messages with the same role will be concatenated to a single message.
    output_message_list is a list of messages that will be used to generate the final message that is chat template compatible with transformers LLM chat template.

    Args:
        message_list (`list[dict[str, str]]`): List of chat messages.
        role_conversions (`dict[MessageRole, MessageRole]`, *optional* ): Mapping to convert roles.
        convert_images_to_image_urls (`bool`, default `False`): Whether to convert images to image URLs.
        flatten_messages_as_text (`bool`, default `False`): Whether to flatten messages as text.
    """
    role_conversions = {
        MessageRole.USER: "user",
        MessageRole.ASSISTANT: "assistant",
        MessageRole.TOOL_CALL: "assistant",
        MessageRole.TOOL_RESPONSE: "tool",
        MessageRole.SYSTEM: "system",
    }
    output_message_list = []
    message_list = deepcopy(message_list)  # Avoid modifying the original list
    for message in message_list:
        role = message["role"]
        if role not in MessageRole.roles():
            raise ValueError(
                f"Incorrect role {role}, only {MessageRole.roles()} are supported for now."
            )

        if role in role_conversions:
            message["role"] = role_conversions[role]

        output_message_list.append(message)
    return output_message_list


def patch_smolagents(func):
    from unittest.mock import patch

    def wrapper(*args, **kwargs):
        patch_map = [
            ("smolagents.memory.ActionStep.to_messages", ActionStep__to_messages),
            ("smolagents.models.get_clean_message_list", get_clean_message_list),
        ]

        patchers = [patch(target, new=new) for target, new in patch_map]
        started = [p.start() for p in patchers]
        try:
            return func(*args, **kwargs)
        finally:
            for p in patchers:
                p.stop()

    return wrapper
