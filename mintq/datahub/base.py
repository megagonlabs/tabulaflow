from typing import Protocol, ClassVar, Sequence, Mapping, TypeAlias
from mintq.schema import NL2QDataset, NL2QTask
from mintq.db_connector import NL2QDBConnector
from mintq.registry import Registry


class BaseNL2QDatasetLoader(Protocol):
    name: ClassVar[str]
    splits: ClassVar[list[str]]
    default_metrics: ClassVar[list[str]]

    def get_databases(self, split: str) -> list[str]: ...

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> Sequence[NL2QTask]: ...

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> Mapping[str, NL2QDBConnector]: ...

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset: ...


NL2QDatasetLoader: TypeAlias = BaseNL2QDatasetLoader


dataset_registry = Registry[NL2QDatasetLoader]("dataset")
