import litellm
import time
import collections
import jinja2
import logging
import asyncio
from typing import Any, ClassVar
from tabulaflow.core.utils import extract_code
from tabulaflow.core.preprocessors import SchemaCompressor
from tabulaflow.core.formatters import formatter_registry
from tabulaflow.core.db_connector import NL2QDBConnector
from tabulaflow.core.types import Trajectory, SystemMessage, UserMessage, AssistantMessage, PredQuery, Usage
from tabulaflow.research.types import SimpleNL2QTask, SimpleNL2QTaskOutput
from tabulaflow.agenthub.base import agent_registry, BaseAgentConfig
from tabulaflow.agenthub.utils import instrument, BasicAgentConfig

SYSTEM_PROMPT = """
You are a database expert responsible for translating natural language questions into {{language}} queries.
- The query must follow the given database schema.
- You must follow the hints if provided.
- The final output should not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, the final query should not fetch the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, the final query should not fetch the score.
  - If the question asks for the list of objects (e.g. students), fetch the IDs of the objects.
- The final output should only include the SQL query, without explanation or any other text.
- Before returning the final output, always execute the query and check if the results match the question.
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
    num_candidates: int = 1
    litellm_kwargs: dict[str, Any] = {}


@agent_registry.register
class SimpleZeroShotNL2Q:
    name: ClassVar = "simple_zero_shot"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[BaseAgentConfig]] = SimpleZeroShotNL2QConfig

    def __init__(
        self,
        config: SimpleZeroShotNL2QConfig,
    ):
        self.config = config
        self.formatter = formatter_registry.get_class(config.schema_formatter)(**config.to_formatter_kwargs())

    @classmethod
    async def from_config_async(cls, config: SimpleZeroShotNL2QConfig) -> "SimpleZeroShotNL2Q":
        return cls(config)

    @instrument
    async def predict_async(self, task: SimpleNL2QTask, db_connector: NL2QDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        schema = db_connector.schema
        if self.config.compress_schema and db_connector.connector_type == "sql":
            schema = SchemaCompressor().compress(schema)  # type: ignore[arg-type]

        if db_connector.connector_type == "property_graph":
            schema_str = self.formatter.format(schema)  # type: ignore[arg-type]
        elif db_connector.connector_type == "sql":
            schema_str = self.formatter.format(schema, add_description=self.config.use_column_description)  # type: ignore[arg-type, call-arg]
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
            question=task.question,
            language=db_connector.language,
        )

        # Text-to-SQL generation by LLM
        responses = await asyncio.gather(
            *[
                litellm.acompletion(
                    model=self.config.llm.replace(":", "/"),
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=self.config.temperature,
                    **self.config.litellm_kwargs,
                )
                for _ in range(self.config.num_candidates)
            ]
        )

        for r in responses:
            if isinstance(r, litellm.BadRequestError):  # type: ignore
                raise ValueError(f"{r}")

        raw_outputs = [r["choices"][0]["message"]["content"] for r in responses]
        queries = [extract_code(q) for q in raw_outputs]
        # Select the best query using self-consistency voting
        best_query_idx = await self.select_best_query_async(queries, db_connector)
        pred_query = PredQuery(query=queries[best_query_idx])

        # Re-construct the trajectory of the best query
        trajectory = Trajectory(
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt),
                AssistantMessage(content=raw_outputs[best_query_idx], tool_calls=[]),
            ]
        )

        usage = Usage.create(
            llm=self.config.llm,
            api_requests=len(responses),
            input_tokens=sum(r["usage"]["prompt_tokens"] for r in responses),
            output_tokens=sum(r["usage"]["completion_tokens"] for r in responses),
        )

        # Compute metrics
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["steps"] = 1

        print(metrics)

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            usage=usage,
            inference_metrics=metrics,
        )

    async def select_best_query_async(self, candidates: list[str], db_connector: NL2QDBConnector) -> int:
        all_results = await asyncio.gather(
            *[db_connector.run_query_async(query) for query in candidates], return_exceptions=True
        )

        result2idx = collections.defaultdict(list)

        for idx, result in enumerate(all_results):
            if isinstance(result, BaseException):
                if isinstance(result, (KeyboardInterrupt, SystemExit)):
                    raise result
                continue
            if not result:
                continue
            hashable = tuple(sorted(set(result), key=lambda row: tuple((x is None, x) for x in row)))
            result2idx[hashable].append(idx)

        if not result2idx:
            return 0

        # select majority query group
        majority_query_group = max(result2idx.values(), key=len)
        return majority_query_group[0]
