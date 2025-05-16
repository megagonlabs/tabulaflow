from abc import ABC, abstractmethod
from mintq.schema import SQLSchema


class BaseSQLSchemaFormatter(ABC):
    name: str

    @abstractmethod
    def format(self, schema: SQLSchema) -> str:
        pass
