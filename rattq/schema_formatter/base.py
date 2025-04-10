from abc import ABC, abstractmethod
from rattq.schema import BaseDBSchema


class BaseSchemaFormatter(ABC):
    @abstractmethod
    def format(self, schema: BaseDBSchema) -> str:
        pass
