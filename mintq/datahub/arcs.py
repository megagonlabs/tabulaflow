import os
import json
import random
import asyncio
from typing import Optional, Any, Literal
from mintq.schema import AmbigNL2QTask, NL2QDataset
from mintq.db_connector import SQLConnector
from mintq.datahub.base import GetSplitMixin


class ARCSDatasetLoader(GetSplitMixin):
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
        return [
            "retails",
            "professional_basketball",
            "github_repos",
            "financial",
            "codebase_community",
            "student_club",
        ]

    async def get_tasks_async(self, split: str) -> list[AmbigNL2QTask]:
        return [AmbigNL2QTask.from_directory(os.path.join(self.directory, "tasks", f"{i:03d}")) for i in range(1, 102)]

    async def get_databases_async(self, split: str, databases: list[str]) -> dict[str, SQLConnector]:
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
