"""Spider 2.0-DBT dataset loader.

Spider 2.0-DBT provides 69 DuckDB data-transformation projects, 68 of which are
covered by the official evaluation specification. Each example consists of a
dbt project directory, a natural-language instruction, and a gold DuckDB
database for evaluation.

Install it with ``tabulaflow benchmark download spider2-dbt``.
"""

import asyncio
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, ClassVar

import duckdb

from tabulaflow.data import SQLConnector, SQLConnectorConfig, SQLConnectorProtocol
from tabulaflow.research.benchmarks.registry import dataset_registry, select_tasks, selected_databases
from tabulaflow.research.benchmarks.installation import (
    BenchmarkInstallation,
    ProgressCallback,
    download_github_directory,
    download_google_drive,
    extract_zip,
)
from tabulaflow.research.types import DbtGoldTable, DbtTask, NL2QDataset

SPIDER2_REVISION = "cafb867313aab4e674652054198f383cf4018943"
SPIDER2_DBT_DATABASE_URL = "https://drive.google.com/uc?id=1N3f7BSWC4foj-V-1C9n8M2XmgV7FOcqL"
SPIDER2_DBT_GOLD_URL = "https://drive.google.com/uc?id=1s0USV_iQLo4oe05QqAMnhGGp5jeejCzp"


def _install_dbt_databases(archive: Path, destination: Path) -> None:
    extracted = archive.with_suffix("")
    if extracted.exists():
        shutil.rmtree(extracted)
    extract_zip(archive, extracted)
    for directory in extracted.iterdir():
        if not directory.is_dir() or directory.name == "__MACOSX":
            continue
        for database in directory.rglob("*.duckdb"):
            target = destination / directory.name
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(database, target / database.name)
    shutil.rmtree(extracted)


async def _fetch_spider2_dbt(destination: Path, progress: ProgressCallback) -> None:
    progress("Downloading Spider 2.0 DBT")
    await download_github_directory("xlang-ai/Spider2", SPIDER2_REVISION, "spider2-dbt", destination)
    downloads = (
        (SPIDER2_DBT_DATABASE_URL, destination / ".dbt-start.zip", destination / "examples"),
        (SPIDER2_DBT_GOLD_URL, destination / ".dbt-gold.zip", destination / "evaluation_suite" / "gold"),
    )
    for url, archive, target in downloads:
        if any(target.rglob("*.duckdb")) and not archive.exists():
            continue
        progress(f"Downloading {archive.stem.removeprefix('.')} databases")
        if not archive.exists():
            await download_google_drive(url, archive)
        await asyncio.to_thread(_install_dbt_databases, archive, target)
        archive.unlink()


logger = logging.getLogger(__name__)

_DUCKDB_PATH_RE = re.compile(r"""path:\s*['"]?\.?/?([^'"\s]+\.duckdb)['"]?""")


# The gold evaluation databases were generated on 2024-09-08. Many dbt models
# use current_timestamp / current_date for time-dependent computations (e.g.
# account_active_months, date spines, past-due amounts). Running at any other
# date produces values that differ from the gold, causing duckdb_match to fail.
SPIDER2_DBT_DATASET_INSTRUCTIONS = """
- **Interpreting Ambiguities:**
  - When the task is ambiguous, follow the most natural interpretation based on the starting files. Pay close attention to YAML column descriptions and existing SQL patterns.
- **Follow Existing Patterns:**
  - Read ALL existing SQL files carefully. Your new models must follow the same patterns, conventions, macro usage, and coding style.
- **Choosing Between Overlapping Data Sources:**
  - When multiple tables contain similar information, prefer the source with more complete coverage.
    Check row counts and date ranges before committing to a source table.
  - Be consistent: if you use a particular data source for one model, use the same source for all models that compute the same metric.
- **Percentage and Ratio Columns:**
  - Follow existing SQL patterns to determine whether a value should be on a 0-1 or 0-100 scale.
  - If the scale cannot be determined from existing SQL, by default percentage should be on a 0-100 scale (i.e. multiply by 100) while ratio or rate should be on a 0-1 scale.
""".strip()


# - **Data Types:**
#   - Do NOT cast source columns to different types (e.g. do NOT cast VARCHAR to TIMESTAMP using `dbt.type_timestamp()`). Keep the original data formats from the source tables unless explicitly requested.


# - **Time-Dependent Models:**
#   - You must treat the current date as **2024-09-08** to match the gold evaluation data.
#     Do NOT leave any `current_timestamp` or `current_date` calls in the SQL.


def _db_name_from_profiles(project_dir: str) -> str:
    """Extract the ``.duckdb`` filename from ``profiles.yml``."""
    profiles_path = os.path.join(project_dir, "profiles.yml")
    if os.path.exists(profiles_path):
        with open(profiles_path) as f:
            m = _DUCKDB_PATH_RE.search(f.read())
            if m:
                return m.group(1)
    raise FileNotFoundError(f"Cannot determine DuckDB filename from {profiles_path}")


