import os
import asyncio
import random
from pydantic import TypeAdapter
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
        self._dbms_semaphore = asyncio.Semaphore(1)

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

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[AmbigNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        with open(os.path.join(self.directory, "all_tasks.json"), "r") as f:
            tasks = TypeAdapter(list[AmbigNL2QTask]).validate_json(f.read())
        return [task for task in tasks if task.db in databases]

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
                    url=f"sqlite+aiosqlite:///{os.path.join(self.directory, 'databases', f'{name}.sqlite')}",
                    max_concurrency_per_db=1,
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
