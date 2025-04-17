import os
import json
import random
import multiprocessing
from tqdm import tqdm
from rattq.dataset.base import NL2QDatasetLoader
from rattq.schema import SingleOutputBaseNL2QTask, NL2QDataset
from rattq.db_connector import SQLiteConnector


def create_connector(args):
    name, conn_cls, kwargs = args
    return conn_cls(name, **kwargs)


class BirdSQLDatasetLoader(NL2QDatasetLoader):
    def __init__(
        self,
        name: str = "bird-sql",
        directory: str = "data/BIRD-SQL",
        num_processes: int = 16,
    ):
        self.name = name
        self.directory = directory
        self.num_processes = num_processes
        self._data = {}

    def _load_split(self, split: str) -> NL2QDataset:
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
            tasks.append(
                SingleOutputBaseNL2QTask(
                    qid=f"{self.name}_{split}_{i}",
                    language="SQLite",
                    db=item["db_id"],
                    question=item["question"],
                    evidence=item["evidence"],
                    gold_query=item["SQL"],
                )
            )

        metadata_path = os.path.join(directory, f"{split}_tables.json")
        with open(metadata_path, "r") as f:
            db_names = [item["db_id"] for item in json.load(f)]

        db_dir = os.path.join(directory, f"{split}_databases")
        with multiprocessing.Pool(processes=self.num_processes) as pool:
            connector_args = [
                (
                    name,
                    SQLiteConnector,
                    {"sqlite_db_path": os.path.join(db_dir, name, f"{name}.sqlite")},
                )
                for name in db_names
            ]
            db_connectors = list(
                tqdm(
                    pool.imap(create_connector, connector_args),
                    total=len(connector_args),
                    desc="Creating database connectors",
                )
            )
            db_connectors = {conn.name: conn for conn in db_connectors}

        return NL2QDataset(
            name=self.name,
            split_id=split,
            tasks=tasks,
            db_connectors=db_connectors,
        )

    def get_split(self, split_id: str) -> NL2QDataset:
        if "_" in split_id:
            split, sample_size = split_id.split("_")
        else:
            split, sample_size = split_id, None

        if split not in self._data:
            self._data[split] = self._load_split(split)

        if sample_size:
            sampler = random.Random(42)
            return NL2QDataset(
                name=self.name,
                split_id=split_id,
                tasks=sampler.sample(self._data[split].tasks, int(sample_size)),
                db_connectors=self._data[split].db_connectors,
            )
        else:
            return self._data[split]
