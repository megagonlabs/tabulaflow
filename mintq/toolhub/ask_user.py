from dataclasses import dataclass, field
from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.agenthub.user_simulator import UserSimulator


class AskUserToolMetrics(BaseModel):
    pass


@dataclass
class AskUserTool:
    name: ClassVar[str] = "ask_user"
    user_simulator: UserSimulator
    metrics_: AskUserToolMetrics = field(default_factory=AskUserToolMetrics)

    async def __call__(self, question: str) -> str:
        """
        Ask the user a question and get a response.

        Args:
            question: The question to ask the user.
        """
        response = await self.user_simulator.ask_async(question)
        return response

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
