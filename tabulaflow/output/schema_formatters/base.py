from typing import Protocol, ClassVar, TypeAlias, Union
from tabulaflow.core import (
    SQLDialect,
    SQLSchema,
    SQLTableSchema,
    SQLColumnSchema,
    PropertyGraphSchema,
    NodeSchema,
    GraphPropertySchema,
)
from tabulaflow.core.registry import ClassRegistry


class BaseSQLSchemaFormatter(Protocol):
    name: ClassVar[str]

    def set_dialect(self, dialect: SQLDialect | None) -> None: ...

    def format(self, schema: SQLSchema, pk_fk_column_only: bool = False, add_description: bool = False) -> str: ...

    def format_table_name(self, table: SQLTableSchema) -> str: ...

    def format_table(
        self,
        table: SQLTableSchema,
        pk_fk_column_only: bool = False,
        add_description: bool = False,
    ) -> str: ...

    def format_column(self, column: SQLColumnSchema, add_description: bool = False) -> str: ...


class BasePropertyGraphSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: PropertyGraphSchema) -> str: ...

    def format_node(self, node: NodeSchema) -> str: ...

    def format_pattern(self, label: str, source_label: str, target_label: str) -> str: ...

    def format_property(self, prop: GraphPropertySchema) -> str: ...


SchemaFormatter: TypeAlias = Union[BaseSQLSchemaFormatter, BasePropertyGraphSchemaFormatter]

schema_formatter_registry = ClassRegistry[SchemaFormatter]("formatter")
