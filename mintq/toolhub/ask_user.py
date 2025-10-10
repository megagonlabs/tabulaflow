from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.agenthub.base import BaseUserSimulator, UserFreeTextQuestion


class AskUserToolMetrics(BaseModel):
    user_refused_to_answer: int = 0


class AskUserTool:
    name: ClassVar[str] = "ask_user"

    def __init__(self, user_simulator: BaseUserSimulator):
        self.user_simulator = user_simulator
        self._metrics = AskUserToolMetrics()

    async def __call__(self, question: str) -> str:
        """
        Ask the user a question and get a response.

        Args:
            question: The question to ask the user.
        """
        response = await self.user_simulator.ask_async(UserFreeTextQuestion(question=question))
        if "cannot answer" in response.answer_text.lower():
            self._metrics.user_refused_to_answer += 1
        return response.answer_text

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def get_metrics(self) -> AskUserToolMetrics:
        return self._metrics
