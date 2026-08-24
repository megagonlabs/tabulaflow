import copy
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from typing import Any, ClassVar, Protocol, TypeAlias, TypeVar, runtime_checkable

from pydantic import BaseModel
from pydantic_ai import RunContext, Tool, ToolOutput
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import ToolDefinition, ToolPrepareFunc


BaseToolMetrics: TypeAlias = BaseModel

_M = TypeVar("_M", bound=BaseModel)


def _omit_tool_parameters(*names: str) -> ToolPrepareFunc[object] | None:
    """Return a tool-definition hook that hides selected function parameters."""
    if not names:
        return None
    omitted = frozenset(names)

    def prepare(_ctx: RunContext[object], tool_def: ToolDefinition) -> ToolDefinition:
        schema = copy.deepcopy(tool_def.parameters_json_schema)
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for name in omitted:
                properties.pop(name, None)
        required = schema.get("required")
        if isinstance(required, list):
            schema["required"] = [name for name in required if name not in omitted]
        return replace(tool_def, parameters_json_schema=schema)

    return prepare


def sum_tool_metrics(metrics_iter: Iterable[_M], cls: type[_M]) -> _M:
    """Sum numeric fields across multiple metrics instances.

    Args:
        metrics_iter: Iterable of metrics objects to aggregate.
        cls: The metrics class to instantiate for the result.
    """
    totals: dict[str, int | float] = {}
    for metrics in metrics_iter:
        for field_name in metrics.model_fields:
            value = getattr(metrics, field_name)
            if isinstance(value, (int, float)):
                totals[field_name] = totals.get(field_name, 0) + value
    return cls(**totals)


class BaseTool(Protocol):
    """Protocol for single-action agent tools.

    Attributes:
        name: Identifier exposed to the LLM as the tool's function name.
    """

    name: ClassVar[str]

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

    def as_pydantic_ai_tool(self) -> Tool | ToolOutput[Any]: ...

    def metrics(self) -> BaseToolMetrics: ...


@runtime_checkable
class LLMProfileTool(Protocol):
    """Tool with an internal LLM profile supplied by its host."""

    def apply_llm_profile(self, *, llm: str, model_settings: ModelSettings | None) -> None: ...


@dataclass(frozen=True)
class ToolProgressUpdate:
    """A progress tick from a long-running tool.

    Attributes:
        completed: Units of work finished so far.
        total: Denominator, or ``None`` for an open-ended running count.
        unit: Optional noun for the count (e.g. ``"rows"``).
        stage: Optional named phase within the tool (e.g. ``"canonicalize"``).
        tool_call_id: Routes the tick to the right step when several tool calls
            run concurrently.
    """

    completed: int
    total: int | None = None
    unit: str | None = None
    stage: str | None = None
    tool_call_id: str | None = None


@runtime_checkable
class ProgressReportingTool(Protocol):
    """Tool that reports progress ticks through its ``on_progress`` slot."""

    on_progress: Callable[[ToolProgressUpdate], None] | None


@dataclass(frozen=True)
class ToolCallOutcome:
    """Facts about one completed tool call, for the host's display.

    Attached as ``pydantic_ai.ToolReturn.metadata`` by the tool's LLM-facing
    entrypoints, so it rides the call's own return — never sent to the model.

    Attributes:
        count: Units of work the call returned (e.g. result rows).
        unit: Noun for the count (e.g. ``"rows"``, ``"columns"``).
        error: Whether the call failed.
    """

    count: int | None = None
    unit: str | None = None
    error: bool = False
