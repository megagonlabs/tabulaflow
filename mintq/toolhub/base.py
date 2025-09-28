from typing import ClassVar, Protocol, Any, Callable, TypeAlias
from pydantic_ai import Tool
from pydantic import BaseModel


PydanticAIOutputTool: TypeAlias = Callable[..., Any]


BaseToolMetrics: TypeAlias = BaseModel


class BaseTool(Protocol):
    name: ClassVar[str]

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

    def as_pydantic_ai_tool(self) -> Tool | PydanticAIOutputTool: ...

    def get_metrics(self) -> BaseToolMetrics: ...
