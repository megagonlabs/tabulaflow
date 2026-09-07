import jinja2
import time
from typing import ClassVar, cast

from tabulaflow.core import PropertyGraphSchema, SQLSchema
from tabulaflow.data import DataConnector
from tabulaflow.agents.trace import Usage, Trajectory
from tabulaflow.research.observability import trace_prediction
from tabulaflow.research.types import PredQuery
from tabulaflow.research.types import SimpleNL2QTask, SimpleNL2QTaskOutput
from tabulaflow.agents.tools import AgentTool, RunQueryTool
from tabulaflow.agents.tools.run_query import latest_query_execution
from tabulaflow.research.tools import FinishTool
from tabulaflow.output.formatting import (
    PropertyGraphSchemaFormatter,
    SQLSchemaFormatter,
    schema_formatter_registry,
)
from tabulaflow.research.agents.registry import agent_registry
from tabulaflow.research.agents.utils import (
    format_question,
    get_max_steps_capability,
    BasicAgentConfig,
)
from tabulaflow.agents.llm import make_agent


FULL_SCHEMA_SYSTEM_PROMPT = """
You are a helpful AI database expert that writes {{language}} queries given a user question.

You are an agent - please keep going until the database query is fully constructed and the execution result is correct, before finishing. Only finish your turn when you are sure that the problem is solved. Autonomously resolve the task to the best of your ability.

<goal>
- Do not attempt to resolve additional ambiguities with the user. Proceed with the provided information and follow the most natural interpretation.
- You need to execute the query at least once before finishing. The last executed query will be the final output.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- Pay close attention to detail. When multiple similar columns exist, select the one that best matches the question and the instructions.
- Follow the dataset and question instructions if they are provided. When there is a conflict between instructions, prioritize the question instructions.
</goal>

<tool_calling>
- You may call the `run_query` tool multiple times while building the final query.
- You may execute intermediate or exploratory queries; however, the final query (the last one executed) must be complete and fully constructed. In the final query, do not split the logic into multiple dependent queries (for example, first retrieving an ID and then using that ID in a subsequent query—this is not allowed).
- Be THOROUGH when constructing the final query. Make sure you have the FULL picture before finishing. Use additional tool calls as needed.
</tool_calling>
{%- if dataset_instructions %}

<dataset_instructions>
{{dataset_instructions}}
</dataset_instructions>
{%- endif %}

<physical_database_schema>
{{schema}}
</physical_database_schema>
{%- if document %}

<document>
{{document}}
</document>
{%- endif %}
""".strip()


@agent_registry.register
class FullSchemaAgent:
    name: ClassVar[str] = "full_schema"
    task_type: ClassVar[str] = "simple"
    output_type: ClassVar[str] = "simple"
    config_cls: ClassVar[type[BasicAgentConfig]] = BasicAgentConfig

    def __init__(
        self,
        config: BasicAgentConfig,
    ):
        self.config = config

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "FullSchemaAgent":
        return cls(config)

    def _format_schema_for_prompt(self, db_connector: DataConnector) -> str:
        schema = db_connector.schema
        if isinstance(schema, SQLSchema):
            sql_formatter = cast(
                SQLSchemaFormatter,
                schema_formatter_registry.get_class(self.config.schema_formatter)(**self.config.to_formatter_kwargs()),
            )
            return sql_formatter.format(schema, include_descriptions=self.config.use_column_descriptions)
        if isinstance(schema, PropertyGraphSchema):
            graph_formatter = cast(
                PropertyGraphSchemaFormatter,
                schema_formatter_registry.get_class(self.config.schema_formatter)(),
            )
            return graph_formatter.format(schema)
        raise TypeError(f"Unsupported schema type for FullSchemaAgent: {type(schema)!r}")

    @trace_prediction
    async def predict_async(self, task: SimpleNL2QTask, db_connector: DataConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        schema_str = self._format_schema_for_prompt(db_connector)

        system_prompt = jinja2.Template(FULL_SCHEMA_SYSTEM_PROMPT).render(
            language=db_connector.language,
            dataset_instructions=task.dataset_instructions,
            schema=schema_str,
            document=task.document,
        )

        tools: dict[str, AgentTool] = {
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
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-GEN-QUERY")

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)
        metrics["tools"] = {key: tool.metrics().model_dump() for key, tool in tools.items()}  # type: ignore

        return SimpleNL2QTaskOutput(
            **task.model_dump(), pred_query=pred_query, trajectory=trajectory, usage=usage, inference_metrics=metrics
        )
