"""Stable schema, result, and registry primitives."""

from tabulaflow.core.registry import ClassRegistry
from tabulaflow.core.results import ErrorInfo, ExecResult, GraphResult, GraphResultEdge, GraphResultNode
from tabulaflow.core.schema import (
    ColumnRef,
    ForeignKeySchema,
    GraphPropertySchema,
    NodeSchema,
    GraphQueryLanguage,
    PropertyGraphSchema,
    RelationshipEndpoint,
    RelationshipSchema,
    SQLColumnSchema,
    SQLDialect,
    SQLSchema,
    SQLTableSchema,
    TableNamePattern,
    TableRef,
)

__all__ = [
    "ClassRegistry",
    "ColumnRef",
    "ErrorInfo",
    "ExecResult",
    "ForeignKeySchema",
    "GraphPropertySchema",
    "GraphResult",
    "GraphResultEdge",
    "GraphResultNode",
    "NodeSchema",
    "GraphQueryLanguage",
    "PropertyGraphSchema",
    "RelationshipEndpoint",
    "RelationshipSchema",
    "SQLColumnSchema",
    "SQLDialect",
    "SQLSchema",
    "SQLTableSchema",
    "TableNamePattern",
    "TableRef",
]
