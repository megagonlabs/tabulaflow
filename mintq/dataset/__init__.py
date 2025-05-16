from mintq.dataset.base import NL2QDatasetLoader, NL2QDataset
from mintq.dataset.bird_sql import BirdSQLDatasetLoader
from mintq.dataset.spider2 import Spider2SnowDatasetLoader
from mintq.dataset.beaver import BeaverDatasetLoader

__all__ = ["NL2QDatasetLoader", "NL2QDataset", "BirdSQLDatasetLoader", "BeaverDatasetLoader", "get_dataset_loader"]

all_dataset_loader_classes = [BirdSQLDatasetLoader, Spider2SnowDatasetLoader, BeaverDatasetLoader]

dataset_loader_registry = {cls.name: cls for cls in all_dataset_loader_classes}  # type: ignore[attr-defined]


def get_dataset_loader(name: str) -> NL2QDatasetLoader:
    if name not in dataset_loader_registry:
        raise ValueError(f"Dataset loader {name} not found")
    return dataset_loader_registry[name]()
