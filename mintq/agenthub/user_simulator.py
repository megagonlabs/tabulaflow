from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pydantic import BaseModel
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
Here,{% for ap in ambig_points %}
- [{{ap.id}}] "{{ap.phrase}}" should be interpreted as "{{ap.interpretation}}".{% endfor %}

You will be asked a question regarding the possible ambiguities in the task, and you are responsible for providing clarifications.

For "free_text" questions, you must identify the relevant ambiguity point id in the `relevant_ambiguity_point_id` field.
- If multiple questions are asked, only identify the relevant ambiguity point for the first question and ignore the rest.
- If there is no matching ambiguity point, reject the question.
- If the question is not related to ambiguity clarification, reject the question.

For "multiple_choice" questions, you must select from the given options and provide the index in the `answer_index` field.
- If none of the options are correct, select the closest option.
- If the question is not related to ambiguity clarification, or cannot be answered using the provided information, reject the question.

For "value" questions, you must provide a value in the `value` field, and an operator selected from the given options in the `operator` field.
- The data type of the value should be the same as the one specified in the question.
- If no valid value is correct, select the closest value.
- If the question is not related to ambiguity clarification, or cannot be answered using the provided information, reject the question.
""".strip()


ANSWER_FREE_TEXT_SYSTEM_PROMPT = """
You are a data analyst trying to solve the following task: {{task}}
Here,{% for ap in ambig_points %}
- [{{ap.id}}] "{{ap.phrase}}" should be interpreted as "{{ap.interpretation}}".{% endfor %}

