from abc import ABC, abstractmethod
from rattq.schema import NL2QDataset


class NL2QDatasetLoader(ABC):
    @abstractmethod
    def get_split(self, split_id: str) -> NL2QDataset:
        pass
