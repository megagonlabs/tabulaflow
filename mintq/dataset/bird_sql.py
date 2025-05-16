import os
import json
import random
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from typing import Optional, Any
from mintq.schema import SimpleNL2QTask, NL2QDataset
from mintq.db_connector import SQLiteConnector, BaseDBConnector


def create_connector(args: tuple[str, type[BaseDBConnector], dict[str, Any]]) -> BaseDBConnector:
    name, conn_cls, kwargs = args
    return conn_cls(name, **kwargs)


class BirdSQLDatasetLoader:
    name = "bird-sql"

    def __init__(
        self,
        directory: str = "data/BIRD-SQL",
        num_threads: int = 16,
    ):
        self.directory = directory
        self.num_threads = num_threads
        self._data = {}

    def _load_split(self, split: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        if split == "train":
            directory = os.path.join(self.directory, "train")
        elif split == "dev":
            directory = os.path.join(self.directory, "dev_20240627")
        else:
            raise ValueError(f"Split {split} not supported")

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
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            connector_args = [
                (
                    name,
                    SQLiteConnector,
                    {"sqlite_db_path": os.path.join(db_dir, name, f"{name}.sqlite")},
                )
                for name in db_names
            ]
            db_connectors = {
                conn.name: conn
                for conn in tqdm(
                    tqdm(
                        executor.map(create_connector, connector_args),
                        total=len(connector_args),
                        desc="Creating database connectors",
                    )
                )
            }

        return NL2QDataset(
            name=self.name,
            split_id=split,
            databases=databases,
            tasks=tasks,  # type: ignore[arg-type]
            db_connectors=db_connectors,
        )

    def get_split(self, split_id: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        if "_" in split_id:
            split, sample_size = split_id.split("_")
        else:
            split, sample_size = split_id, None

        if sample_size and databases:
            raise ValueError("sample_size and databases cannot be both specified")

        key = tuple(sorted(databases)) if isinstance(databases, list) else None

        if (split, key) not in self._data:
            self._data[(split, key)] = self._load_split(split, databases=databases)

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
