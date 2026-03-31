import jinja2
import time
from typing import ClassVar
from pydantic_ai import Agent
import logging

import mintq.formatters  # noqa: F401 — register sql_*, cypher, … formatters

from mintq.db_connector import NL2QDBConnector
from mintq.schema import (
    PropertyGraphSchema,
    SQLSchema,
    SimpleNL2QTask,
    SimpleNL2QTaskOutput,
    PredQuery,
    Usage,
    Trajectory,
)
from mintq.preprocessors import SchemaCompressor
from mintq.formatters.base import formatter_registry
from mintq.agenthub.base import agent_registry, BaseAgentConfig
from mintq.agenthub.utils import (
    instrument,
    BasicAgentConfig,
)
from mintq.utils import extract_code


logger = logging.getLogger(__name__)


def format_question(task: SimpleNL2QTask) -> str:
    res = task.question
    if task.question_instructions:
        res += "\n" + task.question_instructions
    return res


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
    config_cls: ClassVar[type[BaseAgentConfig]] = BasicAgentConfig

    def __init__(
        self,
        config: BasicAgentConfig,
    ):
        self.config = config
        self.compressor = SchemaCompressor() if config.compress_schema else None

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "DirectPrompting":
        return cls(config)

    def _format_schema_for_prompt(self, db_connector: NL2QDBConnector) -> str:
        schema = db_connector.schema
        if isinstance(schema, PropertyGraphSchema):
            fmt_name = self.config.schema_formatter if self.config.schema_formatter in ("cypher",) else "cypher"
            formatter = formatter_registry.get_class(fmt_name)()
            return formatter.format(schema)
        if isinstance(schema, SQLSchema):
            working = schema
            if self.compressor is not None and self.config.compress_schema:
                working = self.compressor.compress(working)
            sql_formatter = formatter_registry.get_class(self.config.schema_formatter)(
                **self.config.to_formatter_kwargs()
            )
            return sql_formatter.format(working, add_description=self.config.use_column_description)
        raise TypeError(f"Unsupported schema type for DirectPrompting: {type(schema)!r}")

    @instrument
    async def predict_async(self, task: SimpleNL2QTask, db_connector: NL2QDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        schema_str = self._format_schema_for_prompt(db_connector)

        system_prompt = jinja2.Template(SQL_AGENT_SYSTEM_PROMPT).render(
            language=db_connector.language,
            dataset_instructions=task.dataset_instructions,
            schema=schema_str,
            document=task.document,
        )

        agent = Agent[None, str](  # type: ignore
            model=self.config.llm,
            instructions=system_prompt,
            model_settings=self.config.to_model_settings(),
        )
        result = await agent.run(format_question(task))
        usage = Usage.from_pydantic_ai_usage(result.usage(), self.config.llm)
        trajectory = Trajectory.from_pydantic_ai_messages(result.all_messages(), id="TRJY-GEN-QUERY")
        pred_query = PredQuery(query=extract_code(result.output))

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0

        return SimpleNL2QTaskOutput(
            **task.model_dump(), pred_query=pred_query, trajectory=trajectory, usage=usage, inference_metrics=metrics
        )
