from mintq.schema_formatter.base import BaseSchemaFormatter
from mintq.schema_formatter.sql import SQLDefaultSchemaFormatter

__all__ = ["BaseSchemaFormatter", "SQLDefaultSchemaFormatter"]


schema_formatter_registry = {
    "sql_default": SQLDefaultSchemaFormatter,
}


def get_schema_formatter(name: str) -> BaseSchemaFormatter:
    if name not in schema_formatter_registry:
        raise ValueError(f"Unknown schema formatter: {name}")
    return schema_formatter_registry[name]()
