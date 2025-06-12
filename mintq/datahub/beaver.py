import os
import json
import random
import asyncio
from tqdm import tqdm
from typing import Optional, Any
from mintq.schema import SimpleNL2QTask, NL2QDataset
from mintq.db_connector import SQLConnector


class BeaverDatasetLoader:
    name = "beaver"

    def __init__(
        self,
        directory: str = "data/beaver",
    ):
        self.directory = directory
        self._data: dict[Any, NL2QDataset] = {}

    async def _load_split_async(self, split: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        if split != "dev":
            raise ValueError("Only dev split is supported for beaver")

        urls = {}
        tasks = []
        for file, port in [("dev_dw.json", 3311), ("dev_nw.json", 3312)]:
            with open(os.path.join(self.directory, file), "r") as f:
                data = json.load(f)

            for i, item in enumerate(data):
                if databases and item["db_id"] not in databases:
                    continue

                tasks.append(
                    SimpleNL2QTask(
                        qid=f"{self.name}_{split}_{i}",
                        language="MySQL",
                        db=item["db_id"],
                        question=item["question"],
                        evidence=None,
                        gold_queries=[item["sql"]],
                    )
                )

                if item["db_id"] not in urls:
                    urls[item["db_id"]] = f"mysql+asyncmy://root:root@localhost:{port}/{item['db_id']}"

        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(name, "async", url, pool_size=16)
                for name, url in urls.items()
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

        if sample_size and databases:
            raise ValueError("sample_size and databases cannot be both specified")

        key = tuple(sorted(databases)) if isinstance(databases, list) else None

        if (split, key) not in self._data:
            self._data[(split, key)] = await self._load_split_async(split, databases=databases)

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
