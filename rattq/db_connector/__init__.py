import os
import json
from rattq.db_connector.base import BaseDBConnector
from rattq.db_connector.sqlite_conn import SQLiteConnector
from multiprocessing import Pool

__all__ = ["BaseDBConnector", "SQLiteConnector", "get_db_connectors"]


def create_connector(args):
    name, conn_cls, kwargs = args
    return conn_cls(name, **kwargs)


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

            # Create connections in parallel using a process pool
            with Pool(processes=16) as pool:
                connections = pool.map(
                    create_connector,
                    [
                        (
                            name,
                            SQLiteConnector,
                            {
                                "sqlite_db_path": os.path.join(
                                    db_dir, name, f"{name}.sqlite"
                                )
                            },
                        )
                        for name in db_names
                    ],
                )
                res = {conn.name: conn for conn in connections}
        return res
    else:
        raise ValueError(f"Dataset {dataset_name} not supported")
