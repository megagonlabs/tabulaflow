from mintq.datahub.base import NL2QDatasetLoader
from mintq.datahub.bird_sql import BirdSQLDatasetLoader
from mintq.datahub.spider2 import Spider2SnowDatasetLoader
from mintq.datahub.beaver import BeaverDatasetLoader

__all__ = ["NL2QDatasetLoader", "BirdSQLDatasetLoader", "BeaverDatasetLoader", "get_dataset_loader"]

all_dataset_loader_classes = [BirdSQLDatasetLoader, Spider2SnowDatasetLoader, BeaverDatasetLoader]

dataset_loader_registry = {cls.name: cls for cls in all_dataset_loader_classes}  # type: ignore[attr-defined]


def get_dataset_loader(name: str) -> NL2QDatasetLoader:
    if name not in dataset_loader_registry:
        raise ValueError(f"Dataset loader {name} not found")
    return dataset_loader_registry[name]()
