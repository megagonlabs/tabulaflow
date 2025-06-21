from typing import ClassVar, Protocol, Any, Callable, TypeAlias
from pydantic_ai import Tool


PydanticAIOutputTool: TypeAlias = Callable[..., Any]


class BaseTool(Protocol):
    name: ClassVar[str]

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

    def as_pydantic_ai_tool(self) -> Tool | PydanticAIOutputTool: ...
