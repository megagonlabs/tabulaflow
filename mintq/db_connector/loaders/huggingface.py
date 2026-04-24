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
    from mintq.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)


class _DatasetServerUnavailableError(Exception):
    """The HuggingFace datasets-server cannot serve this dataset."""


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
            raise _DatasetServerUnavailableError(msg) from None
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
        raise _DatasetServerUnavailableError(
            f"No splits found for dataset '{dataset_id}'. The dataset may be gated, private, or not yet indexed."
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
            raise ValueError(f"Subset '{subset}' not found. Available subsets: {', '.join(configs)}")
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
        raise _DatasetServerUnavailableError(f"No splits found for '{dataset_id}' config '{config}'.")
    return split_sizes


def _dtype_has_blob(dtype: str) -> bool:
    """Return True if a DuckDB type contains BLOB (including nested structs/lists)."""
    return "BLOB" in dtype.upper()


async def _build_sample_columns_async(connector: SQLConnector, source: str) -> str:
    """Build a SELECT column list, replacing BLOB-containing columns with NULL."""
    result = await connector.run_query_async(f"DESCRIBE SELECT * FROM {source} LIMIT 0")
    if result.error is not None or result.df is None:
        return "*"
    parts: list[str] = []
    for row in result.df.itertuples(index=False):
        name = row[0]
        dtype = row[1]
        quoted = f'"{name}"'
        if _dtype_has_blob(dtype):
            parts.append(f"'<binary: skipped>' AS {quoted}")
            logger.info("Skipping BLOB column '%s' (%s) in sample", name, dtype)
        else:
            parts.append(quoted)
    return ", ".join(parts) if parts else "*"


async def _run_or_raise(connector: SQLConnector, sql: str, desc: str) -> None:
    """Run a statement and raise if it errored."""
    result = await connector.run_query_async(sql)
    if result.error is not None:
        raise RuntimeError(f"{desc} failed: {result.error.message}")


async def _create_tables_async(
    connector: SQLConnector,
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
        urls = await asyncio.to_thread(_fetch_parquet_urls, dataset_id, config, split_name)
        if not urls:
            raise ValueError(f"No parquet files found for '{dataset_id}' config '{config}' split '{split_name}'.")
        url_list = ", ".join(f"'{u}'" for u in urls)
        source = f"read_parquet([{url_list}])"

        base_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
        materialize = size > 0 and size < MATERIALIZE_THRESHOLD_BYTES
        if materialize:
            logger.info("Creating TABLE '%s' from %d parquet files", base_name, len(urls))
            await _run_or_raise(
                connector,
                f'CREATE TABLE "{base_name}" AS SELECT * FROM {source}',
                f"CREATE TABLE {base_name}",
            )
            table_names.append(base_name)
        else:
            # Full-data view over all parquet files.
            logger.info("Creating VIEW '%s' from %d parquet files", base_name, len(urls))
            await _run_or_raise(
                connector,
                f'CREATE VIEW "{base_name}" AS SELECT * FROM {source}',
                f"CREATE VIEW {base_name}",
            )
            table_names.append(base_name)

            # Materialized 1k sample from the first parquet file.
            # Null out BLOB columns (images, audio) to avoid downloading
            # huge binary data just for a preview.
            sample_name = f"{base_name}_sample"
            first_source = f"read_parquet('{urls[0]}')"
            columns = await _build_sample_columns_async(connector, first_source)
            sample_sql = f'CREATE TABLE "{sample_name}" AS SELECT {columns} FROM {first_source} LIMIT 1000'
            logger.info("Creating TABLE '%s' (at most 1k sample) from first parquet file", sample_name)
            sample_result = await connector.run_query_async(sample_sql)
            if sample_result.error is None:
                table_names.append(sample_name)
            else:
                logger.warning("Failed to create sample table '%s'; skipping", sample_name)
                await connector.run_query_async(f'DROP TABLE IF EXISTS "{sample_name}"')

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
            for r in conn.sql("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
        )
    if tables:
        logger.info("Using cached DuckDB file with tables: %s", ", ".join(tables))
        return tables
    logger.warning("Removing incomplete cached DuckDB file: %s", db_path)
    os.remove(db_path)
    return None


async def _open_loader_connector(db_path: str) -> SQLConnector:
    """Open a writable DuckDB SQLConnector for the loader phase, with
    httpfs installed.  Cancellation during the subsequent loading goes
    through ``ThrottledEngine.aclose`` like any other sync-driver query."""
    from mintq.db_connector.sql_conn import SQLConnector

    return await SQLConnector.from_url_async(
        global_id=f"hf-loader+{os.path.splitext(os.path.basename(db_path))[0]}",
        url=f"duckdb:///{db_path}",
        db_name=os.path.basename(db_path),
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
        duckdb_init_sql=["INSTALL httpfs; LOAD httpfs;"],
    )


async def _load_hf_via_datasets_lib(
    dataset_id: str,
    subset: str | None,
    split_filter: str | None,
    cache_dir: str,
) -> tuple[str, list[str]]:
    """Fallback loader using the ``datasets`` library for datasets not indexed
    by the HuggingFace datasets-server (e.g. those with custom loading scripts).

    Downloads via ``datasets.load_dataset()``, exports each split to parquet,
    and loads them into DuckDB.

    Returns:
        A tuple of (db_path, table_names).
    """
    import tempfile

    import datasets as ds

    logger.info(
        "Falling back to datasets library for '%s' (not available via datasets-server)",
        dataset_id,
    )

    kwargs: dict[str, Any] = {}
    if subset is not None:
        kwargs["name"] = subset
    if split_filter is not None:
        kwargs["split"] = split_filter

    # ``datasets.load_dataset`` is a blocking download; run it off the loop.
    # The thread itself remains uncancellable (no async API exists for this
    # library), but the DuckDB work below is cancellable via the SQLConnector.
    loaded = await asyncio.to_thread(ds.load_dataset, dataset_id, **kwargs)

    if isinstance(loaded, ds.DatasetDict):
        split_dict: dict[str, ds.Dataset] = dict(loaded)
    else:
        # Single split returned when split_filter is specified.
        split_name = split_filter or "data"
        split_dict = {split_name: loaded}

    config_label = subset or "default"
    db_file = _db_path(cache_dir, dataset_id, config_label, split_filter)

    connector = await _open_loader_connector(db_file)
    try:
        table_names: list[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for split_name, split_ds in sorted(split_dict.items()):
                base_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
                parquet_path = os.path.join(tmpdir, f"{base_name}.parquet")
                await asyncio.to_thread(split_ds.to_parquet, parquet_path)

                source = f"read_parquet('{parquet_path}')"
                columns = await _build_sample_columns_async(connector, source)
                logger.info("Creating TABLE '%s' from datasets library", base_name)
                await _run_or_raise(
                    connector,
                    f'CREATE TABLE "{base_name}" AS SELECT {columns} FROM {source}',
                    f"CREATE TABLE {base_name}",
                )
                table_names.append(base_name)
    finally:
        await connector.disconnect_async()

    return db_file, table_names


async def _load_hf_into_duckdb(
    dataset_id: str,
    subset: str | None,
    split_filter: str | None,
) -> tuple[str, list[str]]:
    """Discover metadata and load a HuggingFace dataset into DuckDB.

    Discovery (config resolution, split listing, size estimation) uses the
    HuggingFace datasets-server API to avoid DuckDB HTTP HEAD requests that
    trigger 429 rate limiting.  Only the final table/view creation uses DuckDB.

    Falls back to the ``datasets`` library when the datasets-server API is
    unavailable (e.g. for datasets with custom loading scripts).

    Returns:
        A tuple of (db_path, table_names).
    """
    from mintq.config import mintq_config

    cache_dir = os.path.join(mintq_config.cache_dir, "hf")
    os.makedirs(cache_dir, exist_ok=True)

    # Try cache before making any API calls.  If subset is given we know
    # the config; otherwise guess "default" (the most common case).
    candidate_config = subset or "default"
    db_path = _db_path(cache_dir, dataset_id, candidate_config, split_filter)
    cached = await asyncio.to_thread(_try_cache, db_path)
    if cached is not None:
        return db_path, cached

    # Cache miss — resolve config and discover splits via API.
    try:
        config = await asyncio.to_thread(_resolve_config, dataset_id, subset)
        split_sizes = await asyncio.to_thread(_discover_splits_and_size, dataset_id, config)
    except _DatasetServerUnavailableError:
        # datasets-server unavailable — fall back to datasets library.
        return await _load_hf_via_datasets_lib(dataset_id, subset, split_filter, cache_dir)

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
        cached = await asyncio.to_thread(_try_cache, db_path)
        if cached is not None:
            return db_path, cached

    loaded_sizes = {s: split_sizes[s] for s in splits}
    loaded_total = sum(loaded_sizes.values())
    size_str = _format_size(loaded_total) if loaded_total > 0 else "unknown size"
    logger.info("Loading HF dataset '%s' (%s, %d splits)", dataset_id, size_str, len(splits))

    connector = await _open_loader_connector(db_path)
    try:
        table_names = await _create_tables_async(connector, dataset_id, config, loaded_sizes)
        return db_path, table_names
    finally:
        await connector.disconnect_async()


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

    db_path, _ = await _load_hf_into_duckdb(dataset_id, subset, split)

    # Derive global_id from the DuckDB cache path so the schema cache key
    # is stable across sessions regardless of the user-chosen alias.
    global_id = f"hf+{os.path.splitext(os.path.basename(db_path))[0]}"

    # Fetch dataset description only on schema cache miss.
    from mintq.config import mintq_config

    schema_cache_path = os.path.join(mintq_config.cache_dir, "schemas", f"{global_id}.json")
    description: str | None = None
    if not os.path.exists(schema_cache_path):
        hf_description = await asyncio.to_thread(_fetch_hf_description, dataset_id)
        if hf_description:
            if len(hf_description) > 5000:
                from mintq.preprocessors.components.text_summarizer import TextSummarizer

                summarizer = TextSummarizer()
                hf_description = await summarizer.summarize(hf_description)
            description = f"Source: HuggingFace dataset {dataset_url}\n\n<readme>\n{hf_description}\n</readme>"

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
