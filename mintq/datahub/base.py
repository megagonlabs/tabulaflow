from typing import Optional, Protocol, ClassVar
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


class GetSplitMixin:
    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset:
        if not hasattr(self, "_split_data"):
            self._split_data = {}

        if split not in self.splits:
            raise ValueError(f"Split {split} not supported, only {self.splits} are supported for {self.name}")

        if split not in self._split_data:
            self._split_data[split] = NL2QDataset(
                name=self.name,
                split=split,
                subsample_size=None,
                tasks=await self.get_tasks_async(split),
                db_connectors={},
            )
        dataset = self._split_data[split]

        if databases is None:
            databases = self.get_database_names(split)
        missing_databases = sorted(set(databases) - set(dataset.db_connectors.keys()))
        if missing_databases:
            dataset.db_connectors.update(await self.get_databases_async(split, missing_databases))

        return NL2QDataset(
            name=self.name,
            split=split,
            subsample_size=None,
            tasks=dataset.tasks,
            db_connectors={db: dataset.db_connectors[db] for db in databases},
        )
