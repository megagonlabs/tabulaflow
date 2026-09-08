import jinja2
import time
from typing import ClassVar, cast
from tabulaflow.data import DataConnector, SQLConnector
from tabulaflow.agents.trace import Usage, Trajectory
from tabulaflow.research.observability import trace_prediction
from tabulaflow.research.types import PredQuery
from tabulaflow.research.types import SimpleNL2QTask, SimpleNL2QTaskOutput
from tabulaflow.agents.summarization import DataSourceSummarizer
from tabulaflow.agents.tools import AgentTool, GetColumnJsonSchemaTool, GetTableSchemaTool, RunQueryTool
from tabulaflow.agents.tools.run_query import latest_query_execution
from tabulaflow.research.tools import FinishTool
from tabulaflow.output.formatting import schema_formatter_registry, SQLSchemaFormatter
from tabulaflow.research.agents.registry import agent_registry
from tabulaflow.research.agents.utils import (
    format_question,
    get_max_steps_capability,
    BasicAgentConfig,
)
from tabulaflow.agents.llm import make_agent


class SchemaDiscoveryAgentConfig(BasicAgentConfig):
    db_summarizer_llm: str = "openai-responses:gpt-5.4"


SCHEMA_DISCOVERY_SYSTEM_PROMPT = """
You are a helpful AI database expert that writes {{language}} queries given a user question.

You are an agent - please keep going until the database query is fully constructed and the execution result is correct, before finishing. Only finish your turn when you are sure that the problem is solved. Autonomously resolve the task to the best of your ability.

<goal>
- Do not attempt to resolve additional ambiguities with the user. Proceed with the provided information and follow the most natural interpretation.
- You need to execute the query at least once before finishing. The last executed query will be the final output.
- Ensure the query accurately reflects the original question without adding or omitting any conditions.
- Adhere strictly to the given database schema when constructing queries.
- Pay close attention to detail.
  - When multiple similar columns or JSON fields exist, carefully select the one that best matches the question and the instructions.
  - When applying filters, if multiple columns are semantically equivalent, prefer the one that is more reliable and contains fewer null values.
- Follow the dataset and question instructions if they are provided. When there is a conflict between instructions, prioritize the question instructions.
</goal>

<tool_calling>
Gathering information:
- Always use the `get_table_schema` tool to get the schema of the relevant tables before constructing the query.
- You may use the `get_column_json_schema` tool to inspect the internal structure of semi-structured columns (e.g. VARIANT, OBJECT, ARRAY, JSON, JSONB).
- You may use `run_query` to inspect some sample values to determine the data format if necessary.

Writing the task query:
- Ensure you have collected enough information and fully understand the database structure before composing the task query.
- You may execute intermediate or exploratory queries multiple times; however, the final query (the last one executed) must be complete and fully constructed. In the final query, do not split the logic into multiple dependent queries (for example, first retrieving an ID and then using that ID in a subsequent query—this is not allowed).
- For complex queries with multiple CTEs, build incrementally: execute and verify each CTE's output before adding the next. Do NOT jump straight to the full assembled query.
- Be THOROUGH when constructing the final query. Make sure you have the FULL picture before finishing. Use additional tool calls as needed.
</tool_calling>
{%- if dataset_instructions %}

<dataset_instructions>
{{dataset_instructions}}
</dataset_instructions>
{%- endif %}
{%- if db_document %}

<db_document>
{{db_document}}
</db_document>
{%- endif %}
{%- if task_document %}

<task_document>
{{task_document}}
</task_document>
{%- endif %}
""".strip()


@agent_registry.register
class SchemaDiscoveryAgent:
    name: ClassVar[str] = "schema_discovery"
    task_type: ClassVar[str] = "simple"
    output_type: ClassVar[str] = "simple"
    config_cls: ClassVar[type[SchemaDiscoveryAgentConfig]] = SchemaDiscoveryAgentConfig

    def __init__(
        self,
        config: SchemaDiscoveryAgentConfig,
    ):
        self.config = config
        self.formatter = cast(
            SQLSchemaFormatter,
            schema_formatter_registry.get_class(config.schema_formatter)(**config.to_formatter_kwargs()),
        )

    @classmethod
    async def from_config_async(cls, config: SchemaDiscoveryAgentConfig) -> "SchemaDiscoveryAgent":
        return cls(config)

    @trace_prediction
    async def predict_async(self, task: SimpleNL2QTask, db_connector: DataConnector) -> SimpleNL2QTaskOutput:
        if not isinstance(db_connector, SQLConnector):
            raise TypeError(f"SchemaDiscoveryAgent requires a SQL db connector, got {type(db_connector)!r}")
        t0 = time.time()

        db_summarizer = DataSourceSummarizer(llm=self.config.db_summarizer_llm)

        db_summary = await db_summarizer.summarize(db_connector)
        system_prompt = jinja2.Template(SCHEMA_DISCOVERY_SYSTEM_PROMPT).render(
            language=db_connector.language,
            dataset_instructions=task.dataset_instructions,
            db_document=db_summary,
            task_document=task.document,
        )
        tools: dict[str, AgentTool] = {
            "get_table_schema": GetTableSchemaTool(
                db_connector,
                self.formatter,
                include_descriptions=self.config.use_column_descriptions,
            ),
            "get_column_json_schema": GetColumnJsonSchemaTool(db_connector.schema),
            "run_query": RunQueryTool(db_connector),
            "finish": FinishTool(),
        }

        agent = make_agent(
            self.config.llm,
            tools=[tool.as_pydantic_ai_tool() for key, tool in tools.items() if key != "finish"],
            output_type=tools["finish"].as_pydantic_ai_tool(),
            instructions=system_prompt,
            capabilities=[get_max_steps_capability(self.config.max_steps)],
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(format_question(task))
        pred_query = PredQuery.from_execution(latest_query_execution(result.all_messages()))
        usage = Usage.from_pydantic_ai_usage(result.usage, self.config.llm)
        summary_usage = db_summarizer.usage()
        if summary_usage.api_requests:
            usage += summary_usage
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-GEN-SQL")

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in tools.items()}  # type: ignore

        return SimpleNL2QTaskOutput(
            **task.model_dump(), pred_query=pred_query, trajectory=trajectory, usage=usage, inference_metrics=metrics
        )
