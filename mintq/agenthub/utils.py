from typing import Any
from functools import partial
from typing import Callable
from opentelemetry.trace import get_tracer_provider
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from functools import wraps
from mintq.schema import NL2QTask
from mintq.config import config


def max_steps_processor(
    ctx: RunContext[Any],
    messages: list[ModelMessage],
    max_steps: int,
) -> list[ModelMessage]:
    if ctx.run_step >= max_steps - 1:
        content = "You are about to reach the maximum number of steps. You have one more attempt to execute a tool before submitting the final answer."
        msg = ModelRequest(parts=[UserPromptPart(content=content)])
        return messages + [msg]
    return messages


def get_max_steps_processor(max_steps: int) -> Any:
    assert max_steps >= 1
    return partial(max_steps_processor, max_steps=max_steps)


def instrument(predict_async: Callable[..., Any]) -> Callable[..., Any]:
    if not config.instrument_enabled:
        return predict_async

    tracer_provider = get_tracer_provider()
    tracer = tracer_provider.get_tracer(__name__)

    @wraps(predict_async)
    async def wrapper(self, task: NL2QTask, *args: Any, **kwargs: Any) -> Any:
        with tracer.start_as_current_span(task.qid):
            return await wrapper(self, task, *args, **kwargs)

    return wrapper
