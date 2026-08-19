import os
import json
import random
import asyncio
from typing import Any, ClassVar
from tabulaflow.research.types import GoldQuery
from tabulaflow.research.types import SimpleNL2QTask, NL2QDataset
from tabulaflow.data import SQLConnector, SQLConnectorConfig
from tabulaflow.research.benchmarks.base import dataset_registry


@dataset_registry.register
class BeaverDatasetLoader:
    name: ClassVar = "beaver"
    splits: ClassVar = ["test"]
    default_metrics: ClassVar = [
        "simple_ex",
        "executable",
        "gold_executable",
        "gold_result_not_empty",
        "pred_success",
    ]

    def __init__(
        self,
        directory: str = "data/beaver",
        dw_port: int = 3311,
        nw_port: int = 3312,
        connector_config: SQLConnectorConfig | None = None,
    ):
        self.directory = directory
        self.dw_dbms_port = dw_port
        self.nw_dbms_port = nw_port
        self.connector_config = SQLConnectorConfig() if connector_config is None else connector_config
        self._data: dict[Any, NL2QDataset] = {}

    def get_databases(self, split: str) -> list[str]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        return [
            "dw",
            "csail_stata_cinder",
            "csail_stata_neutron",
            "csail_stata_glance",
            "csail_stata_nova",
            "keystone",
        ]

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> list[SimpleNL2QTask]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        tasks = []
        for file in ["dev_dw.json", "dev_nw.json"]:
            with open(os.path.join(self.directory, file), "r") as f:
                data = json.load(f)

            for i, item in enumerate(data):
                if item["db_id"] in databases:
                    tasks.append(
                        SimpleNL2QTask(
                            qid=f"{self.name}_{split}_{i}",
                            db=item["db_id"],
                            question=item["question"],
                            document=None,
                            gold_query=GoldQuery(query=item["sql"]),
                        )
                    )
        return tasks

    async def get_db_connectors_async(self, split: str, databases: list[str] | None = None) -> dict[str, SQLConnector]:
        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        databases = databases or self.get_databases(split)
        urls = {
            db: f"mysql+asyncmy://root:root@localhost:{self.dw_dbms_port if db == 'dw' else self.nw_dbms_port}/{db}"
            for db in databases
        }
        db_connectors = await asyncio.gather(
            *[
                SQLConnector.from_url_async(
                    url,
                    global_id=f"beaver+{name}",
                    db_name=name,
                    config=self.connector_config.model_copy(update={"max_query_concurrency": 16}),
                )
                for name, url in urls.items()
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
