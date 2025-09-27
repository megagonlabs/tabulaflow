from typing import Protocol, ClassVar, Sequence, Mapping
from mintq.schema import NL2QDataset, NL2QTask
from mintq.db_connector import NL2QDBConnector


class BaseNL2QDatasetLoader(Protocol):
    name: ClassVar[str]
    splits: ClassVar[list[str]]

    def get_databases(self, split: str) -> list[str]: ...

    async def get_tasks_async(self, split: str, databases: list[str] | None = None) -> Sequence[NL2QTask]: ...

    async def get_db_connectors_async(
        self, split: str, databases: list[str] | None = None
    ) -> Mapping[str, NL2QDBConnector]: ...

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset: ...
