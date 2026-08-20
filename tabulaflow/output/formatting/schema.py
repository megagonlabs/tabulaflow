"""Schema formatter protocols and registry."""

from typing import ClassVar, Protocol, TypeAlias

from tabulaflow.core import PropertyGraphSchema, SQLDialect, SQLSchema, SQLTableSchema
from tabulaflow.core.registry import ClassRegistry


class SQLSchemaFormatter(Protocol):
    """Render SQL schema models as readable text."""

    name: ClassVar[str]

    def format(self, schema: SQLSchema, *, include_descriptions: bool = False) -> str:
        """Render a complete database schema."""
        ...

    def format_table(
        self,
        table: SQLTableSchema,
        *,
        dialect: SQLDialect | None,
        include_descriptions: bool = False,
    ) -> str:
        """Render one table using the supplied SQL dialect."""
        ...


class PropertyGraphSchemaFormatter(Protocol):
    """Render property-graph schema models as readable text."""

    name: ClassVar[str]

    def format(self, schema: PropertyGraphSchema) -> str:
        """Render a complete property-graph schema."""
        ...


_SchemaFormatter: TypeAlias = SQLSchemaFormatter | PropertyGraphSchemaFormatter

schema_formatter_registry = ClassRegistry[_SchemaFormatter]("formatter")
