from typing import ClassVar, Callable
from pydantic_ai import RunContext, ModelRetry
import json
from dataclasses import field, dataclass
from collections import defaultdict


@dataclass
class FinishTool:
    name: ClassVar[str] = "finish"
    metrics_: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def __call__(self) -> None:
        pass

    def as_pydantic_ai_tool(self) -> Callable[[RunContext], str]:
        def finish(ctx: RunContext) -> str:
            """
            Finish the task and return the last executed query as final answer.
            """
            for msg in ctx.messages[::-1]:
                if msg.kind == "response":
                    for part in msg.parts[::-1]:
                        if part.part_kind == "tool-call" and part.tool_name == "run_query":
                            if isinstance(part.args, str):
                                return json.loads(part.args)["query"]  # type: ignore
                            elif isinstance(part.args, dict):
                                return part.args["query"]  # type: ignore
                            else:
                                raise ValueError(f"Unexpected tool call argument type: {type(part.args)}")
            self.metrics_["finish_no_query_executed"] += 1
            raise ModelRetry("No query has been executed, you cannot finish yet")

        return finish
