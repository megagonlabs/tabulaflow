import os
import json
import asyncio
import random
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
        self._dbms_semaphore = asyncio.Semaphore(1)

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        with open(os.path.join(self.directory, "dev_20240627" if split == "dev" else split, f"{split}.json"), "r") as f:
            return list(dict.fromkeys([item["db_id"] for item in json.load(f)]))

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[SimpleNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        tasks = []
        with open(os.path.join(self.directory, "dev_20240627" if split == "dev" else split, f"{split}.json"), "r") as f:
            for i, item in enumerate(json.load(f)):
                if item["db_id"] in databases:
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

    async def get_db_connectors_async(self, split: str, databases: list[str] | None = None) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
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
            subsample_size=None,
            tasks=tasks,
            db_connectors=db_connectors,
        )
