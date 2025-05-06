import litellm
import time
import collections
import jinja2
import logging
from mintq.utils import parse_query, get_llm_api_cost
from mintq.baseline.base import BaseNL2QModel
from mintq.schema_formatter import BaseSchemaFormatter

NL2Q_PROMPT = """
Translate the following natural language question into a {{language}} query.
- The query must follow the database schema.
- You must utilize the hints if provided.
- Output the query only, without any additional explanation.
- Do not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, do not fetch the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, do not fetch the score.
  - If the question asks for the list of objects (e.g. students), fetch the IDs of the objects.
{{language_instructions}}
=== Your task ===

Database Schema:
{{schema}}

Question: {{question}}

Hints:
{{hints}}

{{language}} Query:
""".strip()

LANGUAGE_INSTRUCTIONS = {
    "SnowflakeSQL": """For Snowflake SQL, the column names must be quoted with double quotes (e.g. `SELECT ORDER."product_id"`).\n"""
}

SCHEMA_MAX_CHARS = 20000

logger = logging.getLogger(__name__)


class SimpleZeroShotNL2Q(BaseNL2QModel):
    def __init__(
        self,
        llm: str,
        schema_formatter: BaseSchemaFormatter,
        temperature: float = 0.0,
        num_candidates: int = 1,
        litellm_kwargs: dict = {},
    ):
        self.llm = llm
        self.schema_formatter = schema_formatter
        self.temperature = temperature
        self.num_candidates = num_candidates
        self.litellm_kwargs = litellm_kwargs

    @property
    def llm_name(self) -> str:
        return self.llm

    def predict(self, task, db_connector):
        t0 = time.time()

        # Construct prompt
        language_instructions = LANGUAGE_INSTRUCTIONS.get(task.language, "")
        hints = task.evidence if task.evidence else "NO HINTS PROVIDED"
        schema_str = self.schema_formatter.format(db_connector.schema)
        if len(schema_str) > SCHEMA_MAX_CHARS:
            logger.warning(f"Schema {db_connector.db_name} is too long ({len(schema_str)} chars), truncating to {SCHEMA_MAX_CHARS} chars.")
            schema_str = schema_str[:SCHEMA_MAX_CHARS] + "..."
        prompt = jinja2.Template(NL2Q_PROMPT).render(
            language=task.language,
            language_instructions=language_instructions,
            schema=schema_str,
            hints=hints,
            question=task.question,
        )

        # Text-to-SQL generation by LLM
        responses = litellm.batch_completion(
            model=self.llm,
            messages=[[{"role": "user", "content": prompt}] for _ in range(self.num_candidates)],
            temperature=self.temperature,
            **self.litellm_kwargs,
        )
        raw_queries = [r["choices"][0]["message"]["content"] for r in responses]
        queries = [parse_query(q) for q in raw_queries]
        # Select the best query using self-consistency voting
        best_query_idx = self.select_best_query(queries, db_connector)
        if hasattr(task, "pred_query"):  # single-output task
            task.pred_query = queries[best_query_idx]
        else:  # multi-output task
            task.pred_queries = [queries[best_query_idx]]

        # Re-construct the trajectory of the best query
        task.trajectory = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": raw_queries[best_query_idx]},
        ]

        # Compute metrics
        latency = time.time() - t0
        input_tokens = sum([r["usage"]["prompt_tokens"] for r in responses])
        output_tokens = sum([r["usage"]["completion_tokens"] for r in responses])
        api_cost_usd = get_llm_api_cost(self.llm, input_tokens, output_tokens)
        metrics = {
            "latency": round(latency, 1),
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "api_cost_usd": api_cost_usd,
        }
        task.metrics.update(metrics)

        return task

    def select_best_query(self, candidates, db_connector) -> int:
        result2idx = collections.defaultdict(list)
        run_time = {}
        for idx, query in enumerate(candidates):
            t0 = time.time()
            try:
                result = db_connector.run_query(query)
                if not result:
                    continue
            except Exception as e:
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
