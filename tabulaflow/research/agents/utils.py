"""Shared configuration, context, and helpers for research agents."""

from typing import Any, Literal, overload
from functools import partial
from dataclasses import dataclass
import re

from pydantic_ai import RunContext
from pydantic_ai.capabilities import ProcessHistory
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from pydantic import BaseModel, Field
from tabulaflow.core import DataSourceSchema, SQLSchema
from tabulaflow.agents.trace import Usage, Trajectory
from tabulaflow.research.types import NL2QTask, SimpleNL2QTask
from tabulaflow.data import DataConnector
from tabulaflow.agents.llm import ReasoningLevel, ServiceTier, make_model_settings
from tabulaflow.agents.tools import AgentTool
from tabulaflow.output.formatting import PropertyGraphSchemaFormatter, SQLSchemaFormatter, get_schema_formatter_class


def format_question(task: SimpleNL2QTask) -> str:
    """Combine a task's question with its question-specific instructions."""
    if task.question_instructions:
        return f"{task.question}\n{task.question_instructions}"
    return task.question


def extract_code(response: str) -> str:
    match = re.search(r"```(?:([\w+-]+))?\n([\s\S]*?)\n```", response)
    return match.group(2).strip() if match else response.strip()


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


def get_max_steps_capability(max_steps: int) -> ProcessHistory[Any]:
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    return ProcessHistory(partial(max_steps_processor, max_steps=max_steps))


@dataclass
class TaskRunContext:
    task: NL2QTask
    db_connector: DataConnector
    preprocessed_schema: SQLSchema
    schema_formatter: SQLSchemaFormatter
    usage: Usage
    tools: dict[str, AgentTool]
    trajectories: list[Trajectory]


class BasicAgentConfig(BaseModel):
    llm: str = "openai:gpt-5-mini"
    schema_formatter: str | None = None
    compact_table_families: bool = True
    temperature: float | None = None
    max_steps: int = Field(default=50, ge=1)
    formatter_max_total_columns: int | None = 5000
    use_column_descriptions: bool = True
    reasoning: ReasoningLevel | None = None
    service_tier: ServiceTier | None = None

    @overload
    def create_schema_formatter(self, kind: Literal["sql"]) -> SQLSchemaFormatter: ...

    @overload
    def create_schema_formatter(self, kind: Literal["property_graph"]) -> PropertyGraphSchemaFormatter: ...

    def create_schema_formatter(
        self, kind: Literal["sql", "property_graph"]
    ) -> SQLSchemaFormatter | PropertyGraphSchemaFormatter:
        """Create a compatible formatter with this agent's schema options."""
        if kind == "sql":
            kwargs: dict[str, Any] = {"compact_table_families": self.compact_table_families}
            if self.formatter_max_total_columns is not None:
                kwargs["max_total_columns"] = self.formatter_max_total_columns
            return get_schema_formatter_class(kind, self.schema_formatter)(**kwargs)
        if kind == "property_graph":
            return get_schema_formatter_class(kind, self.schema_formatter)()
        raise TypeError(f"Unsupported research schema kind: {kind!r}")

    def to_model_settings(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        if self.temperature is not None:
            res["temperature"] = self.temperature
        res.update(
            make_model_settings(
                model=self.llm,
                reasoning=self.reasoning,
                service_tier=self.service_tier,
            )
        )
        return res


def format_schema_for_prompt(schema: DataSourceSchema, config: BasicAgentConfig) -> str:
    """Render a research prompt's schema using the agent's configured formatter."""
    if schema.kind == "sql":
        return config.create_schema_formatter(schema.kind).format(
            schema, include_descriptions=config.use_column_descriptions
        )
    if schema.kind == "property_graph":
        return config.create_schema_formatter(schema.kind).format(schema)
    raise TypeError(f"Unsupported research schema kind: {schema.kind!r}")
