from mintq.formatters.base import BaseSchemaFormatter, BaseSQLSchemaFormatter
from mintq.formatters.sql import SQLDefaultSchemaFormatter

__all__ = ["BaseSchemaFormatter", "BaseSQLSchemaFormatter", "SQLDefaultSchemaFormatter", "get_schema_formatter"]


all_schema_formatter_classes = [SQLDefaultSchemaFormatter]

schema_formatter_registry: dict[str, type[BaseSchemaFormatter] | type[BaseSQLSchemaFormatter]] = {
    cls.name: cls  # type: ignore
    for cls in all_schema_formatter_classes
}


def get_schema_formatter(name: str) -> BaseSchemaFormatter | BaseSQLSchemaFormatter:
    if name not in schema_formatter_registry:
        raise ValueError(f"Unknown schema formatter: {name}")
    return schema_formatter_registry[name]()
