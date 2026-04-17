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
    """Fetch the full dataset README from HuggingFace Hub.

    Downloads the README.md file directly rather than using dataset_info(),
    which returns a truncated description for large dataset cards.
    """
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(dataset_id, "README.md", repo_type="dataset")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Strip YAML frontmatter.
        content = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL).strip()
        return content or None
    except Exception:
        return None


def _hf_api_get(endpoint: str, dataset_id: str, **params: str) -> dict[str, Any]:
    """Make a GET request to the HuggingFace datasets-server API."""
    import json
    from urllib.error import HTTPError
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    query = {"dataset": dataset_id, **params}
    url = f"https://datasets-server.huggingface.co/{endpoint}?{urlencode(query)}"
    req = Request(url, headers={"User-Agent": "mintq"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())  # type: ignore[no-any-return]
    except HTTPError as e:
        if e.code in (501, 500):
            try:
                detail = json.loads(e.read().decode()).get("error", "")
            except Exception:
                detail = ""
            msg = f"Dataset '{dataset_id}' is not indexed by the HuggingFace datasets server (HTTP {e.code})."
            if detail:
                msg += f"\nServer response: {detail}"
            raise ValueError(msg) from None
        raise


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
    return [f["url"] for f in data.get("parquet_files", []) if f.get("split") == split]


# ---------------------------------------------------------------------------
# DuckDB loading
# ---------------------------------------------------------------------------


def _init_duckdb(db_path: str) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection with httpfs."""
    import duckdb

    conn = duckdb.connect(db_path)
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


def _discover_splits_and_size(dataset_id: str, config: str) -> dict[str, int]:
    """Discover splits and per-split sizes via the HuggingFace API.

    Returns:
        A dict mapping split name to parquet size in bytes.
    """
    data = _hf_api_get("size", dataset_id)

    split_sizes: dict[str, int] = {}
    for entry in data.get("size", {}).get("splits", []):
        if entry.get("config") == config:
            split_sizes[entry["split"]] = int(entry.get("num_bytes_parquet_files", 0))

    if not split_sizes:
        raise ValueError(f"No splits found for '{dataset_id}' config '{config}'.")
    return split_sizes


def _create_tables(
    conn: duckdb.DuckDBPyConnection,
    dataset_id: str,
    config: str,
    split_sizes: dict[str, int],
) -> list[str]:
    """Create DuckDB tables or views from explicit parquet URLs.

    Uses the HuggingFace datasets-server ``/parquet`` API to get direct
    download URLs, avoiding DuckDB ``hf://`` glob resolution which triggers
    HTTP HEAD requests that are easily rate-limited (429).

    Each split is independently materialized or sampled based on its size.
    """
    table_names: list[str] = []

    for split_name, size in split_sizes.items():
        urls = _fetch_parquet_urls(dataset_id, config, split_name)
        if not urls:
            raise ValueError(
                f"No parquet files found for '{dataset_id}' config '{config}' split '{split_name}'."
            )
        url_list = ", ".join(f"'{u}'" for u in urls)
        source = f"read_parquet([{url_list}])"

        base_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
        materialize = size > 0 and size < MATERIALIZE_THRESHOLD_BYTES
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
            sample_name = f"{base_name}_sample"
            first_url = urls[0]
            sample_sql = f"CREATE TABLE \"{sample_name}\" AS SELECT * FROM read_parquet('{first_url}') LIMIT 1000"
            logger.info("Creating TABLE '%s' (at most 1k sample) from first parquet file", sample_name)
            conn.execute(sample_sql)
            table_names.append(sample_name)

    return table_names


def _db_path(cache_dir: str, dataset_id: str, config: str, split_filter: str | None) -> str:
    """Build the cache file path for a dataset/config/split combination."""
    suffix = f"{dataset_id}__{config}"
    if split_filter:
        suffix += f"__{split_filter}"
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", suffix)
    return os.path.join(cache_dir, f"{safe_name}.duckdb")


def _try_cache(db_path: str) -> list[str] | None:
    """Return cached table names if the DuckDB file is valid, else None.

    Removes incomplete cache files (e.g. from interrupted runs).
    """
    if not os.path.exists(db_path):
        return None
    import duckdb

    with duckdb.connect(db_path, read_only=True) as conn:
        tables = sorted(
            r[0]
            for r in conn.sql(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        )
    if tables:
        logger.info("Using cached DuckDB file with tables: %s", ", ".join(tables))
        return tables
    logger.warning("Removing incomplete cached DuckDB file: %s", db_path)
    os.remove(db_path)
    return None


def _load_hf_into_duckdb(
    dataset_id: str,
    subset: str | None,
    split_filter: str | None,
) -> tuple[str, list[str]]:
    """Discover metadata and load a HuggingFace dataset into DuckDB.

    Discovery (config resolution, split listing, size estimation) uses the
    HuggingFace datasets-server API to avoid DuckDB HTTP HEAD requests that
    trigger 429 rate limiting.  Only the final table/view creation uses DuckDB.

    Returns:
        A tuple of (db_path, table_names).
    """
    from mintq.config import mintq_config

    cache_dir = os.path.join(mintq_config.cache_dir, "hf")
    os.makedirs(cache_dir, exist_ok=True)

    # Try cache before making any API calls.  If subset is given we know the
    # config; otherwise guess "default" (the most common case).
    candidate_config = subset or "default"
    db_path = _db_path(cache_dir, dataset_id, candidate_config, split_filter)
    cached = _try_cache(db_path)
    if cached is not None:
        return db_path, cached

    # Cache miss — resolve config and discover splits via API.
    config = _resolve_config(dataset_id, subset)
    split_sizes = _discover_splits_and_size(dataset_id, config)

    if split_filter:
        if split_filter not in split_sizes:
            raise ValueError(
                f"Split '{split_filter}' not found. Available splits: {', '.join(sorted(split_sizes))}"
            )
        splits = [split_filter]
    else:
        splits = sorted(split_sizes)

    # Re-check cache if resolved config differs from the candidate.
    if config != candidate_config:
        db_path = _db_path(cache_dir, dataset_id, config, split_filter)
        cached = _try_cache(db_path)
        if cached is not None:
            return db_path, cached

    loaded_sizes = {s: split_sizes[s] for s in splits}
    loaded_total = sum(loaded_sizes.values())
    size_str = _format_size(loaded_total) if loaded_total > 0 else "unknown size"
    logger.info("Loading HF dataset '%s' (%s, %d splits)", dataset_id, size_str, len(splits))

    conn = _init_duckdb(db_path)
    try:
        table_names = _create_tables(conn, dataset_id, config, loaded_sizes)
        return db_path, table_names
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def load_hf_dataset(
    dataset_url: str,
    *,
    db_name: str | None = None,
    read_only: bool = True,
) -> SQLConnector:
    """Load a HuggingFace dataset into a DuckDB-backed SQLConnector.

    Small datasets are fully materialized.  Large datasets get a lazy view
    over all parquet files plus a materialized sample table.
    DuckDB files are cached in ``~/.mintq/cache/hf/`` across sessions.

    Args:
        dataset_url: A HuggingFace dataset URL.
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
    db_path, table_names = await loop.run_in_executor(
        None, _load_hf_into_duckdb, dataset_id, subset, split,
    )

    # Derive global_id from the DuckDB cache path so the schema cache key
    # is stable across sessions regardless of the user-chosen alias.
    global_id = f"hf+{os.path.splitext(os.path.basename(db_path))[0]}"

    # Fetch dataset description only on schema cache miss.
    from mintq.config import mintq_config

    schema_cache_path = os.path.join(mintq_config.cache_dir, "schemas", f"{global_id}.json")
    description: str | None = None
    if not os.path.exists(schema_cache_path):
        hf_description = await loop.run_in_executor(None, _fetch_hf_description, dataset_id)
        if hf_description:
            if len(hf_description) > 5000:
                from mintq.preprocessors.components.text_summarizer import TextSummarizer

                summarizer = TextSummarizer()
                hf_description = await summarizer.summarize(hf_description)
            description = (
                f"Source: HuggingFace dataset {dataset_url}\n\n"
                f"<readme>\n{hf_description}\n</readme>"
            )

    url = f"duckdb:///{db_path}"
    connector = await SQLConnector.from_url_async(
        global_id=global_id,
        url=url,
        db_name=db_name,
        read_only=read_only,
        enable_schema_caching=True,
        enable_query_caching=False,
        duckdb_init_sql=["LOAD httpfs"],
        description=description,
    )
    return connector
