from typing import Any, ClassVar, Protocol, TypeAlias

from pydantic import BaseModel
from pydantic_ai import Tool, ToolOutput


BaseToolMetrics: TypeAlias = BaseModel


class BaseTool(Protocol):
    """Protocol for single-action agent tools.

    Attributes:
        name: Identifier exposed to the LLM as the tool's function name.
    """

    name: ClassVar[str]

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

    def as_pydantic_ai_tool(self) -> Tool | ToolOutput[Any]: ...

    def metrics(self) -> BaseToolMetrics: ...
