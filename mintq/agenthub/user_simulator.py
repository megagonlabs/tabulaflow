from contextlib import asynccontextmanager
from typing import AsyncGenerator
import pydantic_ai
from pydantic_ai import Agent, ModelRetry, ToolOutput
import asyncio
import jinja2
from mintq.agenthub.base import (
    UserQuestion,
    UserAnswer,
    UserFreeTextQuestion,
    UserFreeTextAnswer,
    UserMultipleChoiceQuestion,
    UserMultipleChoiceAnswer,
    UserValueQuestion,
    UserValueAnswer,
)
from mintq.schema import AmbigNL2QTask, Usage, Trajectory

USER_SIMULATOR_SYSTEM_PROMPT = """
You are a data analyst trying to solve the following task: {{task}}
Here,{% for ap in ambiguity_points %}
- [{{ap.id}}] "{{ap.phrase}}" should be interpreted as "{{ap.interpretation}}".{% endfor %}

You will be asked a question regarding the possible ambiguities in the task, and you are responsible for providing clarifications.

For "free_text" questions, you must provide a natural language answer in the `answer_text` field. 
- You need to find the ambiguity point in that the question is asking about
  - If there is a match, answer the question using the given information. Do not leak additional information in other ambiguity points. Your answer should be grammatical and linguistically diverse.
  - If there is no match, respond "I cannot answer this question."
- If multiple questions are asked, only answer the first one and say "Please only ask one question at a time."
- If the question is not related to ambiguity clarification, respond "I cannot answer this question."

For "multiple_choice" questions, you must select from the given options and provide the index in the `answer_index` field.
- If none of the options are correct, select the closest option.

For "value" questions, you must provide a value in the `value` field, and an operator selected from the given options in the `operator` field.
- The data type of the value should be the same as the one specified in the question.
- If no valid value is correct, select the closest value.
"""

# - If the question provides multiple options but none of them are correct, respond that none of the options are correct.
# - If there are multiple questions, only answer the first one and say "Please only ask one question at a time."


class UserSimulator:
    def __init__(
        self,
        system_prompt: str,
        llm: str = "openai:gpt-4.1",
        temperature: float = 0.0,
        include_history: bool = True,
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.include_history = include_history

        self.user_agent = Agent[None, str](
            model=self.llm,
            tools=[],
            instructions=self.system_prompt,
            model_settings={"temperature": self.temperature},
        )
        self._message_history: list[pydantic_ai.messages.ModelMessage] = []
        self._usage = Usage.create(llm=self.llm)
        self._lock = asyncio.Lock() if include_history else None

    def usage(self) -> Usage:
        return self._usage

    def trajectory(self) -> Trajectory:
        return Trajectory.from_pydantic_ai_messages(self._message_history, id="TRJY-USER-SIMULATOR")

    @classmethod
    def from_ambig_nl2q_task(
        cls, task: AmbigNL2QTask, llm: str = "openai:gpt-4.1", temperature: float = 0.0, include_history: bool = True
    ) -> "UserSimulator":
        if any(ap.intended_interpretation_idx is None for ap in task.gold_ambiguity_points if ap.type == "finite"):
            raise ValueError("All finite ambiguity points must have an intended interpretation")
        if any(ap.intended_parameter_value is None for ap in task.gold_ambiguity_points if ap.type == "infinite"):
            raise ValueError("All infinite ambiguity points must have an intended parameter value")

        system_prompt = jinja2.Template(USER_SIMULATOR_SYSTEM_PROMPT).render(
            task=task.question,
            ambiguity_points=[
                {
                    "id": ap.id,
                    "phrase": ap.phrase,
                    "interpretation": ap.interpretations[ap.intended_interpretation_idx]  # type: ignore
                    if ap.type == "finite"
                    else f"{ap.intended_parameter_operator} {ap.intended_parameter_value} ({ap.parameter_name})",
                }
                for ap in task.gold_ambiguity_points
            ],
        )
        return cls(system_prompt, llm, temperature, include_history)

    @asynccontextmanager
    async def _lock_message_history_async(self) -> AsyncGenerator[None, None]:
        if self._lock:
            await self._lock.acquire()
            try:
                yield
            finally:
                self._lock.release()
        else:
            yield

    async def ask_free_text_async(self, question: UserFreeTextQuestion) -> UserFreeTextAnswer:
        def answer(relevant_ambig_point_id: str | None, answer_free_text: str) -> UserFreeTextAnswer:
            """
            Args:
                relevant_ambig_point_id: The id (e.g. "A", "B", etc.) of the ambiguity point that the question is asking about. If there is no match, this is None.
                answer_free_text: The answer to the question. Do not include the ambiguity point id in answer_free_text.
            """
            return UserFreeTextAnswer(answer_free_text=answer_free_text)

        async with self._lock_message_history_async():
            result = await self.user_agent.run(
                question.question,
                output_type=ToolOutput(answer, name="answer"),
                message_history=self._message_history if self.include_history else None,
            )
            self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
            self._message_history += result.new_messages()
        return result.output

    async def ask_multiple_choice_async(self, question: UserMultipleChoiceQuestion) -> UserMultipleChoiceAnswer:
        def answer(number: int) -> int:
            if number < 1 or number > len(question.options):
                raise ModelRetry(f"Answer number should be between 1 and {len(question.options)}")
            return number - 1

        async with self._lock_message_history_async():
            result = await self.user_agent.run(
                question.question + "".join([f"\n[{i + 1}] {o}" for i, o in enumerate(question.options)]),
                output_type=ToolOutput(answer, name="answer"),
                message_history=self._message_history if self.include_history else None,
            )
            self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
            self._message_history += result.new_messages()
        return UserMultipleChoiceAnswer(answer_index=result.output)

    async def ask_value_async(self, question: UserValueQuestion) -> UserValueAnswer:
        async with self._lock_message_history_async():
            result = await self.user_agent.run(
                question.model_dump_json(indent=2),
                output_type=ToolOutput(UserValueAnswer, name="answer"),
                message_history=self._message_history if self.include_history else None,
            )
            self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
            self._message_history += result.new_messages()
        return result.output

    async def ask_async(self, question: UserQuestion) -> UserAnswer:
        if question.type == "free_text":
            return await self.ask_free_text_async(question)
        elif question.type == "multiple_choice":
            return await self.ask_multiple_choice_async(question)
        elif question.type == "value":
            return await self.ask_value_async(question)
        else:
            raise ValueError(f"Invalid question type: {question.type}")
