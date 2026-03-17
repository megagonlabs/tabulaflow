"""Spider 2.0-Lite dataset loader.

Spider 2.0-Lite provides 547 examples across BigQuery, Snowflake, and SQLite.
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
from mintq.schema import SimpleNL2QTask, NL2QDataset, GoldQuery, ExecResult
from mintq.db_connector import SQLConnector, BaseSQLDBConnector
from mintq.datahub.base import dataset_registry

logger = logging.getLogger(__name__)

Backend = str  # "bigquery" | "snowflake" | "sqlite"


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

    def __init__(
        self,
        directory: str = "data/Spider2/spider2-lite",
        sf_user: Optional[str] = None,
        sf_password: Optional[str] = None,
        sf_account: Optional[str] = None,
        bq_credentials_path: Optional[str] = None,
        sqlite_db_dir: Optional[str] = None,
    ):
        self.directory = directory
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self.bq_credentials_path = bq_credentials_path
        self.sqlite_db_dir = sqlite_db_dir or os.path.join(
            directory, "resource", "databases", "spider2-localdb"
        )
        self._sf_semaphore = asyncio.Semaphore(16)

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

    def _get_backend(self, db_name: str) -> Backend:
        """Determine the backend for a database by checking resource directories."""
        resource_dir = os.path.join(self.directory, "resource", "databases")
        for backend in ("bigquery", "snowflake", "sqlite"):
            backend_dir = os.path.join(resource_dir, backend)
            if os.path.isdir(backend_dir) and db_name in os.listdir(backend_dir):
                return backend
        raise ValueError(f"Cannot determine backend for database {db_name!r}")

    def _get_bq_project_datasets(self, db_name: str) -> list[tuple[str, str]]:
        """Parse project.dataset pairs from the BigQuery resource directory."""
        bq_dir = os.path.join(self.directory, "resource", "databases", "bigquery", db_name)
        result = []
        for entry in sorted(os.listdir(bq_dir)):
            entry_path = os.path.join(bq_dir, entry)
            if os.path.isdir(entry_path) and "." in entry:
                project, dataset = entry.split(".", 1)
                result.append((project, dataset))
        return result

    def _load_column_descriptions(self) -> dict[tuple[str, str, str], str]:
        """Load column descriptions from resource JSON files.

        Returns:
            Mapping from (db_name, table_name, column_name) to description.
        """
        res: dict[tuple[str, str, str], str] = {}
        resource_dir = os.path.join(self.directory, "resource", "databases")
        for backend in ("bigquery", "snowflake", "sqlite"):
            backend_dir = os.path.join(resource_dir, backend)
            if not os.path.isdir(backend_dir):
                continue
            for db_name in os.listdir(backend_dir):
                db_path = os.path.join(backend_dir, db_name)
                if not os.path.isdir(db_path):
                    continue
                for root, _dirs, files in os.walk(db_path):
                    for fname in files:
                        if not fname.endswith(".json"):
                            continue
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath, "r") as f:
                                data = json.load(f)
                        except (json.JSONDecodeError, KeyError):
                            continue
                        table_name = data.get("table_name", fname.replace(".json", ""))
                        for col, desc in zip(
                            data.get("column_names", []),
                            data.get("description", []),
                        ):
                            if desc:
                                desc_str = str(desc).strip().replace("\n", " ")
                                if desc_str:
                                    res[(db_name, table_name, col)] = desc_str
        return res

    async def _build_bq_connector(
        self, db_name: str, project_datasets: list[tuple[str, str]]
    ) -> SQLConnector:
        """Build a BigQuery SQLConnector for a spider2-lite database.

        Uses ``billing_project_id`` so that BigQuery jobs are billed to our
        GCP project while the data project in the URL is used for schema
        introspection and table resolution.  A single engine handles
        multi-dataset dbs because the inspector accepts an explicit
        ``schema`` argument that overrides the default dataset.
        """
        billing_project = os.environ.get("GOOGLE_CLOUD_PROJECT", "vertexai-434121")
        bq_credentials_path = self.bq_credentials_path or os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )

        primary_project = project_datasets[0][0]
        first_dataset = project_datasets[0][1]
        datasets = [d for p, d in project_datasets if p == primary_project]

        engine_kwargs: dict = {}
        if bq_credentials_path:
            engine_kwargs["credentials_path"] = bq_credentials_path
        engine_kwargs["billing_project_id"] = billing_project

        url = f"bigquery://{primary_project}/{first_dataset}"
        return await SQLConnector.from_url_async(
            f"spider2-lite+{db_name}",
            db_name,
            "sync",
            url,
            max_concurrency_per_db=4,
            include_schema_names=datasets,
            group_date_partitioned_tables=True,
            **engine_kwargs,
        )

    async def _build_sf_connector(self, db_name: str) -> SQLConnector:
        """Build a Snowflake SQLConnector for a spider2-lite database."""
        sf_user = self.sf_user or os.environ["SF_USER"]
        sf_password = self.sf_password or os.environ["SF_PASSWORD"]
        sf_account = self.sf_account or os.environ["SF_ACCOUNT"]
        base_url = f"snowflake://{quote_plus(sf_user)}:{quote_plus(sf_password)}@{sf_account}"
        connect_args = {
            "disable_ocsp_checks": True,
            "client_session_keep_alive": True,
        }
        return await SQLConnector.from_url_async(
            f"spider2-lite+{db_name}",
            db_name,
            "sync",
            f"{base_url}/{db_name}",
            max_concurrency_per_db=2,
            dbms_semaphore=self._sf_semaphore,
            connect_args=connect_args,
            group_date_partitioned_tables=True,
        )

    async def _build_sqlite_connector(self, db_name: str) -> SQLConnector:
        """Build a SQLite SQLConnector for a spider2-lite database."""
        db_path = os.path.join(self.sqlite_db_dir, f"{db_name}.sqlite")
        if not os.path.exists(db_path):
            raise FileNotFoundError(
                f"SQLite database not found: {db_path}. "
                "Download from https://drive.usercontent.google.com/download?"
                "id=1coEVsCZq-Xvj9p2TnhBFoFTsY-UoYGmG and unzip into "
                f"{self.sqlite_db_dir}/"
            )
        url = f"sqlite+aiosqlite:///{db_path}"
        return await SQLConnector.from_url_async(
            f"spider2-lite+{db_name}",
            db_name,
            "async",
            url,
            max_concurrency_per_db=4,
        )

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> dict[str, BaseSQLDBConnector]:
        """Return DB connectors keyed by database name.

        Dispatches to BigQuery, Snowflake, or SQLite based on the resource
        directory layout.
        """
        if split not in self.splits:
            raise ValueError(
                f"Split {split} not supported, only {self.splits} are supported for {self.name}"
            )

        databases = databases or self.get_databases(split)
        column_descriptions = self._load_column_descriptions()

        connectors: dict[str, BaseSQLDBConnector] = {}
        for db_name in databases:
            backend = self._get_backend(db_name)
            logger.info(f"Building connector for {db_name} (backend={backend})")

            if backend == "bigquery":
                project_datasets = self._get_bq_project_datasets(db_name)
                conn = await self._build_bq_connector(db_name, project_datasets)
            elif backend == "snowflake":
                conn = await self._build_sf_connector(db_name)
            elif backend == "sqlite":
                conn = await self._build_sqlite_connector(db_name)
            else:
                raise ValueError(f"Unknown backend {backend!r} for {db_name}")

            for table in conn.schema.tables:
                for column in table.columns:
                    desc = column_descriptions.get(
                        (db_name, table.name, column.name)
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
