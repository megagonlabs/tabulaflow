from abc import ABC, abstractmethod
from typing import Optional
from mintq.schema import NL2QDataset


class NL2QDatasetLoader(ABC):
    name: str

    @abstractmethod
    def get_split(self, split_id: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        pass
