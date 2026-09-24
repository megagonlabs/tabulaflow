"""Resolve user-facing sources and open data connectors."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

from tabulaflow.data.catalog import (
    DEFAULT_DATA_SOURCE_DEFINITIONS,
    DataSourceDefinition,
    resolve_data_source_definition,
)
from tabulaflow.data.config import (
    DataSourceConnectorConfigs,
    Neo4jConnectorConfig,
    SPARQLConnectorConfig,
    SQLConnectorConfig,
)
from tabulaflow.data.protocols import DataConnector
from tabulaflow.core._cache import stable_cache_key

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


def _split_url_credentials(url: str) -> tuple[str, tuple[str, str] | None]:
    """Return a credential-free URL and decoded username/password, if present."""
    parsed = urlparse(url)
    if parsed.hostname is None:
        return url, None

    auth = (unquote(parsed.username), unquote(parsed.password or "")) if parsed.username else None
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host + (f":{parsed.port}" if parsed.port else "")
    return urlunparse(parsed._replace(netloc=netloc)), auth


def strip_url_credentials(url: str) -> str:
    """Return ``url`` with any username/password removed."""
    return _split_url_credentials(url)[0]


def redact_url_password(url: str) -> str:
    """Return ``url`` with its password replaced by a visible placeholder."""
    parsed = urlparse(url)
    if parsed.password is None:
        return url
    userinfo, separator, host = parsed.netloc.rpartition("@")
    username, password_separator, _ = userinfo.partition(":")
    if not separator or not password_separator:
        return url
    return urlunparse(parsed._replace(netloc=f"{username}:***@{host}"))


def _is_neo4j_bolt_url(url: str) -> bool:
    if "://" not in url:
        return False
    scheme = url.split("://", 1)[0].lower()
    return scheme == "neo4j" or scheme.startswith("neo4j+") or scheme == "bolt" or scheme.startswith("bolt+")


def _is_sparql_url(url: str) -> bool:
    if "://" not in url:
        return False
    scheme = url.split("://", 1)[0].lower()
    return scheme == "sparql" or scheme.startswith("sparql+")


def _sparql_endpoint_params(url: str) -> tuple[str, tuple[str, str] | None]:
    """Split a SPARQL connection URL into its HTTP endpoint and Basic auth."""
    credentialless_url, auth = _split_url_credentials(url)
    parsed = urlparse(credentialless_url)
    if parsed.scheme.lower() not in {"sparql+http", "sparql+https"}:
        raise ValueError("SPARQL connection URL must use sparql+http or sparql+https")
    endpoint_scheme = parsed.scheme.lower().removeprefix("sparql+")
    return urlunparse(parsed._replace(scheme=endpoint_scheme)), auth


def _neo4j_driver_params(url: str) -> tuple[str, str | None, tuple[str, str] | None]:
    """Split a neo4j/bolt URL into ``(driver_url, database, auth)``.

    The neo4j driver takes credentials as a separate ``auth`` argument and does not read
    them from the URI, so any ``user:pass`` in the URL is extracted (and stripped from the
    returned driver URL). The ``database`` / ``db`` query parameter is likewise pulled out.
    """
    credentialless_url, auth = _split_url_credentials(url)
    credentialless = urlparse(credentialless_url)

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


def _global_id_from_url(url: str, *, principal: str | None = None) -> str:
    """Derive a stable global ID from a URL and authenticated identity."""
    source = urlparse(url)
    if principal is None and source.username is not None:
        principal = unquote(source.username)
    parsed = urlparse(strip_url_credentials(url))
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    canonical = urlunparse(parsed._replace(query=query))
    return f"url+{stable_cache_key({'url': canonical, 'principal': principal})}"


def _neo4j_global_id(driver_url: str, database: str | None, *, principal: str | None = None) -> str:
    """Derive a stable cache id from canonical Neo4j driver params."""
    if database is None:
        return _global_id_from_url(driver_url, principal=principal)

    parsed = urlparse(driver_url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    pairs.append(("database", database))
    canonical = urlunparse(parsed._replace(query=urlencode(sorted(pairs))))
    return _global_id_from_url(canonical, principal=principal)


def is_database_file_path(path: str) -> bool:
    """Return whether ``path`` has a supported database-file extension."""
    return Path(path).suffix.lower() in _DB_FILE_SCHEMES


async def connect_url(
    source: str,
    *,
    display_name: str | None = None,
    read_only: bool = True,
    global_id: str | None = None,
    config: SQLConnectorConfig | Neo4jConnectorConfig | SPARQLConnectorConfig | None = None,
) -> DataConnector:
    """Build the appropriate connector from an explicit connection URL.

    Normalizes the URL and dispatches by explicit connector scheme. SQLAlchemy
    consumes SQL URL credentials inline; Neo4j and SPARQL credentials are
    extracted and passed separately to their drivers. SPARQL endpoints are not
    contacted until queried.

    Args:
        source: A SQL, Neo4j, or explicit ``sparql+http(s)`` connection URL.
            Examples include
            ``postgresql://user:pass@host/db``, ``bigquery://project/dataset``,
            ``neo4j+s://user:pass@host``, ``sparql+https://query.wikidata.org/sparql``,
            ``sqlite+aiosqlite:///data.sqlite``, and ``duckdb:///data.duckdb``.
        display_name: Human-readable name stored in the connector schema.
            Inferred by the selected connector when omitted.
        read_only: Request backend-appropriate read-only behavior. SQL callers
            still need read-only credentials or IAM for enforced security.
        global_id: Stable identity of the source and authorization context used
            for caching and provenance. Derived from the URL and non-secret
            authenticated identity, such as a username, when omitted.
        config: Backend-appropriate immutable connector configuration.

    Returns:
        A connected SQL, property-graph, or RDF connector.

    Raises:
        ValueError: If the source is unsupported or required driver settings
            are invalid.
        TypeError: If ``config`` does not match the URL backend.
    """
    if "://" not in source:
        raise ValueError(f"Unsupported connection source: {source!r}; expected an explicit connection URL")
    url = normalize_connection_url(source)

    if _is_sparql_url(url):
        from tabulaflow.data.sparql import SPARQLConnector

        if config is not None and not isinstance(config, SPARQLConnectorConfig):
            raise TypeError("SPARQL URLs require SPARQLConnectorConfig")
        endpoint_url, auth = _sparql_endpoint_params(url)
        return await SPARQLConnector.from_url_async(
            url=endpoint_url,
            display_name=display_name,
            global_id=global_id,
            read_only=read_only,
            auth=auth,
            config=config,
        )

    if _is_neo4j_bolt_url(url):
        from tabulaflow.data.neo4j import Neo4jConnector

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

    if urlparse(url).scheme.lower() in {"http", "https"}:
        raise ValueError("HTTP URLs are not inferred to be SPARQL endpoints; use sparql+http:// or sparql+https://")

    if config is not None and not isinstance(config, SQLConnectorConfig):
        raise TypeError("SQL URLs require SQLConnectorConfig")
    from tabulaflow.data.sql import SQLConnector

    return await SQLConnector.from_url_async(
        url=url,
        display_name=display_name,
        global_id=global_id,
        read_only=read_only,
        config=config,
    )


def _file_source_global_id(paths: Sequence[str], display_name: str) -> str:
    canonical = "\0".join([*(os.path.abspath(path) for path in paths), display_name])
    return f"files+{hashlib.sha256(canonical.encode()).hexdigest()}"


def _combine_descriptions(curated: str, discovered: str | None) -> str:
    if not discovered or discovered.strip() == curated.strip():
        return curated
    return f"{curated.rstrip()}\n\n{discovered.lstrip()}"


def _is_data_file(path: str) -> bool:
    from tabulaflow.data.loaders.files import DATA_FILE_EXTENSIONS

    return Path(path).suffix.lower() in DATA_FILE_EXTENSIONS


def _require_file(path: str) -> str:
    expanded = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(expanded):
        raise FileNotFoundError(f"no such file: {path!r}")
    return expanded


async def _connect_files(
    paths: Sequence[str],
    *,
    display_name: str,
    data_dir: Path | None,
    read_only: bool,
    configs: DataSourceConnectorConfigs | None,
) -> DataConnector:
    from tabulaflow.data.loaders.files import load_files

    if not paths or not all(_is_data_file(path) for path in paths):
        raise ValueError("multiple sources are supported only for local data files")
    resolved = [_require_file(path) for path in paths]
    return await load_files(
        global_id=_file_source_global_id(resolved, display_name),
        file_paths=resolved,
        display_name=display_name,
        data_dir=str(data_dir) if data_dir is not None else None,
        read_only=read_only,
        config=configs.sql if configs is not None else None,
    )


async def _connect_single_source(
    source: str,
    *,
    display_name: str,
    data_dir: Path | None,
    read_only: bool,
    configs: DataSourceConnectorConfigs | None,
) -> DataConnector:
    from tabulaflow.data.loaders.huggingface import is_hf_dataset_url, load_hf_dataset

    if is_hf_dataset_url(source):
        return await load_hf_dataset(
            source,
            display_name=display_name,
            read_only=read_only,
            config=configs.sql if configs is not None else None,
        )
    if "huggingface.co" in source:
        raise ValueError(
            "unsupported Hugging Face URL; expected "
            "https://huggingface.co/datasets/<owner>/<dataset>[/viewer/<subset>[/<split>]]"
        )
    if _is_data_file(source):
        return await _connect_files(
            (source,),
            display_name=display_name,
            data_dir=data_dir,
            read_only=read_only,
            configs=configs,
        )
    if is_database_file_path(source):
        path = _require_file(source)
        return await connect_url(
            normalize_connection_url(path),
            display_name=display_name,
            read_only=read_only,
            config=configs.sql if configs is not None else None,
        )
    if "://" in source:
        config: SQLConnectorConfig | Neo4jConnectorConfig | SPARQLConnectorConfig | None = None
        if configs is not None:
            normalized = normalize_connection_url(source)
            if _is_sparql_url(normalized):
                config = configs.sparql
            elif _is_neo4j_bolt_url(normalized):
                config = configs.neo4j
            else:
                config = configs.sql
        if config is None:
            return await connect_url(source, display_name=display_name, read_only=read_only)
        return await connect_url(source, display_name=display_name, read_only=read_only, config=config)
    if os.path.exists(os.path.expanduser(source)):
        raise ValueError(f"unsupported local data source: {source!r}")
    raise ValueError(
        f"unsupported data source: {source!r}; expected a catalog id, supported file, "
        "Hugging Face dataset URL, or explicit connection URL"
    )


async def connect_data_source(
    source: str | Sequence[str],
    *,
    display_name: str,
    definitions: Sequence[DataSourceDefinition] = DEFAULT_DATA_SOURCE_DEFINITIONS,
    data_dir: Path | None = None,
    read_only: bool = True,
    configs: DataSourceConnectorConfigs | None = None,
) -> DataConnector:
    """Connect or load a user-facing source into a queryable connector.

    Args:
        source: Catalog identifier, connection URL, Hugging Face dataset URL,
            local database path, local data-file path, or a sequence of local
            data-file paths.
        display_name: Human-readable name stored in the connector schema.
        definitions: Curated source definitions used for identifier and exact-locator
            resolution.
        data_dir: Directory for loader-owned DuckDB files.
        read_only: Whether the returned connector blocks write queries.
        configs: Backend-specific connector policies. Connector defaults are
            used when omitted.

    Returns:
        A connected, queryable data connector.

    Raises:
        FileNotFoundError: If a referenced local file does not exist.
        ValueError: If the source form is unsupported or incompatible with the
            other supplied sources.
    """
    sources = (source,) if isinstance(source, str) else tuple(source)
    if not sources:
        raise ValueError("at least one data source is required")
    if len(sources) > 1:
        return await _connect_files(
            sources,
            display_name=display_name,
            data_dir=data_dir,
            read_only=read_only,
            configs=configs,
        )

    raw_source = sources[0]
    definition = resolve_data_source_definition(raw_source, definitions)
    effective_source = definition.source if definition is not None else raw_source
    connector = await _connect_single_source(
        effective_source,
        display_name=display_name,
        data_dir=data_dir,
        read_only=read_only,
        configs=configs,
    )
    if definition is not None:
        connector.schema.description = _combine_descriptions(definition.description, connector.schema.description)
    return connector
