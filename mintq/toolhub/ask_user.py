from typing import ClassVar
from pydantic_ai import Tool, RunContext, ToolDefinition
from pydantic import BaseModel
from mintq.agenthub.base import BaseUserSimulator, UserFreeTextQuestion


class AskUserToolMetrics(BaseModel):
    num_calls: int = 0
    user_refused_to_answer: int = 0


class AskUserTool:
    name: ClassVar = "ask_user"

    def __init__(self, user_simulator: BaseUserSimulator, patience: int | None = None):
        self.user_simulator = user_simulator
        self.patience = patience
        self._metrics = AskUserToolMetrics()

    async def __call__(self, question: str) -> str:
        """
        Ask the user a question and get a response.

        Args:
            question: The question to ask the user.
        """
        self._metrics.num_calls += 1

        response = await self.user_simulator.ask_async(UserFreeTextQuestion(question=question))
        if "cannot answer" in response.answer_free_text.lower():
            self._metrics.user_refused_to_answer += 1
        return response.answer_free_text

    async def _pydantic_ai_prepare(self, ctx: RunContext, tool_def: ToolDefinition) -> ToolDefinition | None:
        """After the patience limit is reached, this tool will not be provided to the LLM anymore."""
        return None if self.patience is not None and self._metrics.num_calls >= self.patience else tool_def

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name, prepare=self._pydantic_ai_prepare)

    def metrics(self) -> AskUserToolMetrics:
        return self._metrics
