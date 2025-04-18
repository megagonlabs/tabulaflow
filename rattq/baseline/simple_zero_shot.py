import litellm
import time
import collections
from rattq.utils import *
from rattq.baseline.base import BaseNL2QModel
from rattq.schema_formatter import BaseSchemaFormatter

NL2Q_PROMPT = """
Translate the following natural language question into a {language} query.
- The query must follow the database schema.
- You must use the hints to generate the query.
- You must use the 【Foreign keys】 section in the database schema to connect the tables.
- Output the query only, without any additional explanation.
- Do not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, do not fetch the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, do not fetch the score.
  - Example:
    Table: student
    [
    (id:TEXT, Primary Key, Example: 1),
    (name:TEXT, Examples: [John]),
    (score:INTEGER, Examples: [100, 95, 90]),
    ]
    Question: What is the highest score?
    Query: SELECT MAX(score) FROM student

    Question: What is the student with the highest score?
    Query: SELECT name FROM student WHERE score = (SELECT MAX(score) FROM student)

=== Your task ===

Database Schema:
{schema}

Question: {question}

Hints:
{evidence}

Query:
""".strip()


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
        prompt = NL2Q_PROMPT.format(
            language=task.language,
            schema=self.schema_formatter.format(db_connector.schema),
            evidence=task.evidence,
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
