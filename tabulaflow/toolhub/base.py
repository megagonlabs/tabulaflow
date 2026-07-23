from collections.abc import Iterable
from typing import Any, ClassVar, Protocol, TypeAlias, TypeVar

from pydantic import BaseModel
from pydantic_ai import Tool, ToolOutput
from pydantic_ai.settings import ModelSettings


BaseToolMetrics: TypeAlias = BaseModel

_M = TypeVar("_M", bound=BaseModel)


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


class LLMProfileTool(Protocol):
    """Tool with an internal LLM profile supplied by its host."""

    def apply_llm_profile(self, *, llm: str, model_settings: ModelSettings | None) -> None: ...
