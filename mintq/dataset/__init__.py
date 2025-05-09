from mintq.dataset.base import NL2QDatasetLoader, NL2QDataset
from mintq.dataset.bird_sql import BirdSQLDatasetLoader
from mintq.dataset.spider2 import Spider2SnowDatasetLoader
from mintq.dataset.beaver import BeaverDatasetLoader

__all__ = ["NL2QDatasetLoader", "NL2QDataset", "BirdSQLDatasetLoader", "BeaverDatasetLoader"]


dataset_loader_registry = {
    "bird-sql": BirdSQLDatasetLoader,
    "spider2-snow": Spider2SnowDatasetLoader,
    "beaver": BeaverDatasetLoader,
}


def get_dataset_loader(name: str) -> NL2QDatasetLoader:
    if name not in dataset_loader_registry:
        raise ValueError(f"Dataset loader {name} not found")
    return dataset_loader_registry[name]()
