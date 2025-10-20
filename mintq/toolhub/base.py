from typing import ClassVar, Protocol, Any, TypeAlias
from pydantic_ai import Tool, ToolOutput
from pydantic import BaseModel


BaseToolMetrics: TypeAlias = BaseModel


class BaseTool(Protocol):
    name: ClassVar[str]

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

    def as_pydantic_ai_tool(self) -> Tool | ToolOutput[Any]: ...

    def metrics(self) -> BaseToolMetrics: ...
