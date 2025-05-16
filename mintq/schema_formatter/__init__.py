from mintq.schema_formatter.base import BaseSchemaFormatter
from mintq.schema_formatter.sql import SQLDefaultSchemaFormatter

__all__ = ["BaseSchemaFormatter", "SQLDefaultSchemaFormatter", "get_schema_formatter"]


all_schema_formatter_classes = [SQLDefaultSchemaFormatter]

schema_formatter_registry = {cls.name: cls for cls in all_schema_formatter_classes}


def get_schema_formatter(name: str) -> BaseSchemaFormatter:
    if name not in schema_formatter_registry:
        raise ValueError(f"Unknown schema formatter: {name}")
    return schema_formatter_registry[name]()
