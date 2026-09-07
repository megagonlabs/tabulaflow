"""Normalize database connection sources and open live connectors.

``connect_url`` accepts a database URL or SQLite/DuckDB path, selects the
appropriate async driver, derives a credential-free identity, and dispatches to
SQL or Neo4j. Loading raw files and Hugging Face datasets belongs to loaders.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

from tabulaflow.data.config import Neo4jConnectorConfig, SQLConnectorConfig

if TYPE_CHECKING:
    from tabulaflow.data.protocols import DataConnector

# Local database-file extension -> SQLAlchemy scheme.
_DB_FILE_SCHEMES: dict[str, str] = {
    ".sqlite": "sqlite+aiosqlite",
    ".sqlite3": "sqlite+aiosqlite",
    ".db": "sqlite+aiosqlite",
    ".duckdb": "duckdb",
}

# Sync driver scheme -> async driver scheme.
_ASYNC_DRIVER_UPGRADES: dict[str, str] = {
    "sqlite": "sqlite+aiosqlite",
    "postgresql": "postgresql+asyncpg",
    "postgres": "postgresql+asyncpg",
    "mysql": "mysql+asyncmy",
}


def normalize_connection_url(source: str) -> str:
    """Normalize a raw source to a connectable URL.

    A local database-file path becomes a file URL; a sync driver scheme is upgraded to
    its async equivalent. Anything else is returned unchanged.
    """
    # No scheme yet → it's a path; turn a known db-file extension into a file URL.
    # (Guarded by the scheme check so the function is idempotent — re-normalizing an
    # already-built URL that ends in e.g. ".sqlite" must not re-treat it as a path.)
    if "://" not in source:
        for ext, scheme in _DB_FILE_SCHEMES.items():
            if source.lower().endswith(ext):
                return f"{scheme}:///{os.path.abspath(os.path.expanduser(source))}"
        return source

    scheme, rest = source.split("://", 1)
    scheme = scheme.lower()
    if "+" not in scheme and scheme in _ASYNC_DRIVER_UPGRADES:
        return f"{_ASYNC_DRIVER_UPGRADES[scheme]}://{rest}"
    return source


def strip_url_credentials(url: str) -> str:
    """Return ``url`` with any username/password removed."""
    parsed = urlparse(url)
    if parsed.hostname is None:
        return url

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host + (f":{parsed.port}" if parsed.port else "")
    return urlunparse(parsed._replace(netloc=netloc))


def _is_neo4j_bolt_url(url: str) -> bool:
    if "://" not in url:
        return False
    scheme = url.split("://", 1)[0].lower()
    return scheme == "neo4j" or scheme.startswith("neo4j+") or scheme == "bolt" or scheme.startswith("bolt+")


def _neo4j_driver_params(url: str) -> tuple[str, str | None, tuple[str, str] | None]:
    """Split a neo4j/bolt URL into ``(driver_url, database, auth)``.

    The neo4j driver takes credentials as a separate ``auth`` argument and does not read
    them from the URI, so any ``user:pass`` in the URL is extracted (and stripped from the
    returned driver URL). The ``database`` / ``db`` query parameter is likewise pulled out.
    """
    parsed = urlparse(url)
    auth = (unquote(parsed.username), unquote(parsed.password or "")) if parsed.username else None
    credentialless = urlparse(strip_url_credentials(url))

    pairs = parse_qsl(credentialless.query, keep_blank_values=True)
    database: str | None = None
    kept: list[tuple[str, str]] = []
    for k, v in pairs:
        if k.lower() in ("database", "db"):
            if database is None and v:
                database = v
            continue
        kept.append((k, v))
    new_query = urlencode(kept) if kept else ""
    return urlunparse(credentialless._replace(query=new_query)), database, auth


def _global_id_from_url(url: str) -> str:
    """Derive a stable global_id from a database URL, stripping credentials."""
    parsed = urlparse(strip_url_credentials(url))
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    canonical = urlunparse(parsed._replace(query=query))
    return f"url+{hashlib.sha256(canonical.encode()).hexdigest()}"


def _neo4j_global_id(driver_url: str, database: str | None) -> str:
    """Derive a stable cache id from canonical Neo4j driver params."""
    if database is None:
        return _global_id_from_url(driver_url)

    parsed = urlparse(driver_url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    pairs.append(("database", database))
    canonical = urlunparse(parsed._replace(query=urlencode(sorted(pairs))))
    return _global_id_from_url(canonical)


def is_database_file_path(path: str) -> bool:
    """Return whether ``path`` has a supported database-file extension."""
    return Path(path).suffix.lower() in _DB_FILE_SCHEMES


async def connect_url(
    source: str,
    *,
    display_name: str,
    read_only: bool = True,
    global_id: str | None = None,
    config: SQLConnectorConfig | Neo4jConnectorConfig | None = None,
) -> DataConnector:
    """Build the appropriate connector from a raw database URL or local db-file path.

    Normalizes the URL, dispatches to the Neo4j or SQL connector by scheme, and applies
    engine kwargs (e.g. BigQuery billing). Credentials come from the URL for every backend
    (SQLAlchemy reads them inline; for neo4j they are extracted and passed as the driver's
    ``auth``). Raises on a failed connection or, for BigQuery, a missing billing project.

    Args:
        source: A database URL (``postgresql://user:pass@…``, ``bigquery://…``,
            ``neo4j://user:pass@…``, …) or a local database-file path (``.sqlite`` / ``.duckdb``).
        display_name: Human-readable name stored in the connector schema.
        read_only: Request backend-appropriate read-only behavior. SQL callers
            still need read-only credentials or IAM for enforced security.
        global_id: Stable id for schema caching; derived from the URL if omitted.
        config: Backend-appropriate immutable connector configuration.

    Returns:
        A connected SQL or property-graph connector.

    Raises:
        ValueError: If the source is unsupported or required driver settings
            are invalid.
        TypeError: If ``config`` does not match the URL backend.
    """
    from tabulaflow.data.neo4j import Neo4jConnector
    from tabulaflow.data.sql import SQLConnector

    url = normalize_connection_url(source)
    if "://" not in url:
        raise ValueError(f"Unsupported database source: {source!r}; expected a database URL or SQLite/DuckDB file path")

    if _is_neo4j_bolt_url(url):
        if config is not None and not isinstance(config, Neo4jConnectorConfig):
            raise TypeError("Neo4j URLs require Neo4jConnectorConfig")
        driver_url, database, auth = _neo4j_driver_params(url)
        return await Neo4jConnector.from_url_async(
            url=driver_url,
            global_id=global_id,
            database=database,
            display_name=display_name,
            read_only=read_only,
            auth=auth,
            config=config,
        )

    if config is not None and not isinstance(config, SQLConnectorConfig):
        raise TypeError("SQL URLs require SQLConnectorConfig")
    return await SQLConnector.from_url_async(
        url=url,
        display_name=display_name,
        global_id=global_id,
        read_only=read_only,
        config=config,
    )
