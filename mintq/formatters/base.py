from typing import Protocol, ClassVar, TypeAlias
from mintq.schema import SQLDialect, SQLSchema, SQLTableSchema, SQLColumnSchema
from mintq.registry import Registry


class BaseSQLSchemaFormatter(Protocol):
    name: ClassVar[str]

    def set_dialect(self, dialect: SQLDialect | None) -> None: ...

    def format(self, schema: SQLSchema, pk_fk_column_only: bool = False, add_description: bool = False) -> str: ...

    def format_table_name(self, table: SQLTableSchema) -> str: ...

    def format_table(
        self, table: SQLTableSchema, pk_fk_column_only: bool = False, add_description: bool = False,
    ) -> str: ...

    def format_column(self, column: SQLColumnSchema, add_description: bool = False) -> str: ...


NL2QFormatter: TypeAlias = BaseSQLSchemaFormatter

formatter_registry = Registry[NL2QFormatter]("formatter")
