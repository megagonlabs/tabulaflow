"""HuggingFace dataset loader that produces SQLConnector instances.

Uses DuckDB's native ``hf://`` protocol to query remote parquet files from
the HuggingFace Hub.  Small datasets (below ``MATERIALIZE_THRESHOLD_BYTES``)
are fully materialized into a local DuckDB table; larger datasets are exposed
as views with lazy, on-demand fetching.

Authentication is handled natively by DuckDB via the HuggingFace token at
``~/.cache/huggingface/token`` (written by ``huggingface-cli login``).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import duckdb

    from mintq.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)

_HF_DATASET_RE = re.compile(
    r"^https?://huggingface\.co/datasets/"
    r"(?P<owner>[^/]+)/(?P<dataset>[^/]+)"
    r"(?:/viewer/(?P<subset>[^/]+)(?:/(?P<split>[^/]+))?)?"
)

# Datasets smaller than this are fully materialized into DuckDB on connect.
# Larger datasets are exposed as views (lazy, on-demand fetching).
MATERIALIZE_THRESHOLD_BYTES = 500 * 1024 * 1024  # 500 MB


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------


def parse_hf_dataset_url(url: str) -> tuple[str, str | None, str | None]:
    """Parse a HuggingFace dataset URL into (dataset_id, subset, split).

    Args:
        url: A URL like ``https://huggingface.co/datasets/user/name``
            or ``https://huggingface.co/datasets/user/name/viewer/subset/split``.

    Returns:
        A tuple of ``(dataset_id, subset, split)`` where subset and split
        may be ``None``.

    Raises:
        ValueError: If the URL does not match the expected HuggingFace
            dataset pattern.
    """
    m = _HF_DATASET_RE.match(url)
    if not m:
        raise ValueError(
            f"Not a valid HuggingFace dataset URL: {url}\n"
            "Expected: https://huggingface.co/datasets/<owner>/<dataset>[/viewer/<subset>[/<split>]]"
        )
    dataset_id = f"{m.group('owner')}/{m.group('dataset')}"
    subset = m.group("subset")
    split = m.group("split")
    return dataset_id, subset, split


def is_hf_dataset_url(url: str) -> bool:
    """Return True if the URL points to a HuggingFace dataset."""
    return bool(_HF_DATASET_RE.match(url))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_size(n_bytes: int) -> str:
    """Format bytes as a human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n_bytes) < 1024:
            return f"{n_bytes:.0f} {unit}" if unit == "B" else f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024  # type: ignore[assignment]
    return f"{n_bytes:.1f} TB"


def _fetch_hf_description(dataset_id: str) -> str | None:
    """Fetch the dataset card description from HuggingFace Hub."""
    try:
        from huggingface_hub import dataset_info

        info = dataset_info(dataset_id)
        desc = info.description
        return desc.strip() if desc else None
    except Exception:
        return None


