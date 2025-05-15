from abc import ABC, abstractmethod
from mintq.schema import SQLSchema


class BaseSchemaFormatter(ABC):
    name: str


class BaseSQLSchemaFormatter(BaseSchemaFormatter):
    name: str

    @abstractmethod
    def format(self, schema: SQLSchema) -> str:
        pass
