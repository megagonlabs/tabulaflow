import jinja2
import time
from typing import ClassVar, cast

from tabulaflow.data import DBConnector
from tabulaflow.agents.trace import Usage, Trajectory
from tabulaflow.research.observability import trace_prediction
from tabulaflow.research.types import PredQuery
from tabulaflow.research.types import SimpleNL2QTask, SimpleNL2QTaskOutput
from tabulaflow.output.formatting import (
    PropertyGraphSchemaFormatter,
    SQLSchemaFormatter,
    schema_formatter_registry,
)
from tabulaflow.research.agents.registry import agent_registry, AgentConfig
from tabulaflow.research.agents.utils import (
    format_question,
    extract_code,
    BasicAgentConfig,
)
from tabulaflow.agents.llm import make_agent


SQL_AGENT_SYSTEM_PROMPT = """
You a helpful AI database expert that writes {{language}} queries given a user question.

<goal>
- Do not attempt to resolve additional ambiguities with the user. Proceed with the provided information and follow the most natural interpretation.
- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- Pay close attention to detail. When multiple similar columns exist, select the one that best matches the question and the instructions.
- Follow the dataset and question instructions if they are provided. When there is a conflict between instructions, prioritize the question instructions.
- The ouput should be a single executable {{language}} query with no explanation or any other text.
</goal>
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
class DirectPrompting:
    name: ClassVar = "direct_prompting"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[AgentConfig]] = BasicAgentConfig

    def __init__(
        self,
        config: BasicAgentConfig,
    ):
        self.config = config

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "DirectPrompting":
        return cls(config)

    def _format_schema_for_prompt(self, db_connector: DBConnector) -> str:
        if db_connector.connector_type == "sql":
            schema = db_connector.schema
            sql_formatter = cast(
                SQLSchemaFormatter,
                schema_formatter_registry.get_class(self.config.schema_formatter)(**self.config.to_formatter_kwargs()),
            )
            return sql_formatter.format(schema, include_descriptions=self.config.use_column_descriptions)
        if db_connector.connector_type == "property_graph":
            graph_formatter = cast(
                PropertyGraphSchemaFormatter,
                schema_formatter_registry.get_class(self.config.schema_formatter)(),
            )
            return graph_formatter.format(db_connector.schema)
        raise TypeError(f"Unsupported connector type for DirectPrompting: {db_connector.connector_type!r}")

    @trace_prediction
    async def predict_async(self, task: SimpleNL2QTask, db_connector: DBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        schema_str = self._format_schema_for_prompt(db_connector)

        system_prompt = jinja2.Template(SQL_AGENT_SYSTEM_PROMPT).render(
            language=db_connector.language,
            dataset_instructions=task.dataset_instructions,
            schema=schema_str,
            document=task.document,
        )

        agent = make_agent(self.config.llm, instructions=system_prompt, model_settings=self.config.to_model_settings())
        result = await agent.run(format_question(task))
        usage = Usage.from_pydantic_ai_usage(result.usage, self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-GEN-QUERY")
        pred_query = PredQuery(query=extract_code(result.output))

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0

        return SimpleNL2QTaskOutput(
            **task.model_dump(), pred_query=pred_query, trajectory=trajectory, usage=usage, inference_metrics=metrics
        )
