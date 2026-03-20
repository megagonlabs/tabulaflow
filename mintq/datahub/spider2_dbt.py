"""Spider 2.0-DBT dataset loader.

Spider 2.0-DBT provides 67 DuckDB data-transformation projects evaluated via
``duckdb_match``.  Each example consists of a dbt project directory, a natural-
language instruction, and a gold DuckDB database for evaluation.

See ``data/Spider2/spider2-dbt/README.md`` for setup instructions.
"""

import asyncio
import json
import logging
import os
import random
import re
import shutil
from typing import Any, ClassVar

import duckdb

from mintq.datahub.base import dataset_registry
from mintq.db_connector import SQLConnector, BaseSQLDBConnector
from mintq.schema import DbtTask, DbtGoldTable, NL2QDataset

logger = logging.getLogger(__name__)

_DUCKDB_PATH_RE = re.compile(r"""path:\s*['"]?\.?/?([^'"\s]+\.duckdb)['"]?""")


def _db_name_from_profiles(project_dir: str) -> str:
    """Extract the ``.duckdb`` filename from ``profiles.yml``."""
    profiles_path = os.path.join(project_dir, "profiles.yml")
    if os.path.exists(profiles_path):
        with open(profiles_path) as f:
            m = _DUCKDB_PATH_RE.search(f.read())
            if m:
                return m.group(1)
    raise FileNotFoundError(f"Cannot determine DuckDB filename from {profiles_path}")


async def prepare_working_env_async(dataset: NL2QDataset, result_dir: str) -> None:
    """Copy each dbt project to a working directory and rewire db_connectors.

    For each ``DbtTask`` in *dataset*, this function:
    1. Copies ``project_dir`` → ``<result_dir>/working/<qid>``
    2. Sets ``task.working_dir`` to the copy
    3. Creates an empty DuckDB if the project has none yet
    4. Replaces ``dataset.db_connectors[task.db]`` with a read/write
       ``SQLConnector`` pointing to the duckdb file inside the copy

    Args:
        dataset: The dataset returned by
            :meth:`Spider2DbtDatasetLoader.get_split_async`.
        result_dir: Root output directory for the experiment run.
    """
    for task in dataset.tasks:
        if not isinstance(task, DbtTask):
            continue
        working_dir = os.path.join(result_dir, "working", task.qid)
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
            db_name=task.db,
            engine_type="sync",
            url=f"duckdb:///{working_db_path}",
            max_concurrency_per_db=4,
            schema=existing_schema,
            read_only=False,
            enable_caching=False,
        )
        dataset.db_connectors[task.db] = conn


@dataset_registry.register
class Spider2DbtDatasetLoader:
    """Loader for Spider 2.0-DBT (DuckDB dbt transformation tasks)."""

    name: ClassVar = "spider2-dbt"
    splits: ClassVar = ["test"]

    def __init__(
        self,
        directory: str = "data/Spider2/spider2-dbt",
        max_concurrency: int = 16,
    ):
        """Initializes the Spider 2.0-DBT dataset loader.

        Args:
            directory: Path to the spider2-dbt data directory.
            max_concurrency: Maximum concurrent DuckDB connections.
        """
        self.directory = directory
        self.max_concurrency = max_concurrency
        self._dbms_semaphore = asyncio.Semaphore(max_concurrency)

    def _jsonl_path(self) -> str:
        return os.path.join(self.directory, "examples", "spider2-dbt.jsonl")

    def _eval_jsonl_path(self) -> str:
        return os.path.join(self.directory, "evaluation_suite", "gold", "spider2_eval.jsonl")

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        jsonl_path = self._jsonl_path()
        if not os.path.exists(jsonl_path):
            return []

        with open(jsonl_path, "r") as f:
            return list(dict.fromkeys(json.loads(line)["instance_id"] for line in f))

    def _load_eval_spec(self) -> dict[str, dict[str, Any]]:
        """Load evaluation specifications keyed by instance_id."""
        eval_path = self._eval_jsonl_path()
        specs: dict[str, dict[str, Any]] = {}
        if os.path.exists(eval_path):
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
        if not os.path.exists(jsonl_path):
            return []

        tasks: list[DbtTask] = []
        with open(jsonl_path, "r") as f:
            for line in f:
                item = json.loads(line)
                instance_id = item["instance_id"]
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

                gold_db_name = params.get("gold")
                gold_db_path: str | None = None
                if gold_db_name:
                    gold_db_path = os.path.join(self.directory, "evaluation_suite", "gold", instance_id, gold_db_name)

                tasks.append(
                    DbtTask(
                        qid=instance_id,
                        db=instance_id,
                        question=item["instruction"],
                        project_dir=project_dir,
                        gold_tables=gold_tables,
                        gold_db_path=gold_db_path,
                    )
                )

        return tasks

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> dict[str, BaseSQLDBConnector]:
        """Return DuckDB connectors keyed by instance_id.

        Each dbt project directory contains a ``.duckdb`` file that serves as
        the source database for that project.
        """
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        connectors: dict[str, BaseSQLDBConnector] = {}

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
                db_name=instance_id,
                engine_type="sync",
                url=url,
                max_concurrency_per_db=4,
                dbms_semaphore=self._dbms_semaphore,
                read_only=True,
            )
            connectors[instance_id] = conn

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
