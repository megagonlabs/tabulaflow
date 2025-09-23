from typing import Protocol, ClassVar
from mintq.schema import NL2QDataset, NL2QTask
from mintq.db_connector import BaseAsyncDBConnector


class BaseAsyncNL2QDatasetLoader(Protocol):
    name: ClassVar[str]
    splits: ClassVar[list[str]]

    def get_database_names(self, split: str) -> list[str]: ...

    async def get_tasks_async(self, split: str) -> list[NL2QTask]: ...

    async def get_databases_async(self, split: str, databases: list[str]) -> dict[str, BaseAsyncDBConnector]: ...

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset: ...
