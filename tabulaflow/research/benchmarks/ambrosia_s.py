import os
import asyncio
import json
from typing import ClassVar

import pandas as pd

from tabulaflow.research.types import AmbigNL2QTask, NL2QDataset
from tabulaflow.data import SQLConnector, SQLConnectorConfig
from tabulaflow.research.benchmarks.registry import dataset_registry, select_tasks, selected_databases
from tabulaflow.research.benchmarks.installation import DEFAULT_BENCHMARK_DIR, require_benchmark_downloaded


AMBROSIA_TAXONOMY = """
- In this dataset, the ambiguity point in the question is one of the following three types:

1. Scope Ambiguity
   Definition: Uncertainty about how widely a quantifier, such as "each", "every", or "all", applies.
   Example:
     Question: “What activities does each gym offer?”
     Possible interpretations:
       - Show only classes common to all gyms.
       - For each gym, show the classes offered at that specific gym.

2. Attachment Ambiguity
   Definition: Uncertainty about which entity a modifier or phrase attaches to, also known as PP attachment ambiguity.
   Example:
     Question: “Show the writers and editors on a work-for-hire.”
     Possible interpretations:
       - Work-for-hire writers and work-for-hire editors.
       - All writers, and work-for-hire editors.

3. Vagueness
   Definition: The question can plausibly refer to multiple query targets in the schema, where the intended meaning could be either of them individually or both of them together.
   Example:
     Question: “Who issued CD Special?”
     Possible interpretations:
       - Which bank issued CD Special?
       - Which branch issued CD Special?
       - Find the bank and branch that issued CD Special.
""".strip()

AMBROSIA_DATASET_INSTRUCTIONS = """
- Do not concatenate columns in the results unless explicitly requested.
- Each question has exactly one ambiguity point.
- There are no parameter ambiguity points.
""".strip()


@dataset_registry.register
class AmbrosiaSDatasetLoader:
    name: ClassVar[str] = "ambrosia-s"
    splits: ClassVar[list[str]] = ["test", "few_shot_examples"]
    default_metrics: ClassVar[list[str]] = [
        "simple_ex",
        "executable",
        "gold_executable",
        "gold_result_not_empty",
        "pred_success",
        "ambig_point_stats",
        "gold_ambig_point_stats",
        "found_one",
    ]

    def __init__(
        self,
        directory: str | None = None,
        max_concurrency: int = 16,
        include_taxonomy: bool = False,
        connector_config: SQLConnectorConfig | None = None,
    ):
        if directory is None:
            require_benchmark_downloaded(self.name)
        self.directory = str(DEFAULT_BENCHMARK_DIR / self.name if directory is None else directory)
        self.max_concurrency = max_concurrency
        self.include_taxonomy = include_taxonomy
        self.connector_config = SQLConnectorConfig() if connector_config is None else connector_config

        self._dbms_semaphore = asyncio.Semaphore(max_concurrency)

        self.db_list: list[str] = []
        with open(os.path.join(self.directory, "db_list.txt"), "r") as f:
            self.db_list = [line.strip() for line in f.readlines() if line.strip()]

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        return self.db_list

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[AmbigNL2QTask]:
        """
        Load tasks from JSON and transform to AmbigNL2QTask schema.

        Args:
            split: Dataset split to load
            databases: Optional list of databases to filter

        Returns:
            List of validated AmbigNL2QTask instances
        """
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        dataset_instructions = AMBROSIA_DATASET_INSTRUCTIONS
        if self.include_taxonomy:
            dataset_instructions += "\n" + AMBROSIA_TAXONOMY

        databases = self.get_databases(split) if databases is None else databases
        with open(os.path.join(self.directory, f"ambrosia_{split}_processed.json"), "r") as f:
            data = []
            for task_idx, task in enumerate(json.load(f)):
                # Skip tasks with "other" ambiguity type
                if task.get("gold_ambiguity_points"):
                    has_other_type = False
                    for ap in task["gold_ambiguity_points"]:
                        ambig_type = ap.get("ambiguity_type", "").replace("_ambiguity", "")
                        if ambig_type == "other":
                            has_other_type = True
                            break
                    if has_other_type:
                        continue

                # Transform gold_queries if present
                if task.get("gold_queries"):
                    # Transform gold execution results to pd.DataFrame
                    for gold_query in task["gold_queries"]:
                        if not gold_query.get("exec_result"):
                            continue
                        exec_result = gold_query["exec_result"]
                        gold_query["exec_result"] = {
                            "df": pd.DataFrame.from_records(exec_result),
                            "error": None,
                            "latency_seconds": None,
                        }

                task["dataset_instructions"] = dataset_instructions
                data.append(task)

            tasks = [AmbigNL2QTask.model_validate(dic) for dic in data]
        return [task for task in tasks if task.db in databases]

    async def get_db_connectors_async(self, split: str, databases: list[str] | None = None) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = self.get_databases(split) if databases is None else databases
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    global_id=f"ambrosia-s+{name.replace('/', '___')}",
                    url=f"sqlite+aiosqlite:///{os.path.join(self.directory, 'ambrosia', f'{name}.sqlite')}",
                    db_name=name,
                    dbms_semaphore=self._dbms_semaphore,
                    # 846 databases are opened concurrently; larger pools exceed the OS file limit.
                    config=self.connector_config.model_copy(update={"max_query_concurrency": 1}),
                )
                for name in databases
            ]
        )

        return {name: conn for name, conn in zip(databases, db_connectors)}

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
