from typing import ClassVar, Protocol, Any, TypeAlias
from pydantic_ai import Tool, ToolOutput
from pydantic import BaseModel


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


class BaseToolset(Protocol):
    """Protocol for stateful tools that expose multiple LLM-facing actions
    sharing one underlying instance.

    Use when several actions operate on per-instance state and must be
    registered together (e.g. a browser tool whose navigate/click/type
    actions share a Page and snapshot).

    Attributes:
        name: Group identifier for this toolset (not directly exposed to
            the LLM; individual action tools have their own names).
    """

    name: ClassVar[str]

    def as_pydantic_ai_tools(self) -> list[Tool | ToolOutput[Any]]: ...

    def metrics(self) -> BaseToolMetrics: ...
