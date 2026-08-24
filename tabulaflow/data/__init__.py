"""Connectors, registries, schema services, and external-data loaders."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.data.config import Neo4jConnectorConfig, SQLConnectorConfig
    from tabulaflow.data.neo4j import Neo4jConnector
    from tabulaflow.data.protocols import DBConnector, PropertyGraphConnectorProtocol, SQLConnectorProtocol
    from tabulaflow.data.registry import DBRegistry
    from tabulaflow.data.sql import SQLConnector
    from tabulaflow.data.url import connect_url

_LAZY_EXPORTS = {
    "DBConnector": ("tabulaflow.data.protocols", "DBConnector"),
    "DBRegistry": ("tabulaflow.data.registry", "DBRegistry"),
    "Neo4jConnector": ("tabulaflow.data.neo4j", "Neo4jConnector"),
    "Neo4jConnectorConfig": ("tabulaflow.data.config", "Neo4jConnectorConfig"),
    "PropertyGraphConnectorProtocol": ("tabulaflow.data.protocols", "PropertyGraphConnectorProtocol"),
    "SQLConnector": ("tabulaflow.data.sql", "SQLConnector"),
    "SQLConnectorConfig": ("tabulaflow.data.config", "SQLConnectorConfig"),
    "SQLConnectorProtocol": ("tabulaflow.data.protocols", "SQLConnectorProtocol"),
    "connect_url": ("tabulaflow.data.url", "connect_url"),
}

__all__ = [
    "DBConnector",
    "DBRegistry",
    "Neo4jConnector",
    "Neo4jConnectorConfig",
    "PropertyGraphConnectorProtocol",
    "SQLConnector",
    "SQLConnectorConfig",
    "SQLConnectorProtocol",
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
