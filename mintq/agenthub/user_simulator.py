from typing import Any, Literal
from pydantic import BaseModel
import pydantic_ai
from pydantic_ai import Agent, ToolOutput
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

CONTROLL_AGENT_SYSTEM_PROMPT = """
You are a data analyst trying to solve the following task: {{task}}
Here,{% for ap in ambig_points %}
- [{{ap.id}}] "{{ap.phrase}}" should be interpreted as "{{ap.interpretation}}".{% endfor %}

You will be asked a question regarding the possible ambiguities in the task, you must identify the relevant ambiguity point id in the `relevant_ambiguity_point_id` field.
- If there is no matching ambiguity point, set the `relevant_ambiguity_point_id` to None.
- If multiple questions are asked, only identify the relevant ambiguity point for the first question and ignore the rest.
- If the question is not related to ambiguity clarification, set the `relevant_ambiguity_point_id` to None.
""".strip()


ANSWER_AGENT_SYSTEM_PROMPT = """
You are a data analyst trying to solve the following task: {{task}}
Here,{% for ap in ambig_points %}
- [{{ap.id}}] "{{ap.phrase}}" should be interpreted as "{{ap.interpretation}}".{% endfor %}

You will be asked a question regarding the possible ambiguities in the task, and you are responsible for providing clarifications using the above information.

For "free_text" questions, you need to provide a free-text answer:
- If multiple questions are asked, only answer the first question and say "Please only ask one question at a time."
- Only answer what you are asked using only the information provided above. Do not include additional information.
- Do not make assumptions beyond the provided information.
- You should not ask questions.
- Your answer should be grammatical and linguistically diverse.

For "multiple_choice" questions, you need to select from the given options:
- If none of the options are correct, set answer number to null. 

For "value" questions, you need to select a value as well as an operator from the given options:
- The data type of the value should be consistent with the one specified in the question.
- If no valid value or no valid operator is correct, set both fields to null.
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


class UserSimulator:
    def __init__(self, config: UserSimulatorConfig):
        self.config = config

        control_agent_system_prompt = jinja2.Template(CONTROLL_AGENT_SYSTEM_PROMPT).render(
            task=self.config.task,
            ambig_points=[ap.model_dump() for ap in self.config.ambig_points],
        )

        self.control_agent = Agent(
            model=self.config.llm,
            tools=[],
            instructions=control_agent_system_prompt,
            model_settings={"temperature": self.config.temperature},
        )
        self._message_history: list[pydantic_ai.messages.ModelMessage] = []
        self._usage = Usage.create(llm=self.config.llm)
        self._user_effort = 0
        self._lock = asyncio.Lock()

    def usage(self) -> Usage:
        return self._usage

    def trajectory(self) -> Trajectory:
        return Trajectory.from_pydantic_ai_messages(self._message_history, id="TRJY-USER-SIMULATOR")

    def user_effort(self) -> int:
        return self._user_effort

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

    async def _identify_relevant_ambig_point_id_async(self, question_str: str) -> NLAmbigPoint | None:
        def identify(relevant_ambig_point_id: str | None) -> str | None:
            """
            Args:
                relevant_ambig_point_id: The id (e.g. "A", "B", etc.) of the ambiguity point that the question is asking about. If there is no match, set this to null.
            """
            return relevant_ambig_point_id

        result = await self.control_agent.run(  # type: ignore
            question_str,
            output_type=[ToolOutput(identify, name="identify")],
            message_history=self._message_history if self.config.include_history else None,
        )
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        self._message_history += result.new_messages()
        relevant_ambig_point_id = result.output
        if relevant_ambig_point_id is None:
            return None
        return next((ap for ap in self.config.ambig_points if ap.id == relevant_ambig_point_id), None)

    async def _run_async(self, question_str: str, output_type_or_func: Any) -> UserAnswer | None:
        async with self._lock:
            relevant_ambig_point = await self._identify_relevant_ambig_point_id_async(question_str)
            if relevant_ambig_point is None:
                return None

            answer_agent_system_prompt = jinja2.Template(ANSWER_AGENT_SYSTEM_PROMPT).render(
                task=self.config.task,
                ambig_points=[relevant_ambig_point.model_dump()],
            )
            answer_agent: Agent[None, UserAnswer | None] = Agent(
                model=self.config.llm,
                instructions=answer_agent_system_prompt,
                output_type=ToolOutput(output_type_or_func, name="answer"),
                model_settings={"temperature": self.config.temperature},
            )

            result = await answer_agent.run(question_str)
            usage = Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
            self._usage += usage
            self._user_effort += usage.output_tokens
            self._message_history += result.new_messages()[1:]
        return result.output

    async def ask_free_text_async(self, question: UserFreeTextQuestion) -> UserFreeTextAnswer | None:
        return await self._run_async(question.question, UserFreeTextAnswer)  # type: ignore

    async def ask_multiple_choice_async(self, question: UserMultipleChoiceQuestion) -> UserMultipleChoiceAnswer | None:
        def answer(number: int | None) -> UserMultipleChoiceAnswer | None:
            """
            Args:
                number: The number of the selected option. If none of the options are correct, set this to null.
            """
            if number is None or number < 1 or number > len(question.options):
                return None
            return UserMultipleChoiceAnswer(answer_index=number - 1)

        question_str = question.question + "".join([f"\n[{i + 1}] {o}" for i, o in enumerate(question.options)])
        return await self._run_async(question_str, answer)  # type: ignore

    async def ask_value_async(self, question: UserValueQuestion) -> UserValueAnswer | None:
        def answer(
            operator: Literal["<", ">", "<=", ">=", "=", "<>"] | None, value: int | float | str | None
        ) -> UserValueAnswer | None:
            """
            Args:
                operator: The operator of the value to use in "<expression> <operator> <value>". If none of the operators are correct, set this to null.
                value: The intended value of the parameter. If no valid value is correct, set this to null.
            """
            if operator is None or value is None:
                return None
            return UserValueAnswer(operator=operator, value=value)

        question_str = question.model_dump_json(indent=2)
        return await self._run_async(question_str, answer)  # type: ignore

    async def ask_async(self, question: UserQuestion) -> UserAnswer | None:
        if question.type == "free_text":
            return await self.ask_free_text_async(question)
        elif question.type == "multiple_choice":
            return await self.ask_multiple_choice_async(question)
        elif question.type == "value":
            return await self.ask_value_async(question)
        else:
            raise ValueError(f"Invalid question type: {question.type}")
