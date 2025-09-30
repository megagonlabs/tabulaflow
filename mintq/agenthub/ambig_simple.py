from dataclasses import dataclass
import jinja2
import time
from typing import ClassVar
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.schema import AmbigNL2QTask, SimpleAmbigNL2QTaskOutput, PredQuery, Usage, Trajectory
from mintq.utils import extract_code
from mintq.toolhub import RunQueryTool, SearchKeywordsTool, FinishTool, AskUserTool
from mintq.agenthub.base import agent_registry, BaseUserSimulator


@dataclass
class TaskContext:
    task: AmbigNL2QTask
    db_connector: BaseSQLDBConnector
    max_steps: int


SYSTEM_PROMPT = """
You are MintQ agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- The question is ambiguous and you will need to ask the user to clarify the ambiguity. Only ask one question at a time.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- Utilize the provided hints to guide query formulation.
- The final query should not return additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, the final query should not return the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, the final query should not return the score.
{% if language == "SnowflakeSQL" %}
- For Snowflake SQL, the column names must be quoted with double quotes (e.g. SELECT ORDER."product_id").
{% endif %}
""".strip()


TASK_PROMPT = """
=== START OF DATABASE SCHEMA ===
{{schema}}
=== END OF DATABASE SCHEMA ===

Question: {{question}}
{% if hints %}
=== START OF HINTS ===
{{hints}}
=== END OF HINTS ===
{% endif %}
{{language}} query:
""".strip()


def get_system_prompt(ctx: RunContext[TaskContext]) -> str:
    return jinja2.Template(SYSTEM_PROMPT).render(language=ctx.deps.task.language)


def max_steps_reached_processor(
    ctx: RunContext[TaskContext],
    messages: list[ModelMessage],
) -> list[ModelMessage]:
    assert messages is ctx.messages  # We want the injected message to be preserved in the message history as well
    if ctx.run_step == ctx.deps.max_steps:
        content = "You have reached the maximum number of steps. You have one more attempt to execute the `run_query` tool with the final query and then the `finish` tool"
        messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
    return messages


class AmbigSimpleSQLAgentConfig(BaseModel):
    llm: str
    schema_formatter: str
    temperature: float = 0.0
    num_candidates: int = 1
    max_steps: int = 20


@agent_registry.register
class AmbigSimpleSQLAgent:
    name: ClassVar = "ambig_simple_sql_agent"
    config_cls: ClassVar = AmbigSimpleSQLAgentConfig

    def __init__(
        self,
        config: AmbigSimpleSQLAgentConfig,
    ):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()

    @classmethod
    async def from_config_async(cls, config: AmbigSimpleSQLAgentConfig) -> "AmbigSimpleSQLAgent":
        return cls(config)

    async def predict_async(
        self, task: AmbigNL2QTask, db_connector: BaseSQLDBConnector, user_simulator: BaseUserSimulator
    ) -> SimpleAmbigNL2QTaskOutput:
        t0 = time.time()
        all_tools = [
            AskUserTool(user_simulator),
            SearchKeywordsTool(db_connector),
            RunQueryTool(db_connector),
            FinishTool(),
        ]
        agent = Agent[
            TaskContext, str
        ](  # type: ignore
            model=self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for tool in all_tools[:-1]],
            deps_type=TaskContext,
            output_type=all_tools[-1].as_pydantic_ai_tool(),
            result_tool_name="finish",
            instructions=get_system_prompt,
            history_processors=[max_steps_reached_processor],
        )
        agent.instrument_all()

        prompt = jinja2.Template(TASK_PROMPT).render(
            schema=self.formatter.format(db_connector.schema),
            question=task.question,
            language=task.language,
        )

        deps = TaskContext(
            task=task,
            db_connector=db_connector,
            max_steps=self.config.max_steps,
        )

        result = await agent.run(prompt, deps=deps, model_settings={"temperature": self.config.temperature})
        messages = result.all_messages()[:-1]
        pred_query = PredQuery(query=extract_code(result.output))
        trajectory = Trajectory.from_pydantic_ai_messages(messages)

        usages = [Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)]
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["api_cost_usd"] = sum(usage.api_cost_usd for usage in usages)
        metrics["input_tokens"] = sum(usage.input_tokens for usage in usages)
        metrics["output_tokens"] = sum(usage.output_tokens for usage in usages)
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {tool.name: tool.get_metrics().model_dump() for tool in all_tools}  # type: ignore

        return SimpleAmbigNL2QTaskOutput(
            **task.model_dump(),
            pred_intended_query=pred_query,
            trajectory=trajectory,
            usages=usages,
            inference_metrics=metrics,
        )
