import os
import json
import random
import asyncio
from typing import Optional, Any, Literal
from mintq.schema import SimpleNL2QTask, NL2QDataset, GoldQuery
from mintq.db_connector import SQLConnector


class BirdSQLDatasetLoader:
    name = "bird-sql"
    splits = ["train", "dev"]

    def __init__(
        self,
        directory: str = "data/BIRD-SQL",
        column_meaning_directory: str = "data/BIRD-SQL_column_meaning",
    ):
        self.directory = directory
        self.column_meaning_directory = column_meaning_directory
        self._split_data: dict[str, NL2QDataset] = {}
        self._dbms_semaphore = asyncio.Semaphore(1)

    async def _load_tasks_async(self, split: str) -> list[SimpleNL2QTask]:
        tasks = []
        with open(os.path.join(self.directory, "dev_20240627" if split == "dev" else split, f"{split}.json"), "r") as f:
            for i, item in enumerate(json.load(f)):
                tasks.append(
                    SimpleNL2QTask(
                        qid=f"{self.name}_{split}_{i}",
                        language="SQLite",
                        db=item["db_id"],
                        question=item["question"],
                        evidence=item["evidence"],
                        gold_queries=[GoldQuery(id="GQRY", query=item["SQL"])],
                    )
                )
        return tasks

    async def _load_databases_async(self, split: str, databases: list[str]) -> dict[str, SQLConnector]:
        db_dir = os.path.join(self.directory, "dev_20240627" if split == "dev" else split, f"{split}_databases")
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    global_id=f"arcs+{name}",
                    db_name=name,
                    engine_type="async",
                    url=f"sqlite+aiosqlite:///{os.path.join(db_dir, name, f'{name}.sqlite')}",
                    max_concurrency_per_db=1,
                    dbms_semaphore=self._dbms_semaphore,
                )
                for name in databases
            ]
        )
        with open(os.path.join(self.column_meaning_directory, f"{split}_column_meaning.json"), "r") as f:
            column_descriptions = {
                key: value.strip().strip("#").strip().replace("\n", " ") for key, value in json.load(f).items()
            }
        for conn in db_connectors:
            for table in conn.schema.tables:
                for column in table.columns:
                    column.description = column_descriptions.get(f"{conn.schema.name}|{table.name}|{column.name}", None)
        return {name: conn for name, conn in zip(databases, db_connectors)}

    def _get_all_databases(self, split: str) -> list[str]:
        with open(os.path.join(self.directory, "dev_20240627" if split == "dev" else split, f"{split}.json"), "r") as f:
            return list(dict.fromkeys([item["db_id"] for item in json.load(f)]))

    async def get_split_async(
        self, split: str, databases: Optional[list[str]] = None, database_only: bool = False
    ) -> NL2QDataset:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        if split not in self._split_data:
            self._split_data[split] = NL2QDataset(
                name=self.name,
                split=split,
                subsample_size=None,
                tasks=[],
                db_connectors={},
            )

        dataset = self._split_data[split]
        if not dataset.tasks and not database_only:
            dataset.tasks = await self._load_tasks_async(split)

        if databases is None:
            databases = self._get_all_databases(split)
        missing_databases = sorted(set(databases) - set(dataset.db_connectors.keys()))
        if missing_databases:
            dataset.db_connectors.update(await self._load_databases_async(split, missing_databases))

        return NL2QDataset(
            name=self.name,
            split=split,
            subsample_size=None,
            tasks=dataset.tasks,
            db_connectors={db: dataset.db_connectors[db] for db in databases},
        )
