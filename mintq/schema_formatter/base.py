from abc import ABC, abstractmethod
from mintq.schema import BaseDBSchema, SQLSchema


class BaseSchemaFormatter(ABC):
    name: str

    @abstractmethod
    def format(self, schema: BaseDBSchema) -> str:
        pass


class BaseSQLSchemaFormatter(BaseSchemaFormatter):
    name: str

    @abstractmethod
    def format(self, schema: SQLSchema) -> str:
        pass