async def prepare_working_env_async(dataset: NL2QDataset, output_dir: str) -> None:
    """Copy each dbt project to a working directory and rewire db_connectors.

    For each ``DbtTask`` in *dataset*, this function:
    1. Copies ``project_dir`` → ``<output_dir>/working/<qid>``
    2. Sets ``task.working_dir`` to the copy
    3. Creates an empty DuckDB if the project has none yet
    4. Replaces ``dataset.db_connectors[task.db]`` with a read-only
       ``SQLConnector`` pointing to the duckdb file inside the copy

    Args:
        dataset: The dataset returned by
            :meth:`Spider2DbtDatasetLoader.get_split_async`.
        output_dir: Root output directory for the experiment run.
    """
    for task in dataset.tasks:
        if not isinstance(task, DbtTask):
            continue
        working_dir = os.path.join(output_dir, "working", task.qid)
        if os.path.exists(working_dir):
            shutil.rmtree(working_dir)
        shutil.copytree(task.project_dir, working_dir)
        task.working_dir = working_dir

        duckdb_files = [f for f in os.listdir(working_dir) if f.endswith(".duckdb")]
        if not duckdb_files:
            db_name = _db_name_from_profiles(working_dir)
            working_db_path = os.path.join(working_dir, db_name)
            duckdb.connect(database=working_db_path).close()
            logger.info("Created empty DuckDB at %s", working_db_path)
        else:
            working_db_path = os.path.join(working_dir, duckdb_files[0])

        original_conn = dataset.db_connectors.get(task.db)
        original_global_id = original_conn.global_id if original_conn is not None else f"spider2-dbt+{task.db}"
        existing_schema = original_conn.schema if original_conn is not None else None
        conn = await SQLConnector.from_url_async(
            global_id=original_global_id,
            url=f"duckdb:///{working_db_path}",
            db_name=task.db,
            schema=existing_schema,
            read_only=True,
            config=SQLConnectorConfig(
                max_query_concurrency=4,
                schema_cache_mode="off",
                query_cache_mode="off",
            ),
        )
        dataset.db_connectors[task.db] = conn


# The manifest and official evaluation contain 68 instances. These four lack
# local gold DuckDBs, so the loader returns 64 and the official-split score,
# whose denominator remains 68, currently has a maximum of 64/68.
EXCLUDE_INSTANCES = ["airbnb002", "biketheft001", "google_ads001", "gitcoin001"]


