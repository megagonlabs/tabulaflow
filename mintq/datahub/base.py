from typing import Optional, Protocol, ClassVar
from mintq.schema import NL2QDataset


class BaseAsyncNL2QDatasetLoader(Protocol):
    name: ClassVar[str]
    splits: ClassVar[list[str]]

    async def get_split_async(
        self, split: str, databases: list[str] | None = None, subsample_size: int | None = None
    ) -> NL2QDataset: ...
