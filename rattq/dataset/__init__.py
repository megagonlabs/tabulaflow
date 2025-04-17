from rattq.dataset.base import NL2QDatasetLoader, NL2QDataset
from rattq.dataset.bird_sql import BirdSQLDatasetLoader
from rattq.dataset.spider2 import Spider2SnowDatasetLoader

__all__ = ["NL2QDatasetLoader", "NL2QDataset", "BirdSQLDatasetLoader"]


dataset_loader_registry = {
    "bird-sql": BirdSQLDatasetLoader,
    "spider2-snow": Spider2SnowDatasetLoader,
}


def get_dataset_loader(name: str) -> NL2QDatasetLoader:
    if name not in dataset_loader_registry:
        raise ValueError(f"Dataset loader {name} not found")
    return dataset_loader_registry[name]()
