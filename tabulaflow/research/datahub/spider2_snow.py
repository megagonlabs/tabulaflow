"""Spider 2.0 Snowflake dataset loader.

Spider 2.0 Snowflake provides 547 examples across 152 Snowflake databases.
See https://spider2-sql.github.io/
"""

import os
import json
import logging
import random
import re
import asyncio
from urllib.parse import quote_plus
from typing import Optional, ClassVar
import pandas as pd
from tabulaflow.core.types import GoldQuery, ExecResult
from tabulaflow.research.types import SimpleNL2QTask, NL2QDataset
from tabulaflow.core.db_connector import SQLConnector, BaseSQLDBConnector
from tabulaflow.research.datahub.base import dataset_registry

logger = logging.getLogger(__name__)


SPIDER2_SNOW_DATASET_INSTRUCTIONS = """
- **Snowflake Syntax Only:**
  - Use only functions and syntax supported by Snowflake.
  - For example, `TRIM(BOTH 'chars' FROM expr)` is not valid in Snowflake. Use `TRIM(expr, 'chars')` or `REPLACE()` instead.
  - When a regex pattern contains backslashes or single quotes, wrap it in dollar-quoted strings (`$$...$$`) to avoid escaping conflicts. Inside `$$...$$`, no escape interpretation occurs at the SQL level.
- **Schema-Qualified Table Names:**
  - Always include the schema name when referencing tables (e.g., `"SCHEMA_NAME"."TABLE_NAME"`).
- **Case-Sensitive Identifiers:**
  - Always enclose schema, table and column names in double quotes (e.g., `SELECT "col_name" FROM "SCHEMA_NAME"."TABLE_NAME"`).
  - In CTEs and subqueries, ensure both table and column aliases are wrapped in double quotes (e.g., `WITH "filtered_data" AS ...`, `SELECT ... AS "col_name"`) so they can be referenced consistently using double quotes.
  - `LATERAL FLATTEN` output columns (`VALUE`, `KEY`, ...) are uppercase. When double-quoting these names, always use uppercase (e.g., `"f"."VALUE"`).
- **Percentage Values:**
  - Do not round percentage values unless explicitly requested.
  - If the question asks for a "percentage", express the result on a 0-100 scale (i.e. multiply the fraction by 100).
  - If the question asks for a "ratio", do not multiply by 100; return the raw fraction on a 0-1 scale.
- **Columns to Return:**
  - It is safe to include all columns relevant to the question. Extra columns do not affect correctness.
  - Do not concatenate columns in the results unless explicitly requested.
- **Rows to Return:**
  - Return exactly the rows requested as the final result in the question, no more and no fewer. Be careful to handle duplicates appropriately.
  - When the question asks for an aggregated value (e.g., "how many", "change in percentage"), return the final aggregated result rather than listing individual rows.
- **No Empty Results:**
  - The final SQL query **must return at least one row**. Empty results are not allowed.
  - Common causes of unexpected empty results include insufficient exploration of alternative columns, misinterpreting value formats or encodings, applying overly restrictive filters, or misinterpreting the question. When you get empty results, systematically explore alternative columns and interpretations before giving up.
- **NULL Values in Results:**
  - Check for unexpected NULLs before finishing. Do not return results with unexpected NULLs (e.g. NULL in computed columns).
""".strip()


# Avoid repeatitive construction of tables with the same schema to speed up schema loading
GROUP_TABLE_REGEXES = {
    "CENSUS_BUREAU_ACS_1": [
        r"CENSUS_TRACTS_.*?",
    ],
}

EVAL_STANDARD_PATCHES = {
    "sf_bq236": {
        "condition_cols": [[0, 4], [0], [0]],
    },
    "sf_bq060": {
        "condition_cols": [[1], [3], [2], [1], [1]],
    },
    "sf_bq389": {
        "condition_cols": [[1, 2, 3, 4, 5, 6], [3], [2], [1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6], [2], [2]],
    },
    "sf_bq169": {
        "condition_cols": [[1, 3, 7, 8, 13], [0, 1, 13], [1, 3, 7, 8, 13], [1, 3, 7, 8, 13]],
    },
}


