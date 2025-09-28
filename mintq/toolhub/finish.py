from typing import ClassVar, Callable
from pydantic_ai import RunContext, ModelRetry
from pydantic import BaseModel
from mintq.schema import Trajectory


class FinishToolMetrics(BaseModel):
    error_no_query_executed: int = 0


class FinishTool:
    name: ClassVar = "finish"

    def __init__(self) -> None:
        self._metrics = FinishToolMetrics()

    def __call__(self, trajectory: Trajectory) -> str:
        """
        Finish the task and return the last executed query as final answer.
        """
        for msg in trajectory.messages[::-1]:
            if msg.role == "assistant":
                for tool_call in msg.tool_calls[::-1]:
                    if tool_call.name == "run_query":
                        return tool_call.arguments["query"]  # type: ignore
        self._metrics.error_no_query_executed += 1
        raise ValueError("No query has been executed, you cannot finish yet")

    def as_pydantic_ai_tool(self) -> Callable[[RunContext], str]:
        def finish(ctx: RunContext) -> str:
            trajectory = Trajectory.from_pydantic_ai_messages(ctx.messages)
            try:
                return self(trajectory)
            except ValueError:
                self._metrics.error_no_query_executed += 1
                raise ModelRetry("No query has been executed, you cannot finish yet")

        finish.__doc__ = self.__call__.__doc__
        return finish

    def get_metrics(self) -> FinishToolMetrics:
        return self._metrics
