from pydantic_ai import Agent
import jinja2
from pydantic import TypeAdapter
from mintq.agenthub.base import UserQuestion, UserAnswer
from mintq.schema import AmbigNL2QTask

USER_SIMULATOR_SYSTEM_PROMPT = """
You are a data analyst trying to solve the following task: {{task}}
Here,{% for ap in ambiguity_points %}
- "{{ap.phrase}}" should be interpreted as "{{ap.interpretation}}".{% endfor %}

You will be asked questions regarding the possible ambiguities in the task, and you are responsible for providing clarifications.

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
    def __init__(self, system_prompt: str, llm: str = "openai:gpt-4.1-mini", temperature: float = 0.0):
        self.llm = llm
        self.system_prompt = system_prompt
        self.temperature = temperature

        self.agent = Agent[None, str](
            model=self.llm,
            tools=[],
            instructions=self.system_prompt,
        )
        self.agent.instrument_all()
        self.message_history = None

    @classmethod
    def from_ambig_nl2q_task(
        cls, task: AmbigNL2QTask, llm: str = "openai:gpt-4.1-mini", temperature: float = 0.0
    ) -> "UserSimulator":
        if any(ap.intended_interpretation_idx is None for ap in task.gold_ambiguity_points if ap.type == "finite"):
            raise ValueError("All finite ambiguity points must have an intended interpretation")
        if any(ap.indended_parameter_value is None for ap in task.gold_ambiguity_points if ap.type == "infinite"):
            raise ValueError("All infinite ambiguity points must have an intended parameter value")

        system_prompt = jinja2.Template(USER_SIMULATOR_SYSTEM_PROMPT).render(
            task=task.question,
            ambiguity_points=[
                {
                    "phrase": ap.phrase,
                    "interpretation": ap.interpretations[ap.intended_interpretation_idx]  # type: ignore
                    if ap.type == "finite"
                    else f"{ap.parameter_operator} {ap.indended_parameter_value}",
                }
                for ap in task.gold_ambiguity_points
            ],
        )
        return cls(system_prompt, llm, temperature)

    async def ask_async(self, questions: list[UserQuestion]) -> list[UserAnswer]:
        result = await self.agent.run(
            TypeAdapter(list[UserQuestion]).dump_json(questions, indent=2).decode(),
            output_type=list[UserAnswer],
            model_settings={"temperature": self.temperature},
            message_history=self.message_history,
        )
        self.message_history = result.all_messages()  # type: ignore
        if len(result.output) != len(questions):
            raise ValueError(
                "The number of answers does not match the number of questions. Please consider using a stronger LLM."
            )
        if any(a.type != q.type for a, q in zip(result.output, questions)):
            raise ValueError(
                "The type of the answers does not match the type of the questions. Please consider using a stronger LLM."
            )
        return result.output
