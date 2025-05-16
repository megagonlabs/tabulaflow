from abc import ABC, abstractmethod
from mintq.schema import BaseDBSchema, SQLSchema, SQLTableSchema, SQLColumnSchema


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

    @abstractmethod
    def format_table_name(self, table: SQLTableSchema) -> str:
        pass

    @abstractmethod
    def format_table(self, table: SQLTableSchema) -> str:
        pass

    @abstractmethod
    def format_column(self, table: SQLTableSchema, column: SQLColumnSchema) -> str:
        pass
