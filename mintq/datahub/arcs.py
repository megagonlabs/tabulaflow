import os
import json
import random
import asyncio
from typing import Optional, Any, Literal
from mintq.schema import AmbigNL2QTask, NL2QDataset
from mintq.db_connector import SQLConnector


class ARCSDatasetLoader:
    name = "arcs"
    splits = ["dev"]

    def __init__(
        self,
        directory: str = "data/ARCS/",
        column_meaning_directory: str = "data/BIRD-SQL_column_meaning",
    ):
        self.directory = directory
        self.column_meaning_directory = column_meaning_directory
        self._split_data: dict[str, NL2QDataset] = {}
        self._dbms_semaphore = asyncio.Semaphore(1)

    async def _load_tasks_async(self, split: str) -> list[AmbigNL2QTask]:
        return [AmbigNL2QTask.from_directory(os.path.join(self.directory, "tasks", f"{i:03d}")) for i in range(1, 102)]

    async def _load_databases_async(self, split: str, databases: list[str]) -> dict[str, SQLConnector]:
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    global_id=f"arcs+{name}",
                    db_name=name,
                    engine_type="async",
                    url=f"sqlite+aiosqlite:///{os.path.join(self.directory, 'databases', f'{name}.sqlite')}",
                    max_concurrency_per_db=1,
                    dbms_semaphore=self._dbms_semaphore,
                )
                for name in databases
            ]
        )
        return {name: conn for name, conn in zip(databases, db_connectors)}

    async def _get_all_databases_async(self) -> list[str]:
        return [
            "retails",
            "professional_basketball",
            "github_repos",
            "financial",
            "codebase_community",
            "student_club",
        ]

    async def get_split_async(
        self, split: str, databases: Optional[list[str]] = None, database_only: bool = False
    ) -> NL2QDataset:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        if split not in self._split_data:
            self._split_data[split] = NL2QDataset(
                name=self.name,
                split=split,
                tasks=[],
                db_connectors={},
            )

        dataset = self._split_data[split]
        if not dataset.tasks and not database_only:
            dataset.tasks = await self._load_tasks_async(split)

        if databases is None:
            databases = await self._get_all_databases_async()
        missing_databases = sorted(set(databases) - set([task.db for task in dataset.tasks]))
        if missing_databases:
            dataset.db_connectors.update(await self._load_databases_async(missing_databases))

        return NL2QDataset(
            name=self.name,
            split=split,
            tasks=dataset.tasks,
            db_connectors={db: dataset.db_connectors[db] for db in databases},
        )
