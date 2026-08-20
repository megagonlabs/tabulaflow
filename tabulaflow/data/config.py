"""Immutable configuration for data connectors."""

from pathlib import Path
from typing import Literal

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CACHE_DIR = Path.home() / ".tabulaflow" / "cache"


class _ConnectorConfig(BaseSettings):
    """Common operational policy for a data connector."""

    model_config = SettingsConfigDict(
        env_prefix="TABULAFLOW_",
        frozen=True,
        extra="forbid",
        env_parse_none_str="none",
    )

    cache_dir: Path = DEFAULT_CACHE_DIR
    max_result_rows: PositiveInt | None = 1_000_000
    query_timeout_seconds: PositiveInt | None = 300
    max_query_concurrency: PositiveInt = 8
    schema_cache_mode: Literal["off", "read_write", "refresh", "cache_only"] = "read_write"


class SQLConnectorConfig(_ConnectorConfig):
    """Operational policy for a SQL connector.

    Attributes:
        cache_dir: Root directory for schema and query-result caches.
        max_result_rows: Maximum rows materialized by one query, or ``None``
            for no limit.
        query_timeout_seconds: Default query timeout, or ``None`` to disable.
        max_query_concurrency: Maximum in-flight queries and connection-pool
            size per connector.
        schema_cache_mode: Schema cache read/write policy.
        collect_column_stats: Whether to collect exact row counts and column
            statistics for physical tables. Tables and views are always
            enriched from one bounded row sample; views are never exhaustively
            profiled.
        query_cache_mode: Query-result cache read/write policy.
    """

    collect_column_stats: bool = False
    query_cache_mode: Literal["off", "read_write", "refresh"] = "off"


class Neo4jConnectorConfig(_ConnectorConfig):
    """Operational policy for a Neo4j connector.

    Attributes:
        cache_dir: Root directory for schema caches.
        max_result_rows: Maximum rows materialized by one query, or ``None``
            for no limit.
        query_timeout_seconds: Default query timeout, or ``None`` to disable.
        max_query_concurrency: Maximum in-flight queries and connection-pool
            size per connector.
        schema_cache_mode: Schema cache read/write policy.
        schema_introspection_mode: ``fast`` for metadata procedures or
            ``full_scan`` for observed graph data.
        max_graph_result_nodes: Maximum nodes extracted into a graph result.
        max_graph_result_edges: Maximum edges extracted into a graph result.
    """

    schema_introspection_mode: Literal["fast", "full_scan"] = "fast"
    max_graph_result_nodes: PositiveInt | None = 300
    max_graph_result_edges: PositiveInt | None = 700


__all__ = [
    "Neo4jConnectorConfig",
    "SQLConnectorConfig",
]
