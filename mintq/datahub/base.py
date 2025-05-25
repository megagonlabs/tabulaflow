from typing import Optional, Protocol, ClassVar
from mintq.schema import NL2QDataset


class BaseAsyncNL2QDatasetLoader(Protocol):
    name: ClassVar[str]

    async def get_split_async(self, split_id: str, databases: Optional[list[str]] = None) -> NL2QDataset: ...
