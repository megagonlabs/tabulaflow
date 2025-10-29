import os
import asyncio
import random
import json
import copy
from typing import ClassVar
from mintq.schema import AmbigNL2QTask, NL2QDataset
from mintq.db_connector import SQLConnector
from mintq.datahub.base import dataset_registry


@dataset_registry.register
class ARCSDatasetLoader:
    name: ClassVar = "arcs"
    splits: ClassVar = ["test", "test_unsampled"]

    def __init__(
        self,
        directory: str = "data/ARCS/",
        column_meaning_directory: str = "data/BIRD-SQL_column_meaning",
        max_concurrency: int = 16,
    ):
        self.directory = directory
        self.column_meaning_directory = column_meaning_directory
        self.max_concurrency = max_concurrency
        self._dbms_semaphore = asyncio.Semaphore(max_concurrency)

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        return [
            "retails",
            "professional_basketball",
            "github_repos",
            "financial",
            "codebase_community",
            "student_club",
        ]

    def _upsample_tasks(self, tasks: list[AmbigNL2QTask]) -> list[AmbigNL2QTask]:
        with open(os.path.join(self.directory, "tasks", "tasks_gold_intended_query_ids.json"), "r") as f:
            qid_to_gold_query_ids = json.load(f)

        res = []
        for task in tasks:
            for i, gq_id in enumerate(qid_to_gold_query_ids[task.qid]):
                new_task = copy.deepcopy(task)
                new_task.qid = f"{task.qid}-{i}"
                new_task.gold_intended_query_id = gq_id
                ap_id_to_interpretation_idx = dict([part.split(".") for part in gq_id.split("-")[1:]])
                for ap in new_task.gold_ambiguity_points:
                    if ap.type == "finite":
                        ap.intended_interpretation_idx = int(ap_id_to_interpretation_idx[ap.id])
                res.append(new_task)
        return res

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[AmbigNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        with open(os.path.join(self.directory, "tasks", "tasks_unsampled.json"), "r") as f:
            tasks = [AmbigNL2QTask.model_validate(dic) for dic in json.load(f)]
        tasks = [task for task in tasks if task.db in databases]
        if split == "test":
            tasks = self._upsample_tasks(tasks)
        return tasks

    async def get_db_connectors_async(self, split: str, databases: list[str] | None = None) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    global_id=f"arcs+{name}",
                    db_name=name,
                    engine_type="async",
                    url=f"sqlite+aiosqlite:///{os.path.join(self.directory, 'databases', 'sqlite', f'{name}.sqlite')}",
                    max_concurrency_per_db=self.max_concurrency,
                    dbms_semaphore=self._dbms_semaphore,
                )
                for name in databases
            ]
        )

        with open(os.path.join(self.directory, "databases", "column_meanings.json"), "r") as f:
            column_descriptions = {
                key: value.strip().strip("#").strip().replace("\n", " ") for key, value in json.load(f).items()
            }
        for conn in db_connectors:
            for table in conn.schema.tables:
                for column in table.columns:
                    column.description = column_descriptions.get(f"{conn.schema.name}|{table.name}|{column.name}", None)
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
