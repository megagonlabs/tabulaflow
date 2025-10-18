import jinja2
import time
from typing import ClassVar
from pydantic_ai import Agent
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
from mintq.agenthub.base import agent_registry, BaseAgentConfig
from mintq.agenthub.utils import get_max_steps_processor, instrument, BasicAgentConfig


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


@agent_registry.register
class SQLAgent:
    name: ClassVar = "sql_agent"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[BaseAgentConfig]] = BasicAgentConfig

    def __init__(self, config: BasicAgentConfig):
        self.config = config
        self.formatter: BaseSQLSchemaFormatter = formatter_registry.get_class(config.schema_formatter)()

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "SQLAgent":
        return cls(config)

    @instrument
    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        tools = {
            "get_schema": GetSchemaTool(
                (await SchemaCompressor().run_async(db_connector.schema))
                if self.config.compress_schema
                else db_connector.schema,
                self.formatter,
            ),
            "get_column_description": GetColumnDescriptionTool(db_connector),
            "search_keywords": SearchKeywordsTool(db_connector),
            "run_query": RunQueryTool(db_connector),
            "finish": FinishTool(),
        }
        system_prompt = jinja2.Template(SYSTEM_PROMPT).render(language=task.language)

        agent = Agent[None, PredQuery](
            model=self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for key, tool in tools.items() if key != "finish"],
            output_type=tools["finish"].as_pydantic_ai_tool(),
            instructions=system_prompt,
            history_processors=[get_max_steps_processor(self.config.max_steps)],
            model_settings={"temperature": self.config.temperature},
        )

        agent_no_tools = Agent(model=self.config.llm, instructions=system_prompt)

        prompt = f"{task.question} {task.evidence}"

        fallback = False
        try:
            result = await agent.run(prompt)
            pred_query: PredQuery = result.output
        except (UsageLimitExceeded, UnexpectedModelBehavior):
            result = await agent_no_tools.run(prompt)
            pred_query = PredQuery(query=extract_code(result.output))
            fallback = True
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages())
        usage = Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["fallback"] = fallback
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in tools.items()}  # type: ignore

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            usage=usage,
            inference_metrics=metrics,
        )
