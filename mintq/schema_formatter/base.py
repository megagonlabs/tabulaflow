from typing import Protocol, ClassVar
from mintq.schema import BaseDBSchema, SQLSchema, SQLTableSchema, SQLColumnSchema


class BaseSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: BaseDBSchema) -> str: ...


class BaseSQLSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: SQLSchema) -> str: ...

    def format_table_name(self, table: SQLTableSchema) -> str: ...

    def format_table(self, table: SQLTableSchema) -> str: ...

    def format_column(self, table: SQLTableSchema, column: SQLColumnSchema) -> str: ...