@dataset_registry.register
class Spider2DbtDatasetLoader:
    """Loader for Spider 2.0-DBT (DuckDB dbt transformation tasks)."""

    name: ClassVar[str] = "spider2-dbt"
    splits: ClassVar[list[str]] = ["test"]
    installation: ClassVar[BenchmarkInstallation] = BenchmarkInstallation(
        name=name,
        required_paths=("examples/spider2-dbt.jsonl", "examples", "evaluation_suite/gold"),
        fetch=_fetch_spider2_dbt,
    )
    default_metrics: ClassVar[list[str]] = [
        "spider2_duckdb_match",
        "executable",
        "pred_success",
    ]

    def __init__(
        self,
        directory: str | None = None,
        max_concurrency: int = 16,
        connector_config: SQLConnectorConfig | None = None,
    ):
        """Initializes the Spider 2.0-DBT dataset loader.

        Args:
            directory: Path to the spider2-dbt data directory.
            max_concurrency: Maximum concurrent DuckDB connections.
        """
        if directory is None:
            self.installation.require()
        self.directory = str(self.installation.directory if directory is None else directory)
        self.max_concurrency = max_concurrency
        self.connector_config = SQLConnectorConfig() if connector_config is None else connector_config
        self._dbms_semaphore = asyncio.Semaphore(max_concurrency)

    def _jsonl_path(self) -> str:
        return os.path.join(self.directory, "examples", "spider2-dbt.jsonl")

    def _eval_jsonl_path(self) -> str:
        return os.path.join(self.directory, "evaluation_suite", "gold", "spider2_eval.jsonl")

    def _resolve_gold_db_path(self, instance_id: str, spec_name: str | None) -> str | None:
        """Resolve the gold DuckDB path, falling back to the actual file on disk.

        The eval spec ``gold`` field sometimes carries a stale filename that
        doesn't match the file actually present in the gold directory.  When the
        spec path doesn't exist, fall back to the single ``.duckdb`` file in the
        gold directory (if exactly one exists).
        """
        gold_dir = os.path.join(self.directory, "evaluation_suite", "gold", instance_id)
        if not os.path.isdir(gold_dir):
            return None

        if spec_name:
            spec_path = os.path.join(gold_dir, spec_name)
            if os.path.exists(spec_path):
                return spec_path

        duckdb_files = [f for f in os.listdir(gold_dir) if f.endswith(".duckdb")]
        if len(duckdb_files) == 1:
            resolved = os.path.join(gold_dir, duckdb_files[0])
            if spec_name:
                logger.info(
                    "Gold DB mismatch for %s: spec says %s, using %s",
                    instance_id,
                    spec_name,
                    duckdb_files[0],
                )
            return resolved

        return None

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        jsonl_path = self._jsonl_path()
        with open(jsonl_path, "r") as f:
            dbs = list(dict.fromkeys(json.loads(line)["instance_id"] for line in f))
            return [db for db in dbs if db not in EXCLUDE_INSTANCES]

    def _load_eval_spec(self) -> dict[str, dict[str, Any]]:
        """Load evaluation specifications keyed by instance_id."""
        eval_path = self._eval_jsonl_path()
        specs: dict[str, dict[str, Any]] = {}
        with open(eval_path, "r") as f:
            for line in f:
                item = json.loads(line)
                specs[item["instance_id"]] = item.get("evaluation", {})
        return specs

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[DbtTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases_set = set(databases) if databases else None
        eval_specs = self._load_eval_spec()

        jsonl_path = self._jsonl_path()
        tasks: list[DbtTask] = []
        with open(jsonl_path, "r") as f:
            for line in f:
                item = json.loads(line)
                instance_id = item["instance_id"]
                if instance_id in EXCLUDE_INSTANCES:
                    continue
                if databases_set is not None and instance_id not in databases_set:
                    continue

                project_dir = os.path.join(self.directory, "examples", instance_id)
                eval_spec = eval_specs.get(instance_id, {})
                params = eval_spec.get("parameters", {})

                condition_tabs = params.get("condition_tabs", [])
                condition_cols = params.get("condition_cols", [])
                ignore_orders = params.get("ignore_orders", [])

                gold_tables: list[DbtGoldTable] = []
                for i, tab in enumerate(condition_tabs):
                    cols = condition_cols[i] if i < len(condition_cols) else []
                    ignore_order = ignore_orders[i] if i < len(ignore_orders) else False
                    gold_tables.append(
                        DbtGoldTable(
                            table_name=tab,
                            required_columns=cols,
                            required_sorted=not ignore_order,
                        )
                    )

                gold_db_path = self._resolve_gold_db_path(instance_id, params.get("gold"))
                if not gold_db_path:
                    raise FileNotFoundError(
                        f"No gold DuckDB found for {instance_id} "
                        f"(spec says {params.get('gold')!r}). "
                        f"If this instance lacks gold data, add it to EXCLUDE_INSTANCES."
                    )

                tasks.append(
                    DbtTask(
                        qid=instance_id,
                        db=instance_id,
                        question=item["instruction"],
                        dataset_instructions=SPIDER2_DBT_DATASET_INSTRUCTIONS,
                        project_dir=project_dir,
                        gold_tables=gold_tables,
                        gold_db_path=gold_db_path,
                    )
                )

        return tasks

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> dict[str, SQLConnectorProtocol]:
        """Return DuckDB connectors keyed by instance_id.

        Each dbt project directory contains a ``.duckdb`` file that serves as
        the source database for that project.
        """
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = self.get_databases(split) if databases is None else databases
        connectors: dict[str, SQLConnectorProtocol] = {}

        for instance_id in databases:
            project_dir = os.path.join(self.directory, "examples", instance_id)
            duckdb_files = [f for f in os.listdir(project_dir) if f.endswith(".duckdb")]
            if not duckdb_files:
                logger.info("No .duckdb file found in %s, skipping", project_dir)
                continue
            if len(duckdb_files) > 1:
                logger.warning("Multiple .duckdb files in %s, using %s", project_dir, duckdb_files[0])
            db_path = os.path.join(project_dir, duckdb_files[0])
            url = f"duckdb:///{db_path}"
            conn = await SQLConnector.from_url_async(
                global_id=f"spider2-dbt+{instance_id}",
                url=url,
                db_name=instance_id,
                dbms_semaphore=self._dbms_semaphore,
                read_only=True,
                config=self.connector_config.model_copy(update={"max_query_concurrency": 4}),
            )
            connectors[instance_id] = conn

        return connectors

    async def get_split_async(
        self,
        split: str,
        databases: list[str] | None = None,
        subsample_size: int | None = None,
        qids: list[str] | None = None,
    ) -> NL2QDataset:
        tasks = select_tasks(await self.get_tasks_async(split, databases), qids, subsample_size)
        databases = selected_databases(tasks)
        db_connectors = await self.get_db_connectors_async(split, databases)
        return NL2QDataset(
            name=self.name,
            split=split,
            databases=databases,
            subsample_size=subsample_size,
            tasks=tasks,  # type: ignore
            db_connectors=db_connectors,
        )
