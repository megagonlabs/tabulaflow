from abc import ABC, abstractmethod
from typing import Any
from mintq.schema import BaseDBSchema


class BaseDBConnector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def schema(self) -> BaseDBSchema:
        pass

    @abstractmethod
    def run_query(self, query: str, parameters=(), timeout: int = 30, return_df: bool = False) -> list[tuple[Any, ...]]:
        pass
