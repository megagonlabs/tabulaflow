import os
import json
from rattq.db_connector.base import BaseDBConnector
from rattq.db_connector.sql import SQLiteConnector

__all__ = ["BaseDBConnector", "SQLiteConnector", "get_db_connectors"]


def get_db_connectors(
    dataset_name: str, splits: list[str] = ["train", "dev", "test"]
) -> dict[str, BaseDBConnector]:
    if dataset_name == "bird-sql":
        res = {}
        paths = {
            "train": (
                "data/BIRD-SQL/train/train_tables.json",
                "data/BIRD-SQL/train/train_databases/",
            ),
            "dev": (
                "data/BIRD-SQL/dev_20240627/dev_tables.json",
                "data/BIRD-SQL/dev_20240627/dev_databases/",
            ),
        }
        for split in splits:
            if "_" in split:
                split = split.split("_")[0]
            metadata_path, db_dir = paths[split]
            with open(metadata_path, "r") as f:
                db_names = [item["db_id"] for item in json.load(f)]
            for db_name in db_names:
                sqlite_path = os.path.join(db_dir, db_name, f"{db_name}.sqlite")
                res[db_name] = SQLiteConnector(name=db_name, db_path=sqlite_path)
        return res
    else:
        raise ValueError(f"Dataset {dataset_name} not supported")
