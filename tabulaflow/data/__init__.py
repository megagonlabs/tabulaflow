"""Connectors, registries, schema services, and external-data loaders."""

from tabulaflow.data.base import DataConnector, GraphConnectorProtocol, SQLConnectorProtocol
from tabulaflow.data.config import Neo4jConnectorConfig, SQLConnectorConfig
from tabulaflow.data.neo4j import Neo4jConnector
from tabulaflow.data.registry import DBRegistry
from tabulaflow.data.sql import SQLConnector
from tabulaflow.data.url import (
    DB_FILE_SCHEMES,
    connect_url,
    credentialless_url,
    global_id_from_url,
    normalize_url,
    url_needs_password,
)
from tabulaflow.data.introspection import connector_info

__all__ = [
    "DBRegistry",
    "DataConnector",
    "GraphConnectorProtocol",
    "Neo4jConnector",
    "Neo4jConnectorConfig",
    "SQLConnector",
    "SQLConnectorConfig",
    "SQLConnectorProtocol",
    "DB_FILE_SCHEMES",
    "connect_url",
    "connector_info",
    "credentialless_url",
    "global_id_from_url",
    "normalize_url",
    "url_needs_password",
]
