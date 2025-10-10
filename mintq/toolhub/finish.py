from typing import ClassVar
from pydantic_ai import RunContext, ModelRetry, ToolOutput
from pydantic import BaseModel
from mintq.schema import Trajectory, PredQuery


class FinishToolMetrics(BaseModel):
    error_no_query_executed: int = 0


class FinishTool:
    name: ClassVar = "finish"

    def __init__(self) -> None:
        self._metrics = FinishToolMetrics()

    def __call__(self, trajectory: Trajectory) -> PredQuery:
        """
        Finish the task. The last executed query will be considered as the final answer. No parameters needed.
        """
        for msg in trajectory.messages[::-1]:
            if msg.role == "assistant":
                for tool_call in msg.tool_calls[::-1]:
                    if tool_call.name == "run_query" and tool_call.arguments is not None:
                        query = tool_call.arguments["query"]
                        parameters = tool_call.arguments.get("parameters", {})
                        return PredQuery(
                            query=query, parameter_names=list(parameters.keys()), parameter_values=parameters
                        )
        self._metrics.error_no_query_executed += 1
        raise ValueError("No query has been executed, you cannot finish yet")

    def as_pydantic_ai_tool(self) -> ToolOutput[PredQuery]:
        def finish(ctx: RunContext) -> PredQuery:
            trajectory = Trajectory.from_pydantic_ai_messages(ctx.messages)
            try:
                return self(trajectory)
            except ValueError:
                self._metrics.error_no_query_executed += 1
                raise ModelRetry("No query has been executed, you cannot finish yet")

        finish.__doc__ = self.__call__.__doc__
        return ToolOutput(finish, name="finish")

    def get_metrics(self) -> FinishToolMetrics:
        return self._metrics
