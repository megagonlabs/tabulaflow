import os
import asyncio
import random
import json
from typing import ClassVar

import pandas as pd

from mintq.schema import AmbigNL2QTask, NL2QDataset
from mintq.db_connector import SQLConnector
from mintq.datahub.base import dataset_registry


@dataset_registry.register
class AmbrosiaSDatasetLoader:
    name: ClassVar = "ambrosia_s"
    splits: ClassVar = ["test", "few_shot_examples"]

    def __init__(
        self,
        directory: str = "data/ambrosia_s/",
    ):
        self.directory = directory
        self._dbms_semaphore = asyncio.Semaphore(4)

        # Actual DB (.sqlite) location: data/ambrosia_s/ambrosia/<db_name>.sqlite
        self.db_list: list[str] = []
        with open(directory + "/db_list.txt", "r") as f:
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

        databases = databases or self.get_databases(split)
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
                            "df_is_truncated": False,
                            "error": None,
                            "latency_seconds": None
                        }

                data.append(task)

            tasks = [AmbigNL2QTask.model_validate(dic) for dic in data]
        return [task for task in tasks if task.db in databases]

    async def get_db_connectors_async(self, split: str, databases: list[str] | None = None) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    global_id=f"ambrosia_s+{name.replace('/', '___')}",
                    db_name=name,
                    engine_type="async",
                    url=f"sqlite+aiosqlite:///{os.path.join(self.directory, 'ambrosia', f'{name}.sqlite')}",
                    max_concurrency_per_db=4,
                    dbms_semaphore=self._dbms_semaphore,
                )
                for name in databases
            ]
        )

        return {name: conn for name, conn in zip(databases, db_connectors)}

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
