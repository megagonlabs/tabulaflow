"""Spider 2.0-Lite dataset loader.

Spider 2.0-Lite provides 547 examples across BigQuery, Snowflake, and SQLite.
See https://spider2-sql.github.io/
"""

import dataclasses
import os
import json
import logging
import random
import re
import asyncio
from urllib.parse import quote_plus
from typing import Any, ClassVar, Literal, Optional
import pandas as pd
from mintq.schema import SimpleNL2QTask, NL2QDataset, GoldQuery, ExecResult
from mintq.db_connector import SQLConnector, BaseSQLDBConnector
from mintq.datahub.base import dataset_registry

logger = logging.getLogger(__name__)


# Match spider2-snow behavior for unavailable Snowflake databases.
EXCLUDE_DBS = [
    "AMAZON_VENDOR_ANALYTICS__SAMPLE_DATASET",
    "NETHERLANDS_OPEN_MAP_DATA",
    "open_targets_genetics_1",  # BigQuery dataset deprecated July 2025
]

# Patches for spider2lite_eval.jsonl where condition_cols length does not match
# the number of exec_result CSV files, or column indices are out of range for
# some CSVs (upstream data inconsistency).
EVAL_STANDARD_PATCHES = {
    "sf_bq236": {"condition_cols": [[0, 4], [0], [0]]},
    "bq060": {"condition_cols": [[1], [3], [2], [1], [1]]},
    "bq169": {"condition_cols": [[1, 3, 7, 8, 13], [0, 1, 13], [1, 3, 7, 8, 13], [1, 3, 7, 8, 13]]},
    "bq389": {"condition_cols": [[1, 2, 3, 4, 5, 6], [3], [2], [1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6], [2], [2]]},
}

# sqlite/ directory names that differ from the canonical JSONL db names.
_SQLITE_DIR_ALIASES: dict[str, str] = {
    "DB_IMDB": "Db-IMDB",
    "SQLITE_SAKILA": "sqlite-sakila",
}


@dataclasses.dataclass
class _DBInfo:
    """Metadata for a spider2-lite database."""

    backend: Literal["bigquery", "snowflake", "sqlite"]
    bq_project_datasets: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    """(project, dataset) pairs; only populated for bigquery backends."""


