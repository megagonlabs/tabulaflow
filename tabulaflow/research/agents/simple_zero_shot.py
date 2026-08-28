import time
import collections
import jinja2
import logging
import asyncio
from typing import ClassVar, cast
from pydantic import Field
from tabulaflow.agents.llm import make_agent
from tabulaflow.output.formatting import (
    PropertyGraphSchemaFormatter,
    SQLSchemaFormatter,
    schema_formatter_registry,
)
from tabulaflow.data import DBConnector
from tabulaflow.agents.trace import Trajectory, Usage
from tabulaflow.research.observability import trace_prediction
from tabulaflow.research.types import PredQuery
from tabulaflow.research.types import SimpleNL2QTask, SimpleNL2QTaskOutput
from tabulaflow.research.agents.registry import agent_registry, AgentConfig
from tabulaflow.research.agents.utils import BasicAgentConfig, extract_code, format_question

SYSTEM_PROMPT = """
You are a database expert responsible for translating natural language questions into {{language}} queries.
- The query must follow the given database schema.
- You must follow the hints if provided.
- The final output should not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, the final query should not fetch the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, the final query should not fetch the score.
  - If the question asks for the list of objects (e.g. students), fetch the IDs of the objects.
- The final output should only include the SQL query, without explanation or any other text.
{% if language == "snowflake" %}
- For Snowflake SQL, the column names must be quoted with double quotes (e.g. SELECT ORDER."product_id").
{% endif %}
""".strip()


TASK_PROMPT = """
=== START OF DATABASE SCHEMA ===
{{schema}}
=== END OF DATABASE SCHEMA ===
{% if hints %}
=== START OF HINTS ===
{{hints}}
=== END OF HINTS ===
{% endif %}
Question to translate: {{question}}
{{language}} query:
""".strip()

SCHEMA_MAX_CHARS = 128000

logger = logging.getLogger(__name__)


class SimpleZeroShotNL2QConfig(BasicAgentConfig):
    num_candidates: int = Field(default=1, ge=1)


@agent_registry.register
class SimpleZeroShotNL2Q:
    name: ClassVar = "simple_zero_shot"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[AgentConfig]] = SimpleZeroShotNL2QConfig

    def __init__(
        self,
        config: SimpleZeroShotNL2QConfig,
    ):
        self.config = config
        self.formatter = schema_formatter_registry.get_class(config.schema_formatter)(**config.to_formatter_kwargs())

    @classmethod
    async def from_config_async(cls, config: SimpleZeroShotNL2QConfig) -> "SimpleZeroShotNL2Q":
        return cls(config)

    @trace_prediction
    async def predict_async(self, task: SimpleNL2QTask, db_connector: DBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        if db_connector.connector_type == "property_graph":
            schema_str = cast(PropertyGraphSchemaFormatter, self.formatter).format(db_connector.schema)
        elif db_connector.connector_type == "sql":
            schema = db_connector.schema
            schema_str = cast(SQLSchemaFormatter, self.formatter).format(
                schema,
                include_descriptions=self.config.use_column_descriptions,
            )
        else:
            raise TypeError(f"Unsupported connector type for SimpleZeroShotNL2Q: {db_connector.connector_type!r}")
        if len(schema_str) > SCHEMA_MAX_CHARS:
            logger.warning(
                f"Schema {db_connector.global_id} is too long ({len(schema_str)} chars), truncating to {SCHEMA_MAX_CHARS} chars."
            )
            schema_str = schema_str[:SCHEMA_MAX_CHARS] + "..."

        system_prompt = jinja2.Template(SYSTEM_PROMPT).render(language=db_connector.language)
        user_prompt = jinja2.Template(TASK_PROMPT).render(
            schema=schema_str,
            hints=task.document,
            question=format_question(task),
            language=db_connector.language,
        )

        # Text-to-SQL generation by LLM
        agent = make_agent(
            self.config.llm,
            instructions=system_prompt,
            model_settings=self.config.to_model_settings(),
        )
        responses = await asyncio.gather(*(agent.run(user_prompt) for _ in range(self.config.num_candidates)))

        raw_outputs = [response.output for response in responses]
        queries = [extract_code(q) for q in raw_outputs]
        # Select the best query using self-consistency voting
        best_query_idx = await self.select_best_query_async(queries, db_connector)
        pred_query = PredQuery(query=queries[best_query_idx])

        # Re-construct the trajectory of the best query
        trajectory = Trajectory.from_pydantic_ai_messages(responses[best_query_idx].all_messages(), id="TRJY-GEN-QUERY")

        usage = Usage.create(llm=self.config.llm)
        for response in responses:
            usage += Usage.from_pydantic_ai_usage(response.usage, self.config.llm)

        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = 1

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            usage=usage,
            inference_metrics=metrics,
        )

    async def select_best_query_async(self, candidates: list[str], db_connector: DBConnector) -> int:
        all_results = await asyncio.gather(
            *[db_connector.run_query_async(query) for query in candidates], return_exceptions=True
        )

        result2idx = collections.defaultdict(list)

        for idx, result in enumerate(all_results):
            if isinstance(result, BaseException):
                if isinstance(result, (KeyboardInterrupt, SystemExit)):
                    raise result
                continue
            if result.error is not None or result.df is None or result.df.empty:
                continue
            rows = result.df.itertuples(index=False, name=None)
            hashable = tuple(sorted(set(rows), key=lambda row: tuple((value is None, value) for value in row)))
            result2idx[hashable].append(idx)

        if not result2idx:
            return 0

        # select majority query group
        majority_query_group = max(result2idx.values(), key=len)
        return majority_query_group[0]
