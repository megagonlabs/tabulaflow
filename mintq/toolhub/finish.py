from typing import ClassVar, Callable
from pydantic_ai import RunContext, ModelRetry
from dataclasses import field, dataclass
from pydantic import BaseModel
from mintq.pydantic_ai_utils import pydantic_ai_messages_to_trajectory
from mintq.schema import Trajectory


class FinishToolMetrics(BaseModel):
    error_no_query_executed: int = 0


@dataclass
class FinishTool:
    name: ClassVar[str] = "finish"
    metrics_: FinishToolMetrics = field(default_factory=FinishToolMetrics)

    def __call__(self, trajectory: Trajectory) -> str:
        """
        Finish the task and return the last executed query as final answer.
        """
        for msg in trajectory.messages[::-1]:
            if msg.role == "assistant":
                for tool_call in msg.tool_calls[::-1]:
                    if tool_call.name == "run_query":
                        return tool_call.arguments["query"]  # type: ignore
        self.metrics_.error_no_query_executed += 1
        raise ValueError("No query has been executed, you cannot finish yet")

    def as_pydantic_ai_tool(self) -> Callable[[RunContext], str]:
        def finish(ctx: RunContext) -> str:
            trajectory = pydantic_ai_messages_to_trajectory(ctx.messages)
            try:
                return self(trajectory)
            except ValueError:
                self.metrics_.error_no_query_executed += 1
                raise ModelRetry("No query has been executed, you cannot finish yet")

        finish.__doc__ = self.__call__.__doc__
        return finish
