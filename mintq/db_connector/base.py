from abc import ABC, abstractmethod
from typing import Any
import sqlalchemy
from mintq.schema import BaseDBSchema, SQLSchema


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


class BaseSQLDBConnector(BaseDBConnector):
    @property
    @abstractmethod
    def schema(self) -> SQLSchema:
        pass

    @property
    @abstractmethod
    def engine(self) -> sqlalchemy.engine.Engine:
        pass
