from typing import Any
from functools import partial
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart


def max_steps_processor(
    ctx: RunContext[Any],
    messages: list[ModelMessage],
    max_steps: int,
) -> list[ModelMessage]:
    assert messages is ctx.messages  # We want the injected message to be preserved in the message history as well
    if ctx.run_step >= max_steps - 1:
        content = "You are about to reach the maximum number of steps. You have one more attempt to execute a tool before submitting the final answer."
        messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
    return messages


def get_max_steps_processor(max_steps: int) -> Any:
    assert max_steps >= 1
    return partial(max_steps_processor, max_steps=max_steps)
