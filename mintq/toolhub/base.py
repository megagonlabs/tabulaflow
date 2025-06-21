from typing import ClassVar, Protocol, Any
from pydantic_ai import Tool


class BaseTool(Protocol):
    name: ClassVar[str]

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

    def as_pydantic_ai_tool(self) -> Tool: ...
