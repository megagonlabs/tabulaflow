from typing import Any, Callable
from functools import partial
import asyncio
from opentelemetry import trace
from pydantic_ai import RunContext, Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from dataclasses import dataclass, field
from functools import wraps
from pydantic import BaseModel
from mintq.schema import NL2QTask
from mintq.config import config
from mintq.db_connector import NL2QDBConnector
from mintq.schema import Usage, Trajectory
from mintq.toolhub import BaseTool


def max_steps_processor(
    ctx: RunContext[Any],
    messages: list[ModelMessage],
    max_steps: int,
) -> list[ModelMessage]:
    if ctx.run_step >= max_steps - 1:
        if ctx.run_step == max_steps - 1:
            content = "You are about to reach the maximum number of steps. You have one more attempt to execute a tool before submitting the final answer."
        else:
            content = "You have reached the maximum number of steps. Please submit the final answer right now."
        msg = ModelRequest(parts=[UserPromptPart(content=content)])
        assert messages == ctx.messages
        ctx.messages.append(msg)
        return ctx.messages
    return messages


def get_max_steps_processor(max_steps: int) -> Any:
    assert max_steps >= 1
    return partial(max_steps_processor, max_steps=max_steps)


def instrument(predict_async_fn: Callable[..., Any]) -> Callable[..., Any]:
    if not config.instrument_enabled:
        return predict_async_fn

    @wraps(predict_async_fn)
    async def wrapper(self, task: NL2QTask, *args: Any, **kwargs: Any) -> Any:
        from mintq import __version__

        tracer_provider = trace.get_tracer_provider()
        tracer = tracer_provider.get_tracer("mintq", __version__)

        current_span = trace.get_current_span()

        if current_span and current_span.get_span_context().is_valid:
            # Already inside a span, do not start a new span
            return await predict_async_fn(self, task, *args, **kwargs)

        span_name = f"qid={task.qid} | agent={self.name}".strip()
        if config.instrument_prefix:
            span_name = f"{config.instrument_prefix} | {span_name}"
        with tracer.start_as_current_span(span_name):
            return await predict_async_fn(self, task, *args, **kwargs)

    return wrapper


@dataclass
class TaskRunContext:
    task: NL2QTask
    db_connector: NL2QDBConnector
    usage: Usage
    tools: dict[str, BaseTool]
    trajectories: list[Trajectory] = field(default_factory=list)


class BasicAgentConfig(BaseModel):
    llm: str
    schema_formatter: str
    compress_schema: bool = True
    temperature: float = 0.0
    max_steps: int = 10


if config.max_pydantic_ai_agent_concurrency is not None:
    _pydantic_ai_agent_semaphore = asyncio.Semaphore(config.max_pydantic_ai_agent_concurrency)
else:
    _pydantic_ai_agent_semaphore = None


class ThrottledAgent:
    def __init__(self, agent: Agent):
        self.agent = agent

    @wraps(Agent.run)
    async def run(self, *args, **kwargs):
        semaphore = _pydantic_ai_agent_semaphore
        if semaphore is not None:
            async with semaphore:
                return await self.agent.run(*args, **kwargs)
        return await self.agent.run(*args, **kwargs)
