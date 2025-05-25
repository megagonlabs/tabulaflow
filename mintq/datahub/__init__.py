from mintq.datahub.base import BaseAsyncNL2QDatasetLoader
from mintq.datahub.bird_sql import BirdSQLDatasetLoader
from mintq.datahub.spider2 import Spider2SnowDatasetLoader
from mintq.datahub.beaver import BeaverDatasetLoader

__all__ = [
    "BaseAsyncNL2QDatasetLoader",
    "BirdSQLDatasetLoader",
    "Spider2SnowDatasetLoader",
    "BeaverDatasetLoader",
    "get_dataset_loader",
]

dataset_loader_classes = [BirdSQLDatasetLoader, Spider2SnowDatasetLoader, BeaverDatasetLoader]
dataset_loader_registry: dict[str, type[BaseAsyncNL2QDatasetLoader]] = {cls.name: cls for cls in dataset_loader_classes}  # type: ignore


def get_dataset_loader(name: str) -> BaseAsyncNL2QDatasetLoader:
    if name not in dataset_loader_registry:
        raise ValueError(f"Dataset loader {name} not found")
    return dataset_loader_registry[name]()
