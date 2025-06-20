import os
import json
import random
import asyncio
from typing import Optional, Any, Literal
from mintq.schema import SimpleNL2QTask, NL2QDataset
from mintq.db_connector import SQLConnector


class BirdSQLDatasetLoader:
    name = "bird-sql"

    def __init__(
        self,
        directory: str = "data/BIRD-SQL",
    ):
        self.directory = directory
        self._data: dict[Any, NL2QDataset] = {}

    async def _load_split_async(
        self, split: Literal["train", "dev"], databases: Optional[list[str]] = None
    ) -> NL2QDataset:
        if split == "train":
            directory = os.path.join(self.directory, "train")
        elif split == "dev":
            directory = os.path.join(self.directory, "dev_20240627")

        tasks = []
        with open(os.path.join(directory, f"{split}.json"), "r") as f:
            data = json.load(f)

        for i, item in enumerate(data):
            if databases and item["db_id"] not in databases:
                continue

            tasks.append(
                SimpleNL2QTask(
                    qid=f"{self.name}_{split}_{i}",
                    language="SQLite",
                    db=item["db_id"],
                    question=item["question"],
                    evidence=item["evidence"],
                    gold_queries=[item["SQL"]],
                )
            )

        db_names = list(dict.fromkeys([task.db for task in tasks]))

        db_dir = os.path.join(directory, f"{split}_databases")
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    name,
                    "async",
                    f"sqlite+aiosqlite:///{os.path.join(db_dir, name, f'{name}.sqlite')}",
                    max_concurrency_per_db=4,
                )
                for name in db_names
            ]
        )

        return NL2QDataset(
            name=self.name,
            split_id=split,
            databases=databases,
            tasks=tasks,  # type: ignore
            db_connectors={conn.name: conn for conn in db_connectors},
        )

    async def get_split_async(self, split_id: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        if "_" in split_id:
            split, sample_size = split_id.split("_")
        else:
            split, sample_size = split_id, None

        if split not in ["train", "dev"]:
            raise ValueError(f"Split {split} not supported")

        if sample_size and databases:
            raise ValueError("sample_size and databases cannot be both specified")

        key = tuple(sorted(databases)) if isinstance(databases, list) else None

        if (split, key) not in self._data:
            self._data[(split, key)] = await self._load_split_async(split, databases=databases)  # type: ignore

        dataset = self._data[(split, key)]
        if sample_size:
            sampler = random.Random(42)
            return NL2QDataset(
                name=self.name,
                split_id=split_id,
                databases=databases,
                tasks=sampler.sample(dataset.tasks, int(sample_size)),
                db_connectors=dataset.db_connectors,
            )
        else:
            return dataset
