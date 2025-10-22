from typing import ClassVar
from pydantic_ai import RunContext, ModelRetry, ToolOutput
from pydantic import BaseModel
from mintq.schema import Trajectory, PredQuery


class FinishToolMetrics(BaseModel):
    num_calls: int = 0
    error_no_query_executed: int = 0


class FinishTool:
    name: ClassVar = "finish"

    def __init__(self) -> None:
        self._metrics = FinishToolMetrics()

    def __call__(self, trajectory: Trajectory) -> PredQuery:
        """
        Finish the task. The last executed query will be considered as the final answer. No parameters needed.
        """
        self._metrics.num_calls += 1

        for msg in trajectory.messages[::-1]:
            if msg.role == "assistant":
                for tool_call in msg.tool_calls[::-1]:
                    if tool_call.name == "run_query" and tool_call.arguments is not None:
                        query = tool_call.arguments["query"]
                        parameters = tool_call.arguments.get("parameters", [])
                        parameter_values = {p["parameter_name"]: p["parameter_value"] for p in parameters}
                        return PredQuery(
                            query=query,
                            parameter_names=list(parameter_values.keys()),
                            parameter_values=parameter_values,
                        )
        self._metrics.error_no_query_executed += 1
        raise ValueError(
            "No query has been executed, you need to call the `run_query` tool at least once before finishing"
        )

    def as_pydantic_ai_tool(self) -> ToolOutput[PredQuery]:
        def finish(ctx: RunContext) -> PredQuery:
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
