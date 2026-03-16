"""Spider 2.0-Lite dataset loader.

Spider 2.0-Lite provides 547 examples across BigQuery, Snowflake, and SQLite.
See https://spider2-sql.github.io/
"""

import os
import json
import logging
import random
import re
from typing import Optional, ClassVar
import pandas as pd
from mintq.schema import SimpleNL2QTask, NL2QDataset, GoldQuery, ExecResult
from mintq.db_connector import BaseSQLDBConnector
from mintq.datahub.base import dataset_registry

logger = logging.getLogger(__name__)


SPIDER2_LITE_DATASET_INSTRUCTIONS = """
- **BigQuery Syntax Only:**
  - Use only functions and syntax supported by BigQuery.
- **Percentage Values:**
  - Do not round percentage values unless explicitly requested.
  - If the question asks for a "percentage", express the result on a 0-100 scale (i.e. multiply the fraction by 100).
  - If the question asks for a "ratio", do not multiply by 100; return the raw fraction on a 0-1 scale.
- **Columns to Return:**
  - It is safe to include all columns relevant to the question. Extra columns do not affect correctness.
  - Do not concatenate columns in the results unless explicitly requested.
- **Rows to Return:**
  - Return exactly the rows requested as the final result in the question, no more and no fewer. Be careful to handle duplicates appropriately.
- **No Empty Results:**
  - The final SQL query **must return at least one row**. Empty results are not allowed.
  - Common causes of unexpected empty results include insufficient exploration of alternative columns, misinterpreting value formats or encodings, applying overly restrictive filters, or misinterpreting the question. When you get empty results, systematically explore alternative columns and interpretations before giving up.
- **NULL Values in Results:**
  - Check for unexpected NULLs before finishing. Do not return results with unexpected NULLs (e.g. NULL in computed columns).
""".strip()


@dataset_registry.register
class Spider2LiteDatasetLoader:
    """Loader for Spider 2.0-Lite (BigQuery, Snowflake, SQLite)."""

    name: ClassVar = "spider2-lite"
    splits: ClassVar = ["test"]

    def __init__(self, directory: str = "data/Spider2/spider2-lite"):
        self.directory = directory

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        jsonl_path = os.path.join(self.directory, "spider2-lite.jsonl")
        if not os.path.exists(jsonl_path):
            return []

        with open(jsonl_path, "r") as f:
            dbs = list(dict.fromkeys([json.loads(line)["db"] for line in f]))
        return dbs

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[SimpleNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        jsonl_path = os.path.join(self.directory, "spider2-lite.jsonl")
        if not os.path.exists(jsonl_path):
            return []

        eval_dir = os.path.join(self.directory, "evaluation_suite", "gold")
        exec_result_dir = os.path.join(eval_dir, "exec_result")
        all_gold_exec_result_files = os.listdir(exec_result_dir) if os.path.isdir(exec_result_dir) else []

        eval_file = os.path.join(eval_dir, "spider2lite_eval.jsonl")
        eval_standard: dict = {}
        if os.path.exists(eval_file):
            with open(eval_file, "r") as f:
                for line in f:
                    item = json.loads(line)
                    eval_standard[item.pop("instance_id")] = item

        tasks = []
        with open(jsonl_path, "r") as f:
            for line in f:
                item = json.loads(line)
                if item["db"] not in databases:
                    continue

                document = None
                if item.get("external_knowledge"):
                    doc_path = os.path.join(self.directory, "resource", "documents", item["external_knowledge"])
                    if os.path.exists(doc_path):
                        with open(doc_path, "r") as df:
                            document = df.read()

                gold_sql = None
                gold_sql_path = os.path.join(eval_dir, "sql", item["instance_id"] + ".sql")
                if os.path.exists(gold_sql_path):
                    with open(gold_sql_path, "r") as gf:
                        gold_sql = gf.read()

                pattern = re.compile(rf"^{re.escape(item['instance_id'])}(_[a-z])?\.csv$")
                gold_exec_result_files = sorted(
                    [f for f in all_gold_exec_result_files if re.match(pattern, f)]
                )
                gold_exec_results = []
                for file in gold_exec_result_files:
                    with open(os.path.join(exec_result_dir, file), "r") as rf:
                        gold_exec_results.append(pd.read_csv(rf))

                condition_cols = eval_standard.get(item["instance_id"], {}).get("condition_cols", [])
                if not condition_cols or not isinstance(condition_cols[0] if condition_cols else None, list):
                    condition_cols = [condition_cols for _ in range(max(1, len(gold_exec_results)))]

                filtered_gold_exec_results = []
                for i, df in enumerate(gold_exec_results):
                    cols = condition_cols[i] if i < len(condition_cols) else []
                    if cols and all(c < len(df.columns) for c in cols):
                        filtered_gold_exec_results.append(df.iloc[:, cols])
                    else:
                        filtered_gold_exec_results.append(df)

                ignore_order = eval_standard.get(item["instance_id"], {}).get("ignore_order", False)
                primary = (
                    ExecResult(df=filtered_gold_exec_results[0])
                    if filtered_gold_exec_results
                    else ExecResult(df=pd.DataFrame())
                )
                alternatives = [ExecResult(df=df) for df in filtered_gold_exec_results[1:]]

                tasks.append(
                    SimpleNL2QTask(
                        qid=item["instance_id"],
                        db=item["db"],
                        question=item["question"],
                        dataset_instructions=SPIDER2_LITE_DATASET_INSTRUCTIONS,
                        document=document,
                        gold_query=GoldQuery(
                            query=gold_sql,
                            exec_result=primary,
                            alternative_results=alternatives,
                            required_columns=None,
                            required_sorted=not ignore_order,
                        ),
                    )
                )

        return tasks

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> dict[str, BaseSQLDBConnector]:
        """Return DB connectors. Spider2-Lite uses BigQuery, Snowflake, and SQLite.

        TODO: Implement backend dispatch (BigQuery via sqlalchemy-bigquery,
        Snowflake via snowflake-sqlalchemy, SQLite via aiosqlite).
        """
        raise NotImplementedError(
            "spider2-lite get_db_connectors_async: implement BigQuery, Snowflake, and SQLite connectors"
        )

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset:
        tasks = await self.get_tasks_async(split, databases)
        if subsample_size:
            tasks = random.Random(42).sample(tasks, subsample_size)
        db_connectors = await self.get_db_connectors_async(split, databases)
        return NL2QDataset(
            name=self.name,
            split=split,
            databases=databases,
            subsample_size=subsample_size,
            tasks=tasks,  # type: ignore
            db_connectors=db_connectors,
        )
