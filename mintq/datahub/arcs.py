import os
import json
import random
import asyncio
from typing import Optional, Any, Literal
from mintq.schema import SimpleNL2QTask, NL2QDataset
from mintq.db_connector import SQLConnector


class ARCSDatasetLoader:
    name = "arcs"

    def __init__(
        self,
        directory: str = "data/ARCS/",
        column_meaning_directory: str = "data/BIRD-SQL_column_meaning",
    ):
        self.directory = directory
        self.column_meaning_directory = column_meaning_directory
        self._split_data: dict[str, NL2QDataset] = {}
        self._dbms_semaphore = asyncio.Semaphore(1)

    async def _load_tasks_async(self, split_id: str) -> list[SimpleNL2QTask]:
        return []

    async def _load_databases_async(self, databases: list[str]) -> dict[str, SQLConnector]:
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
        self, split_id: str, databases: Optional[list[str]] = None, database_only: bool = False
    ) -> NL2QDataset:
        if split_id not in self._split_data:
            self._split_data[split_id] = NL2QDataset(
                name=self.name,
                split_id=split_id,
                tasks=[],
                db_connectors={},
            )

        dataset = self._split_data[split_id]
        if not dataset.tasks and not database_only:
            dataset.tasks = await self._load_tasks_async(split_id)

        if databases is None:
            databases = await self._get_all_databases_async()
        missing_databases = sorted(set(databases) - set([task.db for task in dataset.tasks]))
        if missing_databases:
            dataset.db_connectors.update(await self._load_databases_async(missing_databases))

        return NL2QDataset(
            name=self.name,
            split_id=split_id,
            tasks=dataset.tasks,
            db_connectors={db: dataset.db_connectors[db] for db in databases},
        )
