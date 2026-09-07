"""Stable schema, result, and registry primitives."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.core.dataframe import (
        dataframe_to_arrow,
        deserialize_dataframe,
        normalize_dataframe,
        serialize_dataframe,
    )
    from tabulaflow.core.media import Base64DataUri, MediaFormat
    from tabulaflow.core.registry import ClassRegistry
    from tabulaflow.core.results import ErrorInfo, ExecResult, GraphResult, GraphResultEdge, GraphResultNode
    from tabulaflow.core.schema import (
        ColumnRef,
        ForeignKeySchema,
        GraphPropertySchema,
        GraphQueryLanguage,
        NodeSchema,
        PropertyGraphSchema,
        RelationshipEndpoint,
        RelationshipSchema,
        SQLColumnSchema,
        SQLDialect,
        SQLSchema,
        SQLTableSchema,
        TableRef,
    )

_LAZY_EXPORTS = {
    "Base64DataUri": ("tabulaflow.core.media", "Base64DataUri"),
    "ClassRegistry": ("tabulaflow.core.registry", "ClassRegistry"),
    "ColumnRef": ("tabulaflow.core.schema", "ColumnRef"),
    "dataframe_to_arrow": ("tabulaflow.core.dataframe", "dataframe_to_arrow"),
    "deserialize_dataframe": ("tabulaflow.core.dataframe", "deserialize_dataframe"),
    "ErrorInfo": ("tabulaflow.core.results", "ErrorInfo"),
    "ExecResult": ("tabulaflow.core.results", "ExecResult"),
    "ForeignKeySchema": ("tabulaflow.core.schema", "ForeignKeySchema"),
    "GraphPropertySchema": ("tabulaflow.core.schema", "GraphPropertySchema"),
    "GraphQueryLanguage": ("tabulaflow.core.schema", "GraphQueryLanguage"),
    "GraphResult": ("tabulaflow.core.results", "GraphResult"),
    "GraphResultEdge": ("tabulaflow.core.results", "GraphResultEdge"),
    "GraphResultNode": ("tabulaflow.core.results", "GraphResultNode"),
    "MediaFormat": ("tabulaflow.core.media", "MediaFormat"),
    "normalize_dataframe": ("tabulaflow.core.dataframe", "normalize_dataframe"),
    "NodeSchema": ("tabulaflow.core.schema", "NodeSchema"),
    "PropertyGraphSchema": ("tabulaflow.core.schema", "PropertyGraphSchema"),
    "RelationshipEndpoint": ("tabulaflow.core.schema", "RelationshipEndpoint"),
    "RelationshipSchema": ("tabulaflow.core.schema", "RelationshipSchema"),
    "SQLColumnSchema": ("tabulaflow.core.schema", "SQLColumnSchema"),
    "SQLDialect": ("tabulaflow.core.schema", "SQLDialect"),
    "SQLSchema": ("tabulaflow.core.schema", "SQLSchema"),
    "SQLTableSchema": ("tabulaflow.core.schema", "SQLTableSchema"),
    "serialize_dataframe": ("tabulaflow.core.dataframe", "serialize_dataframe"),
    "TableRef": ("tabulaflow.core.schema", "TableRef"),
}

__all__ = [
    "Base64DataUri",
    "ClassRegistry",
    "ColumnRef",
    "dataframe_to_arrow",
    "deserialize_dataframe",
    "ErrorInfo",
    "ExecResult",
    "ForeignKeySchema",
    "GraphPropertySchema",
    "GraphQueryLanguage",
    "GraphResult",
    "GraphResultEdge",
    "GraphResultNode",
    "MediaFormat",
    "NodeSchema",
    "normalize_dataframe",
    "PropertyGraphSchema",
    "RelationshipEndpoint",
    "RelationshipSchema",
    "SQLColumnSchema",
    "SQLDialect",
    "SQLSchema",
    "SQLTableSchema",
    "serialize_dataframe",
    "TableRef",
]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_EXPORTS})
