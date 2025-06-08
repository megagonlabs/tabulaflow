from typing import Protocol, ClassVar
from mintq.schema import BaseDBSchema, SQLSchema, SQLTableSchema, SQLColumnSchema, HSQLSchema


class BaseSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: BaseDBSchema) -> str: ...


class BaseSQLSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: SQLSchema) -> str: ...

    def format_table_name(self, table: SQLTableSchema) -> str: ...

    def format_table(self, table: SQLTableSchema, pk_fk_column_only: bool = False) -> str: ...

    def format_column(self, column: SQLColumnSchema) -> str: ...


class BaseHSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: HSQLSchema) -> str: ...
