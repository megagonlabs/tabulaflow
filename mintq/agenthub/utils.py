from typing import Any, Callable, Literal
from functools import partial, wraps
from dataclasses import dataclass

from opentelemetry import trace
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from pydantic import BaseModel
from mintq.schema import NL2QTask, Usage, Trajectory, SQLSchema
from mintq.config import mintq_config
from mintq.db_connector import NL2QDBConnector
from mintq.toolhub import BaseTool
from mintq.formatters.base import BaseSQLSchemaFormatter


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
    if not mintq_config.instrument_enabled:
        return predict_async_fn

    @wraps(predict_async_fn)
    async def wrapper(self: Any, task: NL2QTask, *args: Any, **kwargs: Any) -> Any:
        from mintq import __version__

        tracer_provider = trace.get_tracer_provider()
        tracer = tracer_provider.get_tracer("mintq", __version__)

        current_span = trace.get_current_span()

        if current_span and current_span.get_span_context().is_valid:
            # Already inside a span, do not start a new span
            return await predict_async_fn(self, task, *args, **kwargs)

        span_name = f"qid={task.qid}".strip()
        if mintq_config.instrument_prefix:
            span_name = f"{mintq_config.instrument_prefix} | {span_name}"
        with tracer.start_as_current_span(span_name):
            return await predict_async_fn(self, task, *args, **kwargs)

    return wrapper


@dataclass
class TaskRunContext:
    task: NL2QTask
    db_connector: NL2QDBConnector
    preprocessed_schema: SQLSchema
    schema_formatter: BaseSQLSchemaFormatter
    usage: Usage
    tools: dict[str, BaseTool]
    trajectories: list[Trajectory]


class BasicAgentConfig(BaseModel):
    llm: str
    schema_formatter: str = "sql_ddl"
    compress_schema: bool = True
    temperature: float | None = None
    max_steps: int = 20
    formatter_max_total_columns: int | None = 5000
    use_column_description: bool = True
    openai_reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"] | None = None
    openai_reasoning_summary: Literal["detailed", "concise"] | None = None
    openai_service_tier: Literal["auto", "default", "flex", "priority"] | None = None

    def to_formatter_kwargs(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        if self.formatter_max_total_columns is not None:
            res["max_total_columns"] = self.formatter_max_total_columns
        return res

    def to_model_settings(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        if self.temperature is not None:
            res["temperature"] = self.temperature
        if self.openai_reasoning_effort is not None:
            res["openai_reasoning_effort"] = self.openai_reasoning_effort
        if self.openai_reasoning_summary is not None:
            res["openai_reasoning_summary"] = self.openai_reasoning_summary
        if self.openai_service_tier is not None:
            res["openai_service_tier"] = self.openai_service_tier
        return res