You will be asked a question regarding the possible ambiguities in the task, and you are responsible for providing clarifications using the above information.
- Only answer what you are asked using only the information provided above. Do not include additional information.
- Do not make assumptions beyond the provided information.
- You should not ask questions.
- If multiple questions are asked, only answer the first one and say "Please only ask one question at a time."
- Your answer should be grammatical and linguistically diverse.
""".strip()


class NLAmbigPoint(BaseModel):
    id: str
    phrase: str
    interpretation: str


class UserSimulatorConfig(BaseModel):
    task: str
    ambig_points: list[NLAmbigPoint]
    llm: str = "openai:gpt-4.1-2025-04-14"
    temperature: float = 0.0
    include_history: bool = True


def reject() -> None:
    return None


class UserSimulator:
    def __init__(self, config: UserSimulatorConfig):
        self.config = config

        system_prompt = jinja2.Template(USER_SIMULATOR_SYSTEM_PROMPT).render(
            task=self.config.task,
            ambig_points=[ap.model_dump() for ap in self.config.ambig_points],
        )

        self.user_agent = Agent(
            model=self.config.llm,
            tools=[],
            instructions=system_prompt,
            model_settings={"temperature": self.config.temperature},
        )
        self._message_history: list[pydantic_ai.messages.ModelMessage] = [
            pydantic_ai.messages.ModelRequest(parts=[], instructions=system_prompt)
        ]
        self._usage = Usage.create(llm=self.config.llm)
        self._lock = asyncio.Lock() if self.config.include_history else None

    def usage(self) -> Usage:
        return self._usage

    def trajectory(self) -> Trajectory:
        return Trajectory.from_pydantic_ai_messages(self._message_history, id="TRJY-USER-SIMULATOR")

    @classmethod
    def from_ambig_nl2q_task(
        cls,
        task: AmbigNL2QTask,
        llm: str = "openai:gpt-4.1-2025-04-14",
        temperature: float = 0.0,
        include_history: bool = True,
    ) -> "UserSimulator":
        if any(ap.intended_interpretation_idx is None for ap in task.gold_ambiguity_points if ap.type == "finite"):
            raise ValueError("All finite ambiguity points must have an intended interpretation")
        if any(ap.intended_parameter_value is None for ap in task.gold_ambiguity_points if ap.type == "infinite"):
            raise ValueError("All infinite ambiguity points must have an intended parameter value")

        ambig_points = [
            NLAmbigPoint(
                id=ap.id,
                phrase=ap.phrase,
                interpretation=ap.interpretations[ap.intended_interpretation_idx]  # type: ignore
                if ap.type == "finite"
                else f"{ap.intended_parameter_operator} {ap.intended_parameter_value} ({ap.parameter_name})",
            )
            for ap in task.gold_ambiguity_points
        ]

        config = UserSimulatorConfig(
            task=task.question,
            ambig_points=ambig_points,
            llm=llm,
            temperature=temperature,
            include_history=include_history,
        )
        return cls(config)

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

    async def ask_free_text_async(self, question: UserFreeTextQuestion) -> UserFreeTextAnswer | None:
        def return_relevant_ambig_point(ambig_point_id: str) -> str:
            """
            Args:
                ambig_point_id: The id (e.g. "A", "B", etc.) of the ambiguity point that the question is asking about.
            """
            return ambig_point_id

        async with self._lock_message_history_async():
            result0 = await self.user_agent.run(  # type: ignore
                question.question,
                output_type=[
                    ToolOutput(return_relevant_ambig_point, name="return_relevant_ambig_point"),
                    ToolOutput(reject, name="reject"),
                ],
                message_history=self._message_history if self.config.include_history else None,
            )
            self._usage += Usage.from_pydantic_ai_usage(result0.usage(), self.config.llm)
            self._message_history += result0.new_messages()

            relevant_ambig_point_id = result0.output

            if relevant_ambig_point_id is None or not any(
                ap.id == relevant_ambig_point_id for ap in self.config.ambig_points
            ):
                return None

            relevant_ambig_point = next(ap for ap in self.config.ambig_points if ap.id == relevant_ambig_point_id)
            system_prompt = jinja2.Template(ANSWER_FREE_TEXT_SYSTEM_PROMPT).render(
                task=self.config.task,
                ambig_points=[relevant_ambig_point.model_dump()],
            )
            answer_agent = Agent(
                model=self.config.llm,
                instructions=system_prompt,
                model_settings={"temperature": self.config.temperature},
            )
            result = await answer_agent.run(
                question.question, output_type=ToolOutput(UserFreeTextAnswer, name="answer")
            )
            self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
            self._message_history += result.new_messages()[1:]  # The question is already added in the first step
        return result.output

    async def ask_multiple_choice_async(self, question: UserMultipleChoiceQuestion) -> UserMultipleChoiceAnswer | None:
        def answer(number: int) -> UserMultipleChoiceAnswer:
            if number < 1 or number > len(question.options):
                raise ModelRetry(f"Answer number should be between 1 and {len(question.options)}")
            return UserMultipleChoiceAnswer(answer_index=number - 1)

        async with self._lock_message_history_async():
            result = await self.user_agent.run(  # type: ignore
                question.question + "".join([f"\n[{i + 1}] {o}" for i, o in enumerate(question.options)]),
                output_type=[ToolOutput(answer, name="answer"), ToolOutput(reject, name="reject")],
                message_history=self._message_history if self.config.include_history else None,
            )
            self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
            self._message_history += result.new_messages()
        return result.output  # type: ignore

    async def ask_value_async(self, question: UserValueQuestion) -> UserValueAnswer | None:
        async with self._lock_message_history_async():
            result = await self.user_agent.run(  # type: ignore
                question.model_dump_json(indent=2),
                output_type=[ToolOutput(UserValueAnswer, name="answer"), ToolOutput(reject, name="reject")],
                message_history=self._message_history if self.config.include_history else None,
            )
            self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
            self._message_history += result.new_messages()
        return result.output  # type: ignore

    async def ask_async(self, question: UserQuestion) -> UserAnswer | None:
        if question.type == "free_text":
            return await self.ask_free_text_async(question)
        elif question.type == "multiple_choice":
            return await self.ask_multiple_choice_async(question)
        elif question.type == "value":
            return await self.ask_value_async(question)
        else:
            raise ValueError(f"Invalid question type: {question.type}")
