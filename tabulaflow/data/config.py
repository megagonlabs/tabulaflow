"""Immutable configuration for data connectors."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

from tabulaflow.core._cache import DEFAULT_CACHE_DIR


class _ConnectorConfig(BaseSettings):
    """Common query-execution policy for a data connector."""

    model_config = SettingsConfigDict(
        env_prefix="TABULAFLOW_",
        frozen=True,
        extra="forbid",
        env_parse_none_str="none",
    )

    max_result_rows: PositiveInt | None = 1_000_000
    query_timeout_seconds: PositiveInt | None = 300
    max_query_concurrency: PositiveInt = 8


class _CachedSchemaConnectorConfig(_ConnectorConfig):
    """Query and schema-cache policy for an introspected connector."""

    cache_dir: Path = DEFAULT_CACHE_DIR
    schema_cache_mode: Literal["off", "read_write", "refresh", "cache_only"] = "off"


class SQLConnectorConfig(_CachedSchemaConnectorConfig):
    """Operational policy for a SQL connector.

    Attributes:
        cache_dir: Root directory for schema and query-result caches.
        max_result_rows: Maximum rows materialized by one query, or ``None``
            for no limit.
        query_timeout_seconds: Default query timeout, or ``None`` to disable.
        max_query_concurrency: Maximum in-flight queries and connection-pool
            size per connector.
        schema_cache_mode: Schema cache read/write policy.
        sql_column_stats_enabled: Whether to collect exact row counts and column
            statistics for physical tables. Tables and views are always
            enriched from one bounded row sample; views are never exhaustively
            profiled.
        sql_query_cache_mode: Query-result cache read/write policy.
    """

    sql_column_stats_enabled: bool = False
    sql_query_cache_mode: Literal["off", "read_write", "refresh"] = "off"


class Neo4jConnectorConfig(_CachedSchemaConnectorConfig):
    """Operational policy for a Neo4j connector.

    Attributes:
        cache_dir: Root directory for schema caches.
        max_result_rows: Maximum rows materialized by one query, or ``None``
            for no limit.
        query_timeout_seconds: Default query timeout, or ``None`` to disable.
        max_query_concurrency: Maximum in-flight queries and connection-pool
            size per connector.
        schema_cache_mode: Schema cache read/write policy.
        graph_schema_introspection_mode: ``fast`` for metadata procedures or
            ``full_scan`` for observed graph data.
        max_graph_result_nodes: Maximum nodes extracted into a graph result.
        max_graph_result_edges: Maximum edges extracted into a graph result.
    """

    graph_schema_introspection_mode: Literal["fast", "full_scan"] = "fast"
    max_graph_result_nodes: PositiveInt | None = 300
    max_graph_result_edges: PositiveInt | None = 700


class SPARQLConnectorConfig(_ConnectorConfig):
    """Operational policy for a SPARQL connector.

    Attributes:
        max_result_rows: Maximum rows materialized by one query, or ``None``
            for no limit.
        query_timeout_seconds: Overall query deadline, including throttling and
            retries, or ``None`` to disable.
        max_query_concurrency: Maximum in-flight queries per connector.
        max_sparql_response_bytes: Maximum decompressed SPARQL response bytes
            buffered.
    """

    max_sparql_response_bytes: PositiveInt = 50 * 1024 * 1024


@dataclass(frozen=True)
class DataSourceConnectorConfigs:
    """Backend-specific policies used when connecting an untyped data source."""

    sql: SQLConnectorConfig = field(default_factory=SQLConnectorConfig)
    neo4j: Neo4jConnectorConfig = field(default_factory=Neo4jConnectorConfig)
    sparql: SPARQLConnectorConfig = field(default_factory=SPARQLConnectorConfig)


__all__ = [
    "DataSourceConnectorConfigs",
    "Neo4jConnectorConfig",
    "SPARQLConnectorConfig",
    "SQLConnectorConfig",
]