SPIDER2_LITE_DATASET_INSTRUCTIONS = """
- **Dialect-Specific Syntax Only:**
  - Use only functions and syntax supported by the corresponding dialect.
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
        google_cloud_project: Optional[str] = None,
        google_application_credentials: Optional[str] = None,
    ):
        """Initializes the Spider 2.0-Lite dataset loader.

        Args:
            directory: Path to the spider2-lite data directory.
            sf_user: Snowflake username. Falls back to ``SF_USER`` env var.
            sf_password: Snowflake password. Falls back to ``SF_PASSWORD`` env var.
            sf_account: Snowflake account identifier. Falls back to ``SF_ACCOUNT``
                env var.
            google_cloud_project: GCP project used for BigQuery billing. Falls
                back to ``GOOGLE_CLOUD_PROJECT`` env var.
            google_application_credentials: Path to a GCP service account JSON
                key file. Falls back to ``GOOGLE_APPLICATION_CREDENTIALS`` env var.
        """
        self.directory = directory
        self.sf_user = sf_user
        self.sf_password = sf_password
        self.sf_account = sf_account
        self.google_cloud_project = google_cloud_project
        self.google_application_credentials = google_application_credentials
        self._sf_semaphore = asyncio.Semaphore(16)
        self._bq_semaphore = asyncio.Semaphore(64)
        self._db_info = self._build_db_info()

    def _build_db_info(self) -> dict[str, _DBInfo]:
        """Scan resource directories once to build a backend mapping for every db."""
        resource_dir = os.path.join(self.directory, "resource", "databases")
        info: dict[str, _DBInfo] = {}
        for backend in ("bigquery", "snowflake", "sqlite"):
            backend_dir = os.path.join(resource_dir, backend)
            if not os.path.isdir(backend_dir):
                continue
            for db_name in sorted(os.listdir(backend_dir)):
                db_path = os.path.join(backend_dir, db_name)
                if not os.path.isdir(db_path):
                    continue
                bq_project_datasets: list[tuple[str, str]] = []
                if backend == "bigquery":
                    for entry in sorted(os.listdir(db_path)):
                        if os.path.isdir(os.path.join(db_path, entry)) and "." in entry:
                            project, dataset = entry.split(".", 1)
                            bq_project_datasets.append((project, dataset))
                info[db_name] = _DBInfo(
                    backend=backend,
                    bq_project_datasets=bq_project_datasets,
                )

        for old, new in _SQLITE_DIR_ALIASES.items():
            if old in info and new not in info:
                info[new] = info.pop(old)

        return info

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        jsonl_path = os.path.join(self.directory, "spider2-lite.jsonl")
        if not os.path.exists(jsonl_path):
            return []

        with open(jsonl_path, "r") as f:
            dbs = list(dict.fromkeys([json.loads(line)["db"] for line in f]))
            dbs = [db for db in dbs if db not in EXCLUDE_DBS]
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

        eval_standard_file = os.path.join(eval_dir, "spider2lite_eval.jsonl")
        eval_standard: dict[str, Any] = {}
        if os.path.exists(eval_standard_file):
            with open(eval_standard_file, "r") as f:
                for line in f:
                    eval_item = json.loads(line)
                    qid = eval_item.pop("instance_id")
                    if qid in EVAL_STANDARD_PATCHES:
                        eval_item.update(EVAL_STANDARD_PATCHES[qid])
                    eval_standard[qid] = eval_item

        tasks = []
        with open(jsonl_path, "r") as f:
            for line in f:
                item = json.loads(line)
                if item["db"] not in databases:
                    continue

                if item.get("external_knowledge"):
                    document_file = os.path.join(self.directory, "resource", "documents", item["external_knowledge"])
                    if os.path.exists(document_file):
                        with open(document_file, "r") as docf:
                            document = docf.read()
                    else:
                        document = None
                else:
                    document = None

                gold_sql_file = os.path.join(eval_dir, "sql", item["instance_id"] + ".sql")
                if os.path.exists(gold_sql_file):
                    with open(gold_sql_file, "r") as gf:
                        gold_sql = gf.read()
                else:
                    gold_sql = None

                pattern = re.compile(rf"^{re.escape(item['instance_id'])}(_[a-z])?\.csv$")
                gold_exec_result_files = [f for f in all_gold_exec_result_files if re.match(pattern, f)]
                gold_exec_result_files = sorted(gold_exec_result_files)
                gold_exec_results = []
                for file in gold_exec_result_files:
                    with open(os.path.join(exec_result_dir, file), "r") as rf:
                        gold_exec_results.append(pd.read_csv(rf))

                condition_cols = eval_standard.get(item["instance_id"], {}).get("condition_cols", [])
                if not condition_cols or not isinstance(condition_cols[0] if condition_cols else None, list):
                    condition_cols = [condition_cols for _ in range(max(1, len(gold_exec_results)))]

                if gold_exec_results:
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
                else:
                    primary = ExecResult(df=pd.DataFrame())
                    alternatives = []
                    primary_required_columns = None

                ignore_order = eval_standard.get(item["instance_id"], {}).get("ignore_order", False)

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
                            required_columns=primary_required_columns,
                            required_sorted=not ignore_order,
                        ),
                    )
                )

        return tasks

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
            for dir_name in os.listdir(backend_dir):
                db_path = os.path.join(backend_dir, dir_name)
                if not os.path.isdir(db_path):
                    continue
                db_name = _SQLITE_DIR_ALIASES.get(dir_name, dir_name) if backend == "sqlite" else dir_name
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

    async def _build_bigquery_connector(self, db_name: str, db_info: _DBInfo) -> SQLConnector:
        """Build a BigQuery SQLConnector for a spider2-lite database.

        Uses ``billing_project_id`` so that BigQuery jobs are billed to our
        GCP project while the data project in the URL is used for schema
        introspection and table resolution.  A single engine handles
        multi-dataset dbs because the inspector accepts an explicit
        ``schema`` argument that overrides the default dataset.
        """
        google_cloud_project = self.google_cloud_project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not google_cloud_project:
            raise ValueError("BigQuery billing project required: set google_cloud_project or GOOGLE_CLOUD_PROJECT")
        google_application_credentials = self.google_application_credentials or os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )

        projects = set(p for p, d in db_info.bq_project_datasets)
        if len(projects) > 1:
            raise ValueError(f"Multiple BigQuery projects not supported for {db_name}: {projects}")

        project = db_info.bq_project_datasets[0][0]
        datasets = [d for _, d in db_info.bq_project_datasets]

        engine_kwargs: dict[str, Any] = {}
        if google_application_credentials:
            engine_kwargs["credentials_path"] = google_application_credentials
        engine_kwargs["billing_project_id"] = google_cloud_project

        url = f"bigquery://{project}/{datasets[0]}"
        return await SQLConnector.from_url_async(
            f"spider2-lite+{db_name}",
            project,
            "sync",
            url,
            max_concurrency_per_db=8,
            dbms_semaphore=self._bq_semaphore,
            include_schema_names=datasets,
            group_date_partitioned_tables=True,
            **engine_kwargs,
        )

    async def _build_snowflake_connector(self, db_name: str) -> SQLConnector:
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
        sqlite_db_dir = os.path.join(self.directory, "resource", "databases", "spider2-localdb")
        db_path = os.path.join(sqlite_db_dir, f"{db_name}.sqlite")
        if not os.path.exists(db_path):
            raise FileNotFoundError(
                f"SQLite database not found: {db_path}. "
                "See https://github.com/xlang-ai/Spider2/tree/main/spider2-lite#quickstart "
                f"to download and unzip the local databases into {sqlite_db_dir}/"
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
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        column_descriptions = self._load_column_descriptions()

        connectors: dict[str, BaseSQLDBConnector] = {}
        for db_name in databases:
            db_info = self._db_info.get(db_name)
            if db_info is None:
                raise ValueError(f"No backend found for database {db_name!r}")

            if db_info.backend == "bigquery":
                conn = await self._build_bigquery_connector(db_name, db_info)
            elif db_info.backend == "snowflake":
                conn = await self._build_snowflake_connector(db_name)
            elif db_info.backend == "sqlite":
                conn = await self._build_sqlite_connector(db_name)
            else:
                raise ValueError(f"Unknown backend {db_info.backend!r} for {db_name}")

            for table in conn.schema.tables:
                for column in table.columns:
                    desc = column_descriptions.get((db_name, table.name, column.name))
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