# Workaround until https://github.com/xlang-ai/Spider2/issues/178 is fixed.
# (Currently, AMAZON_VENDOR_ANALYTICS__SAMPLE_DATASET and NETHERLANDS_OPEN_MAP_DATA are not available)
EXCLUDE_DBS = ["AMAZON_VENDOR_ANALYTICS__SAMPLE_DATASET", "NETHERLANDS_OPEN_MAP_DATA"]


@dataset_registry.register
class Spider2SnowDatasetLoader:
    """Loader for Spider 2.0 Snowflake."""

    name: ClassVar = "spider2-snow"
    splits: ClassVar = ["test"]
    default_metrics: ClassVar = [
        "spider2_ex",
        "simple_ex",
        "executable",
        "gold_executable",
        "gold_result_not_empty",
        "pred_success",
        "schema_linking_stats",
    ]

    def __init__(
        self,
        directory: str = "data/Spider2/spider2-snow",
        sf_user: Optional[str] = None,
        sf_password: Optional[str] = None,
        sf_account: Optional[str] = None,
    ):
        """Initializes the Spider 2.0 Snowflake dataset loader.

        Args:
            directory: Path to the spider2-snow data directory.
            sf_user: Snowflake username. Falls back to ``SF_USER`` env var.
            sf_password: Snowflake password. Falls back to ``SF_PASSWORD`` env var.
            sf_account: Snowflake account identifier. Falls back to ``SF_ACCOUNT``
                env var.
        """
        self.directory = directory
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account

        # The default warehouse for Spider2 snowflake is "small" which allows for 16 concurrent queries
        self._dbms_semaphore = asyncio.Semaphore(16)

    def _load_column_descriptions(self) -> dict[tuple[str, str, str, str], str]:
        """Load column descriptions from resource JSON files.

        Returns:
            Mapping from (db_name, schema_name, table_name, column_name) to
            description.
        """
        res: dict[tuple[str, str, str, str], str] = {}
        directory = os.path.join(self.directory, "resource", "databases")
        for db_name in os.listdir(directory):
            for schema_name in os.listdir(os.path.join(directory, db_name)):
                for table_file in os.listdir(os.path.join(directory, db_name, schema_name)):
                    if not table_file.endswith(".json"):
                        continue
                    table_name = table_file.replace(".json", "")
                    with open(os.path.join(directory, db_name, schema_name, table_file), "r") as f:
                        data = json.load(f)
                        for column, description in zip(data["column_names"], data["description"]):
                            if description is not None:
                                res[(db_name, schema_name, table_name, column)] = description.strip().replace("\n", " ")
        return res

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        with open(os.path.join(self.directory, "spider2-snow.jsonl"), "r") as f:
            dbs = list(dict.fromkeys([json.loads(line)["db_id"] for line in f]))
            dbs = [db for db in dbs if db not in EXCLUDE_DBS]
            return dbs

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[SimpleNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)

        all_gold_exec_result_files = os.listdir(os.path.join(self.directory, "evaluation_suite", "gold", "exec_result"))

        # Load spider2snow_eval.jsonl
        eval_standard_file = os.path.join(self.directory, "evaluation_suite", "gold", "spider2snow_eval.jsonl")
        eval_standard = {}
        with open(eval_standard_file, "r") as f:
            for line in f:
                item = json.loads(line)
                qid = item.pop("instance_id")
                if qid in EVAL_STANDARD_PATCHES:
                    item.update(EVAL_STANDARD_PATCHES[qid])
                eval_standard[qid] = item

        tasks = []
        with open(os.path.join(self.directory, "spider2-snow.jsonl"), "r") as f:
            for line in f:
                item = json.loads(line)
                if item["db_id"] not in databases:
                    continue

                if item["external_knowledge"]:
                    document_file = os.path.join(self.directory, "resource", "documents", item["external_knowledge"])
                    with open(document_file, "r") as f:
                        document = f.read()
                else:
                    document = None

                gold_sql_file = os.path.join(
                    self.directory, "evaluation_suite", "gold", "sql", item["instance_id"] + ".sql"
                )
                if os.path.exists(gold_sql_file):
                    with open(gold_sql_file, "r") as f:
                        gold_sql = f.read()
                else:
                    gold_sql = None

                pattern = re.compile(rf"^{re.escape(item['instance_id'])}(_[a-z])?\.csv$")
                gold_exec_result_files = [file for file in all_gold_exec_result_files if re.match(pattern, file)]
                gold_exec_result_files = sorted(gold_exec_result_files)  # must load from a to z
                gold_exec_results = []
                for file in gold_exec_result_files:
                    with open(os.path.join(self.directory, "evaluation_suite", "gold", "exec_result", file), "r") as f:
                        gold_exec_results.append(pd.read_csv(f))

                condition_cols = eval_standard[item["instance_id"]].get("condition_cols", [])
                if not condition_cols or not isinstance(condition_cols[0], list):
                    condition_cols = [condition_cols for _ in range(len(gold_exec_results))]

                if len(condition_cols) != len(gold_exec_results):
                    raise ValueError(
                        f"Length of condition_cols and number of CSV files do not match for {item['instance_id']}"
                    )

                # Primary: use full DataFrame (no condition_cols at load).
                # required_columns = condition_cols[0] so spider2_ex applies it at eval time.
                primary = ExecResult(df=gold_exec_results[0])
                primary_required_columns = condition_cols[0] if condition_cols[0] else None
                filtered_alternatives = []
                for df, cols in zip(gold_exec_results[1:], condition_cols[1:]):
                    if cols:
                        if any(c >= len(df.columns) for c in cols):
                            raise ValueError(
                                f"A column index in condition_cols is out of range for {item['instance_id']}"
                            )
                        filtered_alternatives.append(df.iloc[:, cols])
                    else:
                        filtered_alternatives.append(df)
                alternatives = [ExecResult(df=df) for df in filtered_alternatives]

                ignore_order = eval_standard[item["instance_id"]].get("ignore_order", False)

                tasks.append(
                    SimpleNL2QTask(
                        qid=item["instance_id"],
                        db=item["db_id"],
                        question=item["instruction"],
                        dataset_instructions=SPIDER2_SNOW_DATASET_INSTRUCTIONS,
                        document=document,
                        gold_query=GoldQuery(
                            query=gold_sql,
                            exec_result=primary,
                            alternative_results=alternatives,
                            required_columns=primary_required_columns,
                            required_sorted=not ignore_order,
                        ),
                    )
                )

        return tasks

    async def _build_snowflake_connector(self, db_name: str) -> SQLConnector:
        """Build a Snowflake SQLConnector for a spider2-snow database."""
        sf_user = self.sf_user or os.environ["SF_USER"]
        sf_password = self.sf_password or os.environ["SF_PASSWORD"]
        sf_account = self.sf_account or os.environ["SF_ACCOUNT"]
        base_url = f"snowflake://{quote_plus(sf_user)}:{quote_plus(sf_password)}@{sf_account}"
        connect_args = {
            "disable_ocsp_checks": True,
            "client_session_keep_alive": True,
        }
        # Per-db concurrency is 2 because there are 152 databases so we can have up to 152 x 2 = 304 concurrent connections
        return await SQLConnector.from_url_async(
            f"spider2-snow+{db_name}",
            f"{base_url}/{db_name}",
            db_name,
            max_concurrency_per_db=2,
            dbms_semaphore=self._dbms_semaphore,
            connect_args=connect_args,
            group_date_partitioned_tables=True,
            group_table_regexes=GROUP_TABLE_REGEXES.get(db_name, []),
            enable_query_caching=True,
        )

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> dict[str, BaseSQLDBConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        column_descriptions = self._load_column_descriptions()

        connectors: dict[str, BaseSQLDBConnector] = {}
        for db_name in databases:
            conn = await self._build_snowflake_connector(db_name)

            for table in conn.schema.tables:
                for column in table.columns:
                    desc = column_descriptions.get(
                        (db_name, table.schema_name, table.name, column.name),  # type: ignore
                    )
                    if desc:
                        column.description = desc

            connectors[db_name] = conn

        return connectors

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
