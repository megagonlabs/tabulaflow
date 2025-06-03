from typing import Protocol, ClassVar
from mintq.schema import BaseDBSchema, SQLSchema, SQLTableSchema, SQLColumnSchema, HSQLSchema


class BaseSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: BaseDBSchema) -> str: ...


class BaseSQLSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(
        self, schema: SQLSchema, include_foreign_keys: bool = True, include_table_schemas: bool = True
    ) -> str: ...

    def format_table_name(self, table: SQLTableSchema) -> str: ...

    def format_table(self, table: SQLTableSchema) -> str: ...

    def format_column(self, table: SQLTableSchema, column: SQLColumnSchema) -> str: ...


class BaseHSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: HSQLSchema) -> str: ...
