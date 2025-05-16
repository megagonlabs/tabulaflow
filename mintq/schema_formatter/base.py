from abc import ABC, abstractmethod
from mintq.schema import BaseDBSchema


class BaseSchemaFormatter(ABC):
    name: str

    @abstractmethod
    def format(self, schema: BaseDBSchema) -> str:
        pass
