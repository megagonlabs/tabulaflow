"""Connectors, registries, schema services, and external-data loaders."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.data.config import Neo4jConnectorConfig, SPARQLConnectorConfig, SQLConnectorConfig
    from tabulaflow.data.neo4j import Neo4jConnector
    from tabulaflow.data.protocols import DataConnector
    from tabulaflow.data.registry import DataConnectorRegistry
    from tabulaflow.data.sparql import SPARQLConnector
    from tabulaflow.data.sql import SQLConnector, TableWriteMode
    from tabulaflow.data.url import connect_url

_LAZY_EXPORTS = {
    "DataConnector": ("tabulaflow.data.protocols", "DataConnector"),
    "DataConnectorRegistry": ("tabulaflow.data.registry", "DataConnectorRegistry"),
    "Neo4jConnector": ("tabulaflow.data.neo4j", "Neo4jConnector"),
    "Neo4jConnectorConfig": ("tabulaflow.data.config", "Neo4jConnectorConfig"),
    "SPARQLConnector": ("tabulaflow.data.sparql", "SPARQLConnector"),
    "SPARQLConnectorConfig": ("tabulaflow.data.config", "SPARQLConnectorConfig"),
    "SQLConnector": ("tabulaflow.data.sql", "SQLConnector"),
    "SQLConnectorConfig": ("tabulaflow.data.config", "SQLConnectorConfig"),
    "TableWriteMode": ("tabulaflow.data.sql", "TableWriteMode"),
    "connect_url": ("tabulaflow.data.url", "connect_url"),
}

__all__ = [
    "DataConnector",
    "DataConnectorRegistry",
    "Neo4jConnector",
    "Neo4jConnectorConfig",
    "SPARQLConnector",
    "SPARQLConnectorConfig",
    "SQLConnector",
    "SQLConnectorConfig",
    "TableWriteMode",
    "connect_url",
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
