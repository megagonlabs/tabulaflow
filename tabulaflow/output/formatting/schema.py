from typing import ClassVar, Protocol, TypeAlias

from tabulaflow.core import PropertyGraphSchema, SQLDialect, SQLSchema, SQLTableSchema
from tabulaflow.core.registry import ClassRegistry


class SQLSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: SQLSchema, *, include_descriptions: bool = False) -> str: ...

    def format_table(
        self,
        table: SQLTableSchema,
        *,
        dialect: SQLDialect | None,
        include_descriptions: bool = False,
    ) -> str: ...


class PropertyGraphSchemaFormatter(Protocol):
    name: ClassVar[str]

    def format(self, schema: PropertyGraphSchema) -> str: ...


SchemaFormatter: TypeAlias = SQLSchemaFormatter | PropertyGraphSchemaFormatter

schema_formatter_registry = ClassRegistry[SchemaFormatter]("formatter")