def _hf_api_get(endpoint: str, dataset_id: str, **params: str) -> dict[str, Any]:
    """Make a GET request to the HuggingFace datasets-server API."""
    import json
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    query = {"dataset": dataset_id, **params}
    url = f"https://datasets-server.huggingface.co/{endpoint}?{urlencode(query)}"
    req = Request(url, headers={"User-Agent": "mintq"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())  # type: ignore[no-any-return]


def _fetch_splits_from_api(dataset_id: str) -> list[dict[str, Any]]:
    """Fetch split entries from the HuggingFace datasets-server API.

    Returns:
        A list of dicts with keys ``config`` and ``split``.

    Raises:
        ValueError: If the dataset has no splits.
    """
    data = _hf_api_get("splits", dataset_id)
    splits: list[dict[str, Any]] = data.get("splits", [])
    if not splits:
        raise ValueError(
            f"No splits found for dataset '{dataset_id}'. "
            "The dataset may be gated, private, or not yet indexed."
        )
    return splits


def _fetch_configs_from_api(dataset_id: str) -> list[str]:
    """Fetch available config names via the HuggingFace datasets-server API."""
    return sorted({s["config"] for s in _fetch_splits_from_api(dataset_id)})


def _fetch_parquet_urls(dataset_id: str, config: str, split: str) -> list[str]:
    """Fetch direct parquet file URLs for a specific config/split."""
    data = _hf_api_get("parquet", dataset_id, config=config, split=split)
    return [f["url"] for f in data.get("parquet_files", [])]


# ---------------------------------------------------------------------------
# DuckDB loading
# ---------------------------------------------------------------------------


def _init_duckdb(db_path: str) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection with httpfs."""
    import duckdb as _duckdb

    conn = _duckdb.connect(db_path)
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    return conn


def _resolve_config(dataset_id: str, subset: str | None) -> str:
    """Resolve which config to use via the HuggingFace API.

    Args:
        dataset_id: HuggingFace dataset identifier.
        subset: User-specified config, or None.

    Returns:
        The config name to use.

    Raises:
        ValueError: If the config doesn't exist or multiple configs exist
            and none was specified.
    """
    configs = _fetch_configs_from_api(dataset_id)

    if subset is not None:
        if subset not in configs:
            raise ValueError(
                f"Subset '{subset}' not found. Available subsets: {', '.join(configs)}"
            )
        return subset

    if "default" in configs:
        return "default"
    if len(configs) == 1:
        return configs[0]

    listing = ", ".join(configs[:20])
    if len(configs) > 20:
        listing += f", ... ({len(configs)} total)"
    raise ValueError(
        f"Dataset '{dataset_id}' has {len(configs)} subsets: {listing}\n"
        f"Specify one via: https://huggingface.co/datasets/{dataset_id}/viewer/<subset>"
    )


def _discover_splits_and_size(dataset_id: str, config: str) -> tuple[list[str], int]:
    """Discover splits and total size via the HuggingFace API.

    Returns:
        A tuple of (sorted split names, total parquet size in bytes).
    """
    data = _hf_api_get("size", dataset_id)

    total_size = 0
    splits: list[str] = []
    for entry in data.get("size", {}).get("splits", []):
        if entry.get("config") == config:
            splits.append(entry["split"])
            total_size += int(entry.get("num_bytes_parquet_files", 0))

    if not splits:
        raise ValueError(f"No splits found for '{dataset_id}' config '{config}'.")
    return sorted(splits), total_size


def _create_tables(
    conn: duckdb.DuckDBPyConnection,
    dataset_id: str,
    config: str,
    splits: list[str],
    materialize: bool,
) -> list[str]:
    """Create DuckDB tables or views from explicit parquet URLs.

    Uses the HuggingFace datasets-server ``/parquet`` API to get direct
    download URLs, avoiding DuckDB ``hf://`` glob resolution which triggers
    HTTP HEAD requests that are easily rate-limited (429).
    """
    table_names: list[str] = []

    for split_name in splits:
        urls = _fetch_parquet_urls(dataset_id, config, split_name)
        if not urls:
            raise ValueError(
                f"No parquet files found for '{dataset_id}' config '{config}' split '{split_name}'."
            )
        url_list = ", ".join(f"'{u}'" for u in urls)
        source = f"read_parquet([{url_list}])"

        base_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
        if materialize:
            sql = f'CREATE TABLE "{base_name}" AS SELECT * FROM {source}'
            logger.info("Creating TABLE '%s' from %d parquet files", base_name, len(urls))
            table_names.append(base_name)
            conn.execute(sql)
        else:
            # Full-data view over all parquet files.
            view_sql = f'CREATE VIEW "{base_name}" AS SELECT * FROM {source}'
            logger.info("Creating VIEW '%s' from %d parquet files", base_name, len(urls))
            conn.execute(view_sql)
            table_names.append(base_name)

            # Materialized 1k sample from the first parquet file.
            sample_name = f"{base_name}_10k_sample"
            first_url = urls[0]
            sample_sql = f"CREATE TABLE \"{sample_name}\" AS SELECT * FROM read_parquet('{first_url}') LIMIT 10000"
            logger.info("Creating TABLE '%s' (1k sample) from first parquet file", sample_name)
            conn.execute(sample_sql)
            table_names.append(sample_name)

    return table_names


def _load_hf_into_duckdb(
    dataset_id: str,
    subset: str | None,
    split_filter: str | None,
) -> tuple[str, list[str], bool]:
    """Discover metadata and load a HuggingFace dataset into DuckDB.

    Discovery (config resolution, split listing, size estimation) uses the
    HuggingFace datasets-server API to avoid DuckDB HTTP HEAD requests that
    trigger 429 rate limiting.  Only the final table/view creation uses DuckDB.

    Returns:
        A tuple of (db_path, table_names, materialized).
    """
    config = _resolve_config(dataset_id, subset)
    splits, total_size = _discover_splits_and_size(dataset_id, config)

    if split_filter:
        if split_filter not in splits:
            raise ValueError(
                f"Split '{split_filter}' not found. Available splits: {', '.join(splits)}"
            )
        splits = [split_filter]

    # Cache path uses the resolved config name.
    cache_dir = os.path.join(os.path.expanduser("~"), ".mintq", "hf_cache")
    os.makedirs(cache_dir, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", f"{dataset_id}__{config}")
    db_path = os.path.join(cache_dir, f"{safe_name}.duckdb")

    materialize = total_size > 0 and total_size < MATERIALIZE_THRESHOLD_BYTES
    strategy = "materialized" if materialize else "sample"
    size_str = _format_size(total_size) if total_size > 0 else "unknown size"
    logger.info("Loading HF dataset '%s' (%s) as %s", dataset_id, size_str, strategy)

    conn = _init_duckdb(db_path)
    try:
        # Check if already loaded (cached DuckDB file from a previous session).
        existing = {
            r[0]
            for r in conn.sql(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }
        if existing:
            logger.info("Using cached DuckDB file with tables: %s", ", ".join(sorted(existing)))
            return db_path, sorted(existing), materialize

        table_names = _create_tables(conn, dataset_id, config, splits, materialize)
        return db_path, table_names, materialize
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def load_hf_dataset(
    dataset_url: str,
    *,
    global_id: str,
    db_name: str | None = None,
    read_only: bool = True,
) -> SQLConnector:
    """Load a HuggingFace dataset into a DuckDB-backed SQLConnector.

    Small datasets are fully materialized.  Large datasets get a lazy view
    over all parquet files plus a materialized 10k-row sample table.
    DuckDB files are cached in ``~/.mintq/hf_cache/`` across sessions.

    Args:
        dataset_url: A HuggingFace dataset URL.
        global_id: Globally unique identifier for the connection.
        db_name: Display name for the database. Defaults to the dataset name.
        read_only: If True, block write statements.

    Returns:
        A :class:`SQLConnector` backed by a DuckDB database.
    """
    from mintq.db_connector.sql_conn import SQLConnector

    dataset_id, subset, split = parse_hf_dataset_url(dataset_url)

    if db_name is None:
        db_name = dataset_id.split("/")[-1]

    loop = asyncio.get_running_loop()
    db_path, table_names, materialized = await loop.run_in_executor(
        None, _load_hf_into_duckdb, dataset_id, subset, split,
    )

    url = f"duckdb:///{db_path}"
    connector = await SQLConnector.from_url_async(
        global_id=global_id,
        url=url,
        db_name=db_name,
        read_only=read_only,
        enable_schema_caching=False,
        enable_query_caching=False,
        duckdb_init_sql=["LOAD httpfs"] if not materialized else None,
    )
    strategy = "materialized" if materialized else "sample"
    for table in connector.schema.tables:
        if table.name in table_names:
            table.description = f"Imported from HuggingFace parquet ({strategy})"

    # Fetch dataset description for the agent.
    description = await loop.run_in_executor(None, _fetch_hf_description, dataset_id)
    if description:
        connector.db_description = (
            f"Source: HuggingFace dataset {dataset_url}\n\n"
            f"<readme>\n{description}\n</readme>"
        )

    return connector
