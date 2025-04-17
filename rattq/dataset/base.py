from abc import ABC, abstractmethod
from typing import Optional
from rattq.schema import NL2QDataset


class NL2QDatasetLoader(ABC):
    @abstractmethod
    def get_split(self, split_id: str, databases: Optional[list[str]] = None) -> NL2QDataset:
        pass
