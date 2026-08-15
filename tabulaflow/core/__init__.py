"""Stable platform primitives and deterministic helpers."""

from tabulaflow.core.registry import ClassRegistry, NamedClass
from tabulaflow.core.results import ErrorInfo, ExecResult, GraphResult, GraphResultEdge, GraphResultNode
from tabulaflow.core.schema import (
    ColumnRef,
    ForeignKeySchema,
    GraphPropertySchema,
    TableNamePattern,
    NodeSchema,
    NonSQLLanguage,
    PropertyGraphSchema,
    RelationshipEndpoint,
    RelationshipSchema,
    SQLColumnSchema,
    SQLDialect,
    SQLSchema,
    SQLTableSchema,
    TableRef,
)

__all__ = [
    "ClassRegistry",
    "NamedClass",
    "ColumnRef",
    "ErrorInfo",
    "ExecResult",
    "ForeignKeySchema",
    "GraphPropertySchema",
    "GraphResult",
    "GraphResultEdge",
    "GraphResultNode",
    "TableNamePattern",
    "NodeSchema",
    "NonSQLLanguage",
    "PropertyGraphSchema",
    "RelationshipEndpoint",
    "RelationshipSchema",
    "SQLColumnSchema",
    "SQLDialect",
    "SQLSchema",
    "SQLTableSchema",
    "TableRef",
]
