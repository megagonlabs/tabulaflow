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
import tempfile
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


def _hf_parquet_glob(dataset_id: str, config: str, split: str | None = None) -> str:
    """Build a ``hf://`` glob pattern for auto-converted parquet files."""
    split_part = split if split else "*"
    return f"hf://datasets/{dataset_id}@~parquet/{config}/{split_part}/*.parquet"


def _hf_api_get(endpoint: str, dataset_id: str) -> dict[str, Any]:
    """Make a GET request to the HuggingFace datasets-server API."""
    import json
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    url = f"https://datasets-server.huggingface.co/{endpoint}?{urlencode({'dataset': dataset_id})}"
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


# ---------------------------------------------------------------------------
# DuckDB-native discovery & loading
# ---------------------------------------------------------------------------


def _init_duckdb(db_path: str) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection with httpfs and optional HF auth."""
    import duckdb as _duckdb

    conn = _duckdb.connect(db_path)
    conn.execute("INSTALL httpfs; LOAD httpfs;")

    hf_token_path = os.path.expanduser("~/.cache/huggingface/token")
    if os.path.isfile(hf_token_path):
        conn.execute("""
            CREATE SECRET IF NOT EXISTS hf_token (
                TYPE huggingface,
                PROVIDER credential_chain
            )
        """)
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
    """Create DuckDB tables or views from hf:// parquet globs."""
    kind = "TABLE" if materialize else "VIEW"
    table_names: list[str] = []

    for split_name in splits:
        table_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
        table_names.append(table_name)
        source = _hf_parquet_glob(dataset_id, config, split_name)

        sql = f'CREATE {kind} "{table_name}" AS SELECT * FROM \'{source}\''
        logger.info("Creating %s '%s' from %s", kind, table_name, source)
        conn.execute(sql)

    return table_names


def _load_hf_into_duckdb(
    db_path: str,
    dataset_id: str,
    subset: str | None,
    split_filter: str | None,
) -> tuple[list[str], bool]:
    """Discover metadata and load a HuggingFace dataset into DuckDB.

    Discovery (config resolution, split listing, size estimation) uses the
    HuggingFace datasets-server API to avoid DuckDB HTTP HEAD requests that
    trigger 429 rate limiting.  Only the final table/view creation uses DuckDB.

    Returns:
        A tuple of (table_names, materialized).
    """
    config = _resolve_config(dataset_id, subset)
    splits, total_size = _discover_splits_and_size(dataset_id, config)

    if split_filter:
        if split_filter not in splits:
            raise ValueError(
                f"Split '{split_filter}' not found. Available splits: {', '.join(splits)}"
            )
        splits = [split_filter]

    materialize = total_size > 0 and total_size < MATERIALIZE_THRESHOLD_BYTES
    strategy = "materialized" if materialize else "lazy view"
    size_str = _format_size(total_size) if total_size > 0 else "unknown size"
    logger.info("Loading HF dataset '%s' (%s) as %s", dataset_id, size_str, strategy)

    conn = _init_duckdb(db_path)
    try:
        table_names = _create_tables(conn, dataset_id, config, splits, materialize)
        return table_names, materialize
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
    data_dir: str | None = None,
    read_only: bool = True,
) -> SQLConnector:
    """Load a HuggingFace dataset into a DuckDB-backed SQLConnector.

    Uses DuckDB's native ``hf://`` protocol for data access and metadata
    discovery.  Small datasets are materialized for instant local queries;
    large datasets use lazy views.

    Args:
        dataset_url: A HuggingFace dataset URL.
        global_id: Globally unique identifier for the connection.
        db_name: Display name for the database. Defaults to the dataset name.
        data_dir: Directory to store the DuckDB file. If ``None``, a
            system temp directory is used.
        read_only: If True, block write statements.

    Returns:
        A :class:`SQLConnector` backed by a DuckDB database.
    """
    from mintq.db_connector.sql_conn import SQLConnector

    dataset_id, subset, split = parse_hf_dataset_url(dataset_url)

    if db_name is None:
        db_name = dataset_id.split("/")[-1]

    # Create DuckDB database.
    if data_dir is not None:
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, f"{db_name}.duckdb")
    else:
        fd, db_path = tempfile.mkstemp(suffix=".duckdb")
        os.close(fd)
        os.unlink(db_path)

    loop = asyncio.get_running_loop()
    table_names, materialized = await loop.run_in_executor(
        None, _load_hf_into_duckdb, db_path, dataset_id, subset, split,
    )

    url = f"duckdb:///{db_path}"
    connector = await SQLConnector.from_url_async(
        global_id=global_id,
        url=url,
        db_name=db_name,
        read_only=read_only,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    connector._temp_db_path = db_path

    strategy = "materialized" if materialized else "lazy view"
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
