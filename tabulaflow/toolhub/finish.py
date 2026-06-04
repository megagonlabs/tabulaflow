from typing import ClassVar
from pydantic_ai import RunContext, ModelRetry, ToolOutput
from pydantic import BaseModel
from tabulaflow.core.types import Trajectory


class FinishToolMetrics(BaseModel):
    num_calls: int = 0
    error_no_query_executed: int = 0


class FinishTool:
    name: ClassVar = "finish"

    def __init__(self) -> None:
        self._metrics = FinishToolMetrics()

    def __call__(self, trajectory: Trajectory) -> None:
        """
        Finish the task. The last executed query will be considered as the final answer. No parameters needed.

        Example:
        ```python
        finish()
        ```
        """
        self._metrics.num_calls += 1

        for msg in trajectory.messages[::-1]:
            if msg.role == "assistant":
                for tool_call in msg.tool_calls[::-1]:
                    if tool_call.name == "run_query" and tool_call.arguments is not None:
                        return None
        self._metrics.error_no_query_executed += 1
        raise ValueError(
            "No query has been executed, you need to call the `run_query` tool at least once before finishing"
        )

    def as_pydantic_ai_tool(self) -> ToolOutput[None]:
        def finish(ctx: RunContext) -> None:
            trajectory = Trajectory.from_pydantic_ai_messages(ctx.messages)
            try:
                return self(trajectory)
            except ValueError as e:
                self._metrics.error_no_query_executed += 1
                raise ModelRetry(str(e))

        finish.__doc__ = self.__call__.__doc__
        return ToolOutput(finish, name="finish")

    def metrics(self) -> FinishToolMetrics:
        return self._metrics
