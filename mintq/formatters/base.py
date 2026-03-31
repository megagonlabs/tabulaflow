from typing import Protocol, ClassVar, TypeAlias, Union
from mintq.schema import (
    SQLDialect,
    SQLSchema,
    SQLTableSchema,
    SQLColumnSchema,
    PropertyGraphSchema,
    NodeSchema,
    RelationshipSchema,
    GraphPropertySchema,
)
from mintq.registry import Registry


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

    def format(self, schema: PropertyGraphSchema, add_description: bool = False) -> str: ...

    def format_node(self, node: NodeSchema, add_description: bool = False) -> str: ...

    def format_relationship(self, rel: RelationshipSchema) -> str: ...

    def format_property(self, prop: GraphPropertySchema) -> str: ...


NL2QFormatter: TypeAlias = Union[BaseSQLSchemaFormatter, BasePropertyGraphSchemaFormatter]

formatter_registry = Registry[NL2QFormatter]("formatter")
