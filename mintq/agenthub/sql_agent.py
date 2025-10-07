from dataclasses import dataclass
import jinja2
import time
from typing import ClassVar
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior
from mintq.db_connector import BaseSQLDBConnector
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput, PredQuery, Usage, Trajectory
from mintq.utils import extract_code
from mintq.metadata_synthesizers import SchemaCompressor
from mintq.toolhub import (
    RunQueryTool,
    SearchKeywordsTool,
    FinishTool,
    GetSchemaTool,
    GetColumnDescriptionTool,
)
from mintq.formatters.base import formatter_registry, BaseSQLSchemaFormatter
from mintq.agenthub.base import agent_registry
from mintq.agenthub.utils import get_max_steps_processor


@dataclass
class TaskContext:
    task: SimpleNL2QTask
    db_connector: BaseSQLDBConnector
    max_steps: int


SYSTEM_PROMPT = """
You are MintQ agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

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


def get_system_prompt(ctx: RunContext[TaskContext]) -> str:
    return jinja2.Template(SYSTEM_PROMPT).render(language=ctx.deps.task.language)


class SQLAgentConfig(BaseModel):
    llm: str
    schema_formatter: str
    compress_schema: bool = True
    temperature: float = 0.0
    num_candidates: int = 1
    max_steps: int = 20


@agent_registry.register
class SQLAgent:
    name: ClassVar = "sql_agent"
    config_cls: ClassVar = SQLAgentConfig

    def __init__(self, config: SQLAgentConfig):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()

    @classmethod
    async def from_config_async(cls, config: SQLAgentConfig) -> "SQLAgent":
        return cls(config)

    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        schema = db_connector.schema
        if self.config.compress_schema:
            schema = await SchemaCompressor().run_async(schema)

        get_schema_tool = GetSchemaTool(schema, self.formatter)
        get_column_description_tool = GetColumnDescriptionTool(db_connector)
        search_keywords_tool = SearchKeywordsTool(db_connector)
        run_query_tool = RunQueryTool(db_connector)
        finish_tool = FinishTool()
        all_tools = [
            get_schema_tool,
            get_column_description_tool,
            search_keywords_tool,
            run_query_tool,
            finish_tool,
        ]
        agent = Agent[TaskContext, str](  # type: ignore
            model=self.config.llm,
            tools=[
                get_schema_tool.as_pydantic_ai_tool(),
                get_column_description_tool.as_pydantic_ai_tool(),
                search_keywords_tool.as_pydantic_ai_tool(),
                run_query_tool.as_pydantic_ai_tool(),
            ],
            deps_type=TaskContext,
            output_type=finish_tool.as_pydantic_ai_tool(),
            instructions=get_system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
        )
        agent.instrument_all()

        agent_no_tools = Agent[TaskContext, str](
            model=self.config.llm,
            tools=[],
            deps_type=TaskContext,
            instructions=get_system_prompt,
        )
        agent_no_tools.instrument_all()

        prompt = f"{task.question} {task.evidence}"

        deps = TaskContext(
            task=task,
            db_connector=db_connector,
            max_steps=self.config.max_steps,
        )

        fallback = False
        try:
            result = await agent.run(prompt, deps=deps, model_settings={"temperature": self.config.temperature})
            pred_query: PredQuery = result.output
            messages = result.all_messages()[:-1]
        except (UsageLimitExceeded, UnexpectedModelBehavior):
            result = await agent_no_tools.run(
                prompt, deps=deps, model_settings={"temperature": self.config.temperature}
            )
            pred_query = PredQuery(query=extract_code(result.output))
            messages = result.all_messages()
            fallback = True
        trajectory = Trajectory.from_pydantic_ai_messages(messages)

        usages = [Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)]

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["fallback"] = fallback
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {tool.name: tool.get_metrics().model_dump() for tool in all_tools}  # type: ignore

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            usages=usages,
            inference_metrics=metrics,
        )
