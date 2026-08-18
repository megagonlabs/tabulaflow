"""Build a connector from a raw database URL or local database-file path.

A higher-level "smart constructor" on top of the type-specific ``from_url_async``
constructors: it normalizes a user-supplied URL (local db-file path -> scheme, sync ->
async driver), dispatches to the SQL or Neo4j connector by scheme, and applies
engine kwargs (e.g. BigQuery billing). Distinct from loaders (which *acquire*
external file/HuggingFace data) — this only opens a live connection.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from tabulaflow.data.config import Neo4jConnectorConfig, SQLConnectorConfig

if TYPE_CHECKING:
    from tabulaflow.data.base import DataConnector

# Local database-file extension -> SQLAlchemy scheme.
DB_FILE_SCHEMES: dict[str, str] = {
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


def normalize_url(raw: str) -> str:
    """Normalize a raw source to a connectable URL.

    A local database-file path becomes a file URL; a sync driver scheme is upgraded to
    its async equivalent. Anything else is returned unchanged.
    """
    # No scheme yet → it's a path; turn a known db-file extension into a file URL.
    # (Guarded by the scheme check so the function is idempotent — re-normalizing an
    # already-built URL that ends in e.g. ".sqlite" must not re-treat it as a path.)
    if "://" not in raw:
        for ext, scheme in DB_FILE_SCHEMES.items():
            if raw.lower().endswith(ext):
                return f"{scheme}:///{os.path.abspath(os.path.expanduser(raw))}"
        return raw

    scheme, rest = raw.split("://", 1)
    if "+" not in scheme and scheme in _ASYNC_DRIVER_UPGRADES:
        return f"{_ASYNC_DRIVER_UPGRADES[scheme]}://{rest}"
    return raw


def url_needs_password(url: str) -> bool:
    """Return True if the URL gives a username but no password — a strong hint that a
    password is expected (e.g. ``snowflake://user@account/db``), used to prompt for one
    or defer to the user. A heuristic: it can't tell password auth from trust/peer auth,
    and a URL with no username at all may still need credentials."""
    parsed = urlparse(url)
    return bool(parsed.username and not parsed.password and parsed.hostname)


def credentialless_url(url: str) -> str:
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
    auth = (parsed.username, parsed.password or "") if parsed.username else None
    netloc = (parsed.hostname or "") + (f":{parsed.port}" if parsed.port else "")

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    database: str | None = None
    kept: list[tuple[str, str]] = []
    for k, v in pairs:
        if k.lower() in ("database", "db"):
            if database is None and v:
                database = v
            continue
        kept.append((k, v))
    new_query = urlencode(kept) if kept else ""
    return urlunparse(parsed._replace(netloc=netloc, query=new_query)), database, auth


def _engine_kwargs_for_url(url: str) -> dict[str, Any]:
    scheme = url.split("://", 1)[0].split("+", 1)[0].lower()
    if scheme != "bigquery":
        return {}

    google_cloud_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_BILLING_PROJECT")
    if not google_cloud_project:
        raise ValueError("BigQuery billing project required: set GOOGLE_CLOUD_PROJECT (or GCP_BILLING_PROJECT).")

    engine_kwargs: dict[str, Any] = {"billing_project_id": google_cloud_project}
    google_application_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if google_application_credentials:
        engine_kwargs["credentials_path"] = google_application_credentials
    return engine_kwargs


def global_id_from_url(url: str) -> str:
    """Derive a stable global_id from a database URL, stripping credentials."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", credentialless_url(url))
    return f"cli+{safe}"


def _neo4j_global_id(driver_url: str, database: str | None) -> str:
    """Derive a stable cache id from canonical Neo4j driver params."""
    if database is None:
        return global_id_from_url(driver_url)

    parsed = urlparse(driver_url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    pairs.append(("database", database))
    canonical = urlunparse(parsed._replace(query=urlencode(sorted(pairs))))
    return global_id_from_url(canonical)


async def connect_url(
    raw_url: str,
    *,
    db_name: str,
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
        raw_url: A database URL (``postgresql://user:pass@…``, ``bigquery://…``,
            ``neo4j://user:pass@…``, …) or a local database-file path (``.sqlite`` / ``.duckdb``).
        db_name: Display name for the connector.
        read_only: Block write statements.
        global_id: Stable id for schema caching; derived from the URL if omitted.
        config: Backend-appropriate immutable connector configuration.
    """
    from tabulaflow.data.neo4j import Neo4jConnector
    from tabulaflow.data.sql import SQLConnector

    url = normalize_url(raw_url)

    if _is_neo4j_bolt_url(url):
        if config is not None and not isinstance(config, Neo4jConnectorConfig):
            raise TypeError("Neo4j URLs require Neo4jConnectorConfig")
        driver_url, database, auth = _neo4j_driver_params(url)
        gid = global_id or _neo4j_global_id(driver_url, database)
        return await Neo4jConnector.from_url_async(
            global_id=gid,
            url=driver_url,
            database=database,
            db_name=db_name,
            read_only=read_only,
            auth=auth,
            config=config,
        )

    if config is not None and not isinstance(config, SQLConnectorConfig):
        raise TypeError("SQL URLs require SQLConnectorConfig")
    gid = global_id or global_id_from_url(url)
    return await SQLConnector.from_url_async(
        global_id=gid,
        url=url,
        db_name=db_name,
        read_only=read_only,
        config=config,
        **_engine_kwargs_for_url(url),
    )
