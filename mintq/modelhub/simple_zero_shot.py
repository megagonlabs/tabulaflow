import litellm
import time
import collections
import jinja2
import logging
from typing import Any
from mintq.utils import extract_code, get_llm_api_cost
from mintq.schema_formatter import BaseSchemaFormatter
from mintq.db_connector import BaseDBConnector
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput, Trajectory, SystemMessage, UserMessage, AssistantMessage

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
{% if language == "SnowflakeSQL" %}
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


class SimpleZeroShotNL2Q:
    name = "simple_zero_shot"

    def __init__(
        self,
        llm: str,
        schema_formatter: BaseSchemaFormatter,
        temperature: float = 0.0,
        num_candidates: int = 1,
        litellm_kwargs: dict[str, Any] = {},
    ):
        self.llm = llm
        self.schema_formatter = schema_formatter
        self.temperature = temperature
        self.num_candidates = num_candidates
        self.litellm_kwargs = litellm_kwargs

    def get_config(self) -> dict[str, str | int | float | bool]:
        return {
            "llm": self.llm,
            "temperature": self.temperature,
            "num_candidates": self.num_candidates,
        }

    def predict_sync(self, task: SimpleNL2QTask, db_connector: BaseDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        schema_str = self.schema_formatter.format(db_connector.schema)
        if len(schema_str) > SCHEMA_MAX_CHARS:
            logger.warning(
                f"Schema {db_connector.name} is too long ({len(schema_str)} chars), truncating to {SCHEMA_MAX_CHARS} chars."
            )
            schema_str = schema_str[:SCHEMA_MAX_CHARS] + "..."

        system_prompt = jinja2.Template(SYSTEM_PROMPT).render(language=task.language)
        user_prompt = jinja2.Template(TASK_PROMPT).render(
            schema=schema_str,
            hints=task.evidence,
            question=task.question,
            language=task.language,
        )

        # Text-to-SQL generation by LLM
        responses = litellm.batch_completion(
            model=self.llm,
            messages=[
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
                for _ in range(self.num_candidates)
            ],
            temperature=self.temperature,
            **self.litellm_kwargs,
        )

        for r in responses:
            if isinstance(r, litellm.BadRequestError):  # type: ignore
                raise ValueError(f"{r}")

        raw_outputs = [r["choices"][0]["message"]["content"] for r in responses]
        queries = [extract_code(q) for q in raw_outputs]
        # Select the best query using self-consistency voting
        best_query_idx = self.select_best_query(queries, db_connector)
        pred_query = queries[best_query_idx]

        # Re-construct the trajectory of the best query
        trajectory = Trajectory(
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt),
                AssistantMessage(content=raw_outputs[best_query_idx], tool_calls=[]),
            ]
        )

        # Compute metrics
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["api_calls"] = len(responses)
        metrics["input_tokens"] = sum([r["usage"]["prompt_tokens"] for r in responses])
        metrics["output_tokens"] = sum([r["usage"]["completion_tokens"] for r in responses])
        metrics["api_cost_usd"] = get_llm_api_cost(self.llm, metrics["input_tokens"], metrics["output_tokens"])  # type: ignore
        metrics["steps"] = 1
        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            metrics=metrics,
        )

    def select_best_query(self, candidates: list[str], db_connector: BaseDBConnector) -> int:
        result2idx = collections.defaultdict(list)
        run_time = {}
        for idx, query in enumerate(candidates):
            t0 = time.time()
            try:
                result = db_connector.run_query(query)
                if not result:
                    continue
            except Exception:
                continue
            run_time[idx] = time.time() - t0
            hashable = tuple(sorted(set(result), key=lambda row: tuple((x is None, x) for x in row)))
            result2idx[hashable].append(idx)

        if not result2idx:
            return 0

        # select majority query group
        majority_query_group = max(result2idx.values(), key=len)

        # select the query with the least run time
        return min(majority_query_group, key=lambda x: run_time[x])
