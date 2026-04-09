"""HuggingFace dataset loader that produces SQLConnector instances.

Uses DuckDB's httpfs extension to query remote parquet files directly from
the HuggingFace Hub.  Small datasets (below ``MATERIALIZE_THRESHOLD_BYTES``)
are fully materialized into a local DuckDB table for instant queries; larger
datasets are exposed as views so only the requested columns and rows are
fetched on demand.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
from typing import TYPE_CHECKING
from urllib.request import Request, urlopen

if TYPE_CHECKING:
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


def _hf_api_get(path: str, params: dict[str, str]) -> dict:
    """Make a GET request to the HuggingFace datasets-server API."""
    import json
    from urllib.parse import urlencode

    url = f"https://datasets-server.huggingface.co/{path}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "mintq"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _fetch_configs(dataset_id: str) -> list[str]:
    """Fetch available config names for a dataset via the splits endpoint."""
    data = _hf_api_get("splits", {"dataset": dataset_id})
    splits = data.get("splits", [])
    if not splits:
        raise ValueError(
            f"No splits found for dataset '{dataset_id}'. "
            "The dataset may be gated, private, or not yet indexed."
        )
    return sorted({s["config"] for s in splits})


def _fetch_parquet_urls(dataset_id: str, subset: str | None) -> dict[str, list[str]]:
    """Fetch parquet file URLs from the HuggingFace datasets-server API.

    For large datasets with many configs, the ``/parquet`` endpoint without a
    ``config`` parameter may return a 501 because the response exceeds the
    server's size limit.  This function handles that by first discovering
    configs via the ``/splits`` endpoint, then querying ``/parquet`` with the
    specific config.

    Args:
        dataset_id: The dataset identifier (e.g. ``"megagonlabs/cypherbench"``).
        subset: Optional config/subset name.

    Returns:
        A mapping of split name to list of parquet file URLs.

    Raises:
        ValueError: If the API returns an error or no parquet files are found.
    """
    # If a specific subset is requested, query directly with config param.
    if subset is not None:
        return _fetch_parquet_urls_for_config(dataset_id, subset)

    # Try the simple endpoint first (works for most datasets).
    from urllib.error import HTTPError

    try:
        data = _hf_api_get("parquet", {"dataset": dataset_id})
    except HTTPError as e:
        if e.code == 501:
            # Response too large — dataset has many configs. Discover them
            # and ask the user to pick one.
            configs = _fetch_configs(dataset_id)
            if len(configs) > 1:
                listing = ", ".join(configs[:20])
                if len(configs) > 20:
                    listing += f", ... ({len(configs)} total)"
                raise ValueError(
                    f"Dataset '{dataset_id}' has {len(configs)} subsets: {listing}\n"
                    f"Specify one via: https://huggingface.co/datasets/{dataset_id}/viewer/<subset>"
                ) from None
            # Single config but still 501 — try with explicit config.
            return _fetch_parquet_urls_for_config(dataset_id, configs[0])
        raise

    if "error" in data:
        raise ValueError(f"HuggingFace API error: {data['error']}")

    parquet_files = data.get("parquet_files", [])
    if not parquet_files:
        raise ValueError(
            f"No parquet files found for dataset '{dataset_id}'. "
            "The dataset may be gated, private, or not yet converted."
        )

    # If no subset specified and multiple configs exist, require the user to choose.
    configs = sorted({f.get("config", "default") for f in parquet_files})
    if len(configs) > 1:
        listing = ", ".join(configs[:20])
        if len(configs) > 20:
            listing += f", ... ({len(configs)} total)"
        raise ValueError(
            f"Dataset '{dataset_id}' has multiple subsets: {listing}\n"
            f"Specify one via: https://huggingface.co/datasets/{dataset_id}/viewer/<subset>"
        )

    return _parquet_files_to_split_urls(parquet_files, dataset_id)


def _fetch_parquet_urls_for_config(
    dataset_id: str, config: str
) -> dict[str, list[str]]:
    """Fetch parquet URLs for a specific config."""
    data = _hf_api_get("parquet", {"dataset": dataset_id, "config": config})

    if "error" in data:
        # Check if it's an unknown config.
        configs = _fetch_configs(dataset_id)
        if config not in configs:
            raise ValueError(
                f"Subset '{config}' not found. Available subsets: {', '.join(configs)}"
            )
        raise ValueError(f"HuggingFace API error: {data['error']}")

    parquet_files = data.get("parquet_files", [])
    if not parquet_files:
        raise ValueError(f"No parquet files found for '{dataset_id}' config '{config}'.")

    return _parquet_files_to_split_urls(parquet_files, dataset_id)


def _parquet_files_to_split_urls(
    parquet_files: list[dict], dataset_id: str
) -> dict[str, list[str]]:
    """Convert a list of parquet file dicts to a split -> URLs mapping."""
    result: dict[str, list[str]] = {}
    total_size = 0
    for f in parquet_files:
        split_name = f.get("split", "train")
        result.setdefault(split_name, []).append(f["url"])
        total_size += f.get("size", 0)

    logger.info(
        "Found %d parquet file(s) across %d split(s) for '%s' (%s)",
        sum(len(v) for v in result.values()),
        len(result),
        dataset_id,
        _format_size(total_size),
    )
    return result


def get_hf_dataset_info(dataset_url: str) -> tuple[int | None, bool]:
    """Return (total_parquet_size_bytes, False) for a HuggingFace dataset.

    The second element is always False since remote parquet loading does not
    use a local cache.
    """
    dataset_id, subset, _split = parse_hf_dataset_url(dataset_url)
    try:
        params: dict[str, str] = {"dataset": dataset_id}
        if subset:
            params["config"] = subset
        data = _hf_api_get("parquet", params)
        parquet_files = data.get("parquet_files", [])
        total = sum(f.get("size", 0) for f in parquet_files)
        return total if total > 0 else None, False
    except Exception:
        return None, False


def _load_hf_parquet_into_duckdb(
    db_path: str,
    parquet_urls: dict[str, list[str]],
    split_filter: str | None,
    materialize: bool,
) -> dict[str, list[str]]:
    """Create DuckDB tables or views from remote HuggingFace parquet files.

    Args:
        db_path: Path to the DuckDB database file.
        parquet_urls: Mapping of split name to list of parquet URLs.
        split_filter: If set, only load this split. Otherwise load all.
        materialize: If True, create TABLE (full download). If False,
            create VIEW (lazy, on-demand).

    Returns:
        Mapping of table/view name to list of source parquet URLs.
    """
    import duckdb

    conn = duckdb.connect(db_path)
    table_url_map: dict[str, list[str]] = {}
    try:
        conn.execute("INSTALL httpfs; LOAD httpfs;")

        splits = {split_filter: parquet_urls[split_filter]} if split_filter else parquet_urls
        kind = "TABLE" if materialize else "VIEW"

        for split_name, urls in splits.items():
            table_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
            table_url_map[table_name] = urls

            if len(urls) == 1:
                source = f"'{urls[0]}'"
            else:
                url_list = ", ".join(f"'{u}'" for u in urls)
                source = f"read_parquet([{url_list}])"

            sql = f'CREATE {kind} "{table_name}" AS SELECT * FROM {source}'
            logger.info("Creating %s '%s' from %d parquet file(s)", kind, table_name, len(urls))
            conn.execute(sql)
    finally:
        conn.close()

    return table_url_map


async def load_hf_dataset(
    dataset_url: str,
    *,
    global_id: str,
    db_name: str | None = None,
    data_dir: str | None = None,
    read_only: bool = True,
) -> "SQLConnector":
    """Load a HuggingFace dataset into a DuckDB-backed SQLConnector.

    Uses the HuggingFace datasets-server API to discover parquet file URLs,
    then either materializes them (small datasets) or creates lazy views
    (large datasets) in a DuckDB database.

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

    loop = asyncio.get_running_loop()

    # Fetch parquet URLs from the datasets-server API.
    parquet_urls = await loop.run_in_executor(None, _fetch_parquet_urls, dataset_id, subset)

    # Filter to requested split if specified.
    if split and split not in parquet_urls:
        available = ", ".join(sorted(parquet_urls))
        raise ValueError(f"Split '{split}' not found. Available splits: {available}")

    # Calculate total parquet size to decide materialization strategy.
    relevant = {split: parquet_urls[split]} if split else parquet_urls
    total_size = 0
    for urls in relevant.values():
        for url in urls:
            try:
                req = Request(url, method="HEAD", headers={"User-Agent": "mintq"})
                with urlopen(req, timeout=10) as resp:
                    cl = resp.headers.get("Content-Length")
                    if cl:
                        total_size += int(cl)
            except Exception:
                pass

    materialize = total_size < MATERIALIZE_THRESHOLD_BYTES
    strategy = "materialized" if materialize else "lazy view"
    logger.info(
        "Loading HF dataset '%s' (%s) as %s",
        dataset_id,
        _format_size(total_size),
        strategy,
    )

    # Create DuckDB database with tables or views.
    if data_dir is not None:
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, f"{db_name}.duckdb")
    else:
        fd, db_path = tempfile.mkstemp(suffix=".duckdb")
        os.close(fd)
        os.unlink(db_path)

    table_url_map = await loop.run_in_executor(
        None, _load_hf_parquet_into_duckdb, db_path, parquet_urls, split, materialize,
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

    for table in connector.schema.tables:
        urls = table_url_map.get(table.name, [])
        if urls:
            src = f"HuggingFace parquet ({strategy})"
            table.description = f"Imported from {src}, {len(urls)} file(s)"

    # Fetch dataset description for the agent.
    description = await loop.run_in_executor(None, _fetch_hf_description, dataset_id)
    if description:
        connector.db_description = (
            f"Source: HuggingFace dataset {dataset_url}\n\n"
            f"<readme>\n{description}\n</readme>"
        )

    return connector
