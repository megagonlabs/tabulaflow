from typing import Optional, Protocol, ClassVar
from mintq.schema import NL2QDataset


class NL2QDatasetLoader(Protocol):
    name: ClassVar[str]

    def get_split(self, split_id: str, databases: Optional[list[str]] = None) -> NL2QDataset: ...
