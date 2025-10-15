from pydantic_ai import Agent, ModelRetry
import jinja2
from functools import partial
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
- "{{ap.phrase}}" should be interpreted as "{{ap.interpretation}}".{% endfor %}

You will be asked a question regarding the possible ambiguities in the task, and you are responsible for providing clarifications.


For "free_text" questions, you must provide a natural language answer in the `answer_text` field. 
- Only answer what you are asked, do not provide additional information even if it is related.
- If the question is not related to ambiguity clarification, respond "I cannot answer this question."
- If the question cannot be answered based on the provided information, respond "I cannot answer this question."
- Your answer should be grammatical and linguistically diverse.

For "multiple_choice" questions, you must select from the given options and provide the index in the `answer_index` field.
- If none of the options are correct, select the closest option.

For "value" questions, you must provide a value in the `value` field, and an operator selected from the given options in the `operator` field.
- The data type of the value should be the same as the one specified in the question.
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
        self._message_history = []
        self._usage = Usage.create(llm=self.llm)

    def usage(self) -> Usage:
        return self._usage

    def trajectory(self) -> Trajectory:
        return Trajectory.from_pydantic_ai_messages(self._message_history, id="TRJY-USER-SIMULATOR")

    @classmethod
    def from_ambig_nl2q_task(
        cls, task: AmbigNL2QTask, llm: str = "openai:gpt-4.1", temperature: float = 0.0
    ) -> "UserSimulator":
        if any(ap.intended_interpretation_idx is None for ap in task.gold_ambiguity_points if ap.type == "finite"):
            raise ValueError("All finite ambiguity points must have an intended interpretation")
        if any(ap.intended_parameter_value is None for ap in task.gold_ambiguity_points if ap.type == "infinite"):
            raise ValueError("All infinite ambiguity points must have an intended parameter value")

        system_prompt = jinja2.Template(USER_SIMULATOR_SYSTEM_PROMPT).render(
            task=task.question,
            ambiguity_points=[
                {
                    "phrase": ap.phrase,
                    "interpretation": ap.interpretations[ap.intended_interpretation_idx]  # type: ignore
                    if ap.type == "finite"
                    else f"{ap.intended_parameter_operator} {ap.intended_parameter_value}",
                }
                for ap in task.gold_ambiguity_points
            ],
        )
        return cls(system_prompt, llm, temperature)

    async def ask_free_text_async(self, question: UserFreeTextQuestion) -> UserFreeTextAnswer:
        result = await self.user_agent.run(
            question.question,
            output_type=UserFreeTextAnswer,
            message_history=self._message_history if self.include_history else None,
        )
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
        self._message_history += result.new_messages()
        return result.output

    async def ask_multiple_choice_async(self, question: UserMultipleChoiceQuestion) -> UserMultipleChoiceAnswer:
        def return_multiple_choice_answer(answer_number: int, num_options: int) -> int:
            if answer_number < 1 or answer_number > num_options:
                raise ModelRetry(f"Answer number should be between 1 and {num_options}")
            return answer_number - 1

        result = await self.user_agent.run(
            question.question + "".join([f"\n[{i + 1}] {o}" for i, o in enumerate(question.options)]),
            output_type=partial(return_multiple_choice_answer, num_options=len(question.options)),
            message_history=self._message_history if self.include_history else None,
        )
        self._usage += Usage.from_pydantic_ai_usage(result.usage(), self.llm)
        self._message_history += result.new_messages()
        return UserMultipleChoiceAnswer(answer_index=result.output)

    async def ask_value_async(self, question: UserValueQuestion) -> UserValueAnswer:
        result = await self.user_agent.run(
            question.model_dump_json(indent=2),
            output_type=UserValueAnswer,
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
