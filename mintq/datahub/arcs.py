import os
import asyncio
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

    def get_database_names(self, split: str) -> list[str]:
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

    async def get_tasks_async(self, split: str) -> list[AmbigNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        return [AmbigNL2QTask.from_directory(os.path.join(self.directory, "tasks", f"{i:03d}")) for i in range(1, 102)]

    async def get_databases_async(self, split: str, databases: list[str]) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

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
        return NL2QDataset(
            name=self.name,
            split=split,
            subsample_size=None,
            tasks=await self.get_tasks_async(split),
            db_connectors=await self.get_databases_async(split, databases or self.get_database_names(split)),
        )
