from mintq.datahub.base import NL2QDatasetLoader, AsyncNL2QDatasetLoader
from mintq.datahub.bird_sql import AsyncBirdSQLDatasetLoader
from mintq.datahub.spider2 import Spider2SnowDatasetLoader
from mintq.datahub.beaver import BeaverDatasetLoader

__all__ = [
    "NL2QDatasetLoader",
    "AsyncNL2QDatasetLoader",
    "BirdSQLDatasetLoader",
    "BeaverDatasetLoader",
    "get_dataset_loader",
    "get_async_dataset_loader",
]

dataset_loader_classes = [Spider2SnowDatasetLoader, BeaverDatasetLoader]
dataset_loader_registry: dict[str, type[NL2QDatasetLoader]] = {cls.name: cls for cls in dataset_loader_classes}  # type: ignore

async_dataset_loader_classes = [AsyncBirdSQLDatasetLoader]
async_dataset_loader_registry: dict[str, type[AsyncNL2QDatasetLoader]] = {
    cls.name: cls for cls in async_dataset_loader_classes
}  # type: ignore


def get_dataset_loader(name: str) -> NL2QDatasetLoader:
    if name not in dataset_loader_registry:
        raise ValueError(f"Dataset loader {name} not found")
    return dataset_loader_registry[name]()


def get_async_dataset_loader(name: str) -> AsyncNL2QDatasetLoader:
    if name not in async_dataset_loader_registry:
        raise ValueError(f"Dataset loader {name} not found")
    return async_dataset_loader_registry[name]()
