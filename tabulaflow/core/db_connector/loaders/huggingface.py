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
import json
import logging
import os
import re
import sys
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

    from tabulaflow.core.db_connector.sql_conn import SQLConnector

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


async def _fetch_hf_description(dataset_id: str) -> str | None:
    """Fetch the full dataset README from HuggingFace Hub.

    Uses a direct HTTP GET against ``raw/main/README.md`` with a hard
    timeout, sharing the module-level :func:`_get_hf_client` connection
    pool.  The previous implementation went through
    ``huggingface_hub.hf_hub_download``, which has been observed to
    hang indefinitely on this code path (no top-level timeout, retries
    inside the local cache machinery).  ``dataset_info()`` is not an
    option — it truncates descriptions for large dataset cards.
    """
    try:
        client = _get_hf_client()
        url = f"https://huggingface.co/datasets/{dataset_id}/raw/main/README.md"
        r = await client.get(url, timeout=15, follow_redirects=True)
        if r.status_code != 200:
            return None
        # Strip YAML frontmatter.
        content = re.sub(r"^---\n.*?\n---\n", "", r.text, flags=re.DOTALL).strip()
        return content or None
    except Exception:
        return None


_hf_client: tuple[httpx.AsyncClient, asyncio.AbstractEventLoop] | None = None


def _get_hf_client() -> httpx.AsyncClient:
    """Return a cached AsyncClient, recreating if the running loop changed.

    ``httpx.AsyncClient`` is bound to the event loop that created it; this
    guards against tests or other code that runs multiple ``asyncio.run()``
    calls in the same process.
    """
    import httpx  # lazy — keep worker subprocess startup minimal

    global _hf_client
    loop = asyncio.get_running_loop()
    if _hf_client is None or _hf_client[1] is not loop:
        _hf_client = (httpx.AsyncClient(timeout=30, headers={"User-Agent": "tabulaflow"}), loop)
    return _hf_client[0]


async def _hf_api_get(endpoint: str, dataset_id: str, **params: str) -> dict[str, Any]:
    """Make a GET request to the HuggingFace datasets-server API.

    Uses a cached ``httpx.AsyncClient`` so subsequent calls reuse the TCP
    connection, and so cancellation propagates cleanly.
    """
    url = f"https://datasets-server.huggingface.co/{endpoint}"
    query = {"dataset": dataset_id, **params}
    resp = await _get_hf_client().get(url, params=query)
    if resp.status_code in (500, 501):
        try:
            detail = resp.json().get("error", "")
        except Exception:
            detail = ""
        msg = f"Dataset '{dataset_id}' is not indexed by the HuggingFace datasets server (HTTP {resp.status_code})."
        if detail:
            msg += f"\nServer response: {detail}"
        raise _DatasetServerUnavailableError(msg)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


async def _fetch_splits_from_api(dataset_id: str) -> list[dict[str, Any]]:
    """Fetch split entries from the HuggingFace datasets-server API.

    Returns:
        A list of dicts with keys ``config`` and ``split``.

    Raises:
        ValueError: If the dataset has no splits.
    """
    data = await _hf_api_get("splits", dataset_id)
    splits: list[dict[str, Any]] = data.get("splits", [])
    if not splits:
        raise _DatasetServerUnavailableError(
            f"No splits found for dataset '{dataset_id}'. The dataset may be gated, private, or not yet indexed."
        )
    return splits


async def _fetch_configs_from_api(dataset_id: str) -> list[str]:
    """Fetch available config names via the HuggingFace datasets-server API."""
    return sorted({s["config"] for s in await _fetch_splits_from_api(dataset_id)})


async def _fetch_parquet_urls(dataset_id: str, config: str, split: str) -> list[str]:
    """Fetch direct parquet file URLs for a specific config/split."""
    data = await _hf_api_get("parquet", dataset_id, config=config, split=split)
    return [f["url"] for f in data.get("parquet_files", []) if f.get("split") == split]


# ---------------------------------------------------------------------------
# DuckDB loading
# ---------------------------------------------------------------------------


async def _resolve_config(dataset_id: str, subset: str | None) -> str:
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
    configs = await _fetch_configs_from_api(dataset_id)

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


async def _discover_splits_and_size(dataset_id: str, config: str) -> dict[str, int]:
    """Discover splits and per-split sizes via the HuggingFace API.

    Returns:
        A dict mapping split name to parquet size in bytes.
    """
    data = await _hf_api_get("size", dataset_id)

    split_sizes: dict[str, int] = {}
    for entry in data.get("size", {}).get("splits", []):
        if entry.get("config") == config:
            split_sizes[entry["split"]] = int(entry.get("num_bytes_parquet_files", 0))

    if not split_sizes:
        raise _DatasetServerUnavailableError(f"No splits found for '{dataset_id}' config '{config}'.")
    return split_sizes


async def _build_hf_splits(
    dataset_id: str,
    config: str,
    split_sizes: dict[str, int],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Build the subprocess-worker split list for an HF dataset.

    Uses the HuggingFace datasets-server ``/parquet`` API to get direct
    download URLs, avoiding DuckDB ``hf://`` glob resolution which triggers
    HTTP HEAD requests that are easily rate-limited (429).

    Returns ``(splits, table_names)``.  ``table_names`` is the best-guess
    list of tables that should exist after loading (a sample split with
    ``optional=True`` may be silently dropped by the worker if its
    DESCRIBE or CREATE fails).
    """
    splits: list[dict[str, Any]] = []
    table_names: list[str] = []

    for split_name, size in split_sizes.items():
        urls = await _fetch_parquet_urls(dataset_id, config, split_name)
        if not urls:
            raise ValueError(f"No parquet files found for '{dataset_id}' config '{config}' split '{split_name}'.")

        base_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
        materialize = size > 0 and size < MATERIALIZE_THRESHOLD_BYTES
        if materialize:
            logger.info("Queueing TABLE '%s' from %d parquet files", base_name, len(urls))
            splits.append({"name": base_name, "kind": "table", "urls": urls})
            table_names.append(base_name)
        else:
            logger.info("Queueing VIEW '%s' from %d parquet files", base_name, len(urls))
            splits.append({"name": base_name, "kind": "view", "urls": urls})
            table_names.append(base_name)
            sample_name = f"{base_name}_sample"
            # 100 rows with BLOBs preserved — a small representative
            # preview (including media) rather than a BLOB-free
            # metadata scan. Bounds size for high-res datasets while
            # still letting users preview real images / audio / video
            # from the sample table.
            splits.append(
                {
                    "name": sample_name,
                    "kind": "table",
                    "urls": [urls[0]],
                    "limit": 100,
                    "optional": True,
                }
            )
            table_names.append(sample_name)

    return splits, table_names


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


async def _load_hf_via_datasets_lib(
    dataset_id: str,
    subset: str | None,
    split_filter: str | None,
    cache_dir: str,
) -> tuple[str, list[str]]:
    """Fallback loader using the ``datasets`` library for datasets not indexed
    by the HuggingFace datasets-server (e.g. those with custom loading scripts).

    Runs the entire flow — ``datasets.load_dataset()`` download, parquet
    export, DuckDB load — inside a subprocess.  Both the download and the
    parquet export are blocking and have no async cancellation API; the
    subprocess lets a Ctrl+C kill them cleanly via ``proc.terminate()``.

    Returns:
        A tuple of (db_path, table_names).  ``table_names`` is the
        best-guess list of tables created (the actual list is whatever
        ``ds.load_dataset`` produced, which we don't know up front;
        downstream consumers ignore it).
    """
    from tabulaflow.core.db_connector.loaders.runner import run_loader_subprocess

    logger.info(
        "Falling back to datasets library for '%s' (not available via datasets-server)",
        dataset_id,
    )

    config_label = subset or "default"
    db_file = _db_path(cache_dir, dataset_id, config_label, split_filter)

    try:
        await run_loader_subprocess(
            "tabulaflow.core.db_connector.loaders.huggingface",
            {
                "mode": "datasets_lib",
                "db_path": db_file,
                "dataset_id": dataset_id,
                "subset": subset,
                "split_filter": split_filter,
            },
        )
    except BaseException:
        # A killed subprocess can leave a partial DuckDB file at db_file
        # — _try_cache would later treat it as a valid cache hit if it
        # has any tables.  Remove it so the next attempt reloads cleanly.
        if os.path.exists(db_file):
            try:
                os.unlink(db_file)
            except OSError:
                pass
        raise

    return db_file, []


async def _load_hf_into_duckdb(
    dataset_id: str,
    subset: str | None,
    split_filter: str | None,
) -> tuple[str, list[str]]:
    """Discover metadata and load a HuggingFace dataset into DuckDB.

    Discovery (config resolution, split listing, size estimation) uses the
    HuggingFace datasets-server API to avoid DuckDB HTTP HEAD requests that
    trigger 429 rate limiting.  The actual DuckDB work runs in a subprocess
    so that cancellation terminates it cleanly.

    Falls back to the ``datasets`` library when the datasets-server API is
    unavailable (e.g. for datasets with custom loading scripts).

    Returns:
        A tuple of (db_path, table_names).
    """
    from tabulaflow.core.config import tabulaflow_config
    from tabulaflow.core.db_connector.loaders.runner import run_loader_subprocess

    cache_dir = os.path.join(tabulaflow_config.cache_dir, "hf")
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
        config = await _resolve_config(dataset_id, subset)
        split_sizes = await _discover_splits_and_size(dataset_id, config)
    except _DatasetServerUnavailableError:
        # datasets-server unavailable — fall back to datasets library.
        return await _load_hf_via_datasets_lib(dataset_id, subset, split_filter, cache_dir)

    if split_filter:
        if split_filter not in split_sizes:
            raise ValueError(f"Split '{split_filter}' not found. Available splits: {', '.join(sorted(split_sizes))}")
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

    payload_splits, table_names = await _build_hf_splits(dataset_id, config, loaded_sizes)
    try:
        await run_loader_subprocess(
            "tabulaflow.core.db_connector.loaders.huggingface",
            {"mode": "parquet_urls", "db_path": db_path, "splits": payload_splits},
        )
    except BaseException:
        # Partial state from a killed worker would make _try_cache flag the
        # file as complete; remove it so the next attempt reloads cleanly.
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except OSError:
                pass
        raise
    return db_path, table_names


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def load_hf_dataset(
    dataset_url: str,
    *,
    db_name: str | None = None,
    read_only: bool = True,
    summarize: Callable[[str], Awaitable[str]] | None = None,
) -> SQLConnector:
    """Load a HuggingFace dataset into a DuckDB-backed SQLConnector.

    Small datasets are fully materialized.  Large datasets get a lazy view
    over all parquet files plus a materialized sample table.
    DuckDB files are cached in ``~/.tabulaflow/cache/hf/`` across sessions.

    Args:
        dataset_url: A HuggingFace dataset URL.
        db_name: Display name for the database. Defaults to the dataset name.
        read_only: If True, block write statements.

    Returns:
        A :class:`SQLConnector` backed by a DuckDB database.
    """
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

    dataset_id, subset, split = parse_hf_dataset_url(dataset_url)

    if db_name is None:
        db_name = dataset_id.split("/")[-1]

    db_path, _ = await _load_hf_into_duckdb(dataset_id, subset, split)

    # Derive global_id from the DuckDB cache path so the schema cache key
    # is stable across sessions regardless of the user-chosen alias.
    global_id = f"hf+{os.path.splitext(os.path.basename(db_path))[0]}"

    # Fetch dataset description only on schema cache miss.
    from tabulaflow.core.config import tabulaflow_config

    schema_cache_path = os.path.join(tabulaflow_config.cache_dir, "schemas", f"{global_id}.json")
    description: str | None = None
    if not os.path.exists(schema_cache_path):
        hf_description = await _fetch_hf_description(dataset_id)
        if hf_description:
            if len(hf_description) > 5000 and summarize is not None:
                hf_description = await summarize(hf_description)
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


# ---------------------------------------------------------------------------
# Subprocess worker
# ---------------------------------------------------------------------------


def _build_split_columns(conn: Any, source: str, blob_strip: bool) -> str:
    """Return a SELECT-list that drops BLOB columns when ``blob_strip`` is
    set; otherwise just ``*``."""
    if not blob_strip:
        return "*"
    cols = conn.execute(f"DESCRIBE SELECT * FROM {source} LIMIT 0").fetchall()
    parts: list[str] = []
    for row in cols:
        name, dtype = row[0], row[1]
        quoted = f'"{name}"'
        if "BLOB" in dtype.upper():
            parts.append(f"'<binary: skipped>' AS {quoted}")
        else:
            parts.append(quoted)
    return ", ".join(parts) if parts else "*"


def _create_split(conn: Any, split: dict[str, Any]) -> None:
    """Realize one entry from the worker payload's ``splits`` list."""
    name = split["name"]
    kind = split["kind"]
    urls = split["urls"]
    blob_strip = bool(split.get("blob_strip", False))
    limit = split.get("limit")

    if not urls:
        raise ValueError(f"split '{name}' has no urls")
    url_list = ", ".join(f"'{u}'" for u in urls)
    source = f"read_parquet([{url_list}])"
    columns = _build_split_columns(conn, source, blob_strip)

    if kind == "table":
        sql = f'CREATE TABLE "{name}" AS SELECT {columns} FROM {source}'
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
    elif kind == "view":
        sql = f'CREATE VIEW "{name}" AS SELECT {columns} FROM {source}'
    else:
        raise ValueError(f"unknown split kind: {kind!r}")
    conn.execute(sql)


def _run_parquet_urls(payload: dict[str, Any]) -> None:
    """Worker handler for ``mode == "parquet_urls"``.

    Loads each split entry by issuing CREATE TABLE / CREATE VIEW against
    the parquet URLs already discovered in the parent.
    """
    import duckdb

    db_path: str = payload["db_path"]
    splits: list[dict[str, Any]] = payload["splits"]

    conn = duckdb.connect(db_path)
    try:
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")
        for split in splits:
            try:
                _create_split(conn, split)
            except Exception as exc:
                if split.get("optional"):
                    print(
                        f"WARN: optional split failed: {split.get('name', '?')}: {exc}",
                        file=sys.stderr,
                    )
                    try:
                        conn.execute(f'DROP TABLE IF EXISTS "{split["name"]}"')
                        conn.execute(f'DROP VIEW IF EXISTS "{split["name"]}"')
                    except Exception:
                        pass
                    continue
                raise
    finally:
        conn.close()


def _run_datasets_lib(payload: dict[str, Any]) -> None:
    """Worker handler for ``mode == "datasets_lib"`` — the fallback path
    for datasets the HuggingFace datasets-server doesn't index.

    Imports the heavy ``datasets`` library (only when this branch runs),
    downloads the dataset, exports each split to a temp parquet file,
    then materializes them into DuckDB with BLOB columns stripped.

    The whole flow runs inside the subprocess so a parent ``terminate()``
    cleanly kills any in-flight download or parquet write.
    """
    import tempfile

    import datasets as ds
    import duckdb

    db_path: str = payload["db_path"]
    dataset_id: str = payload["dataset_id"]
    subset: str | None = payload.get("subset")
    split_filter: str | None = payload.get("split_filter")

    kwargs: dict[str, Any] = {}
    if subset is not None:
        kwargs["name"] = subset
    if split_filter is not None:
        kwargs["split"] = split_filter

    loaded = ds.load_dataset(dataset_id, **kwargs)
    if isinstance(loaded, ds.DatasetDict):
        split_dict: dict[str, ds.Dataset] = dict(loaded)
    else:
        # Single split returned when split_filter is specified.
        split_name = split_filter or "data"
        split_dict = {split_name: loaded}

    with tempfile.TemporaryDirectory() as tmpdir:
        conn = duckdb.connect(db_path)
        try:
            for split_name, split_ds in sorted(split_dict.items()):
                base_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
                parquet_path = os.path.join(tmpdir, f"{base_name}.parquet")
                split_ds.to_parquet(parquet_path)
                _create_split(
                    conn,
                    {
                        "name": base_name,
                        "kind": "table",
                        "urls": [parquet_path],
                    },
                )
        finally:
            conn.close()


def _worker_main() -> int:
    """Subprocess entry point.

    Dispatches on ``payload["mode"]``:

    ``"parquet_urls"`` — fast path; loads splits the parent has already
    resolved to direct parquet URLs.  Imports only ``duckdb``.

    ``"datasets_lib"`` — fallback for datasets the HF datasets-server
    doesn't index.  Imports the (heavy) ``datasets`` library, downloads,
    exports parquet, and materializes into DuckDB — all inside this
    subprocess so a parent terminate kills it cleanly.
    """
    payload = json.loads(sys.stdin.read())
    mode = payload.get("mode", "parquet_urls")
    if mode == "parquet_urls":
        _run_parquet_urls(payload)
    elif mode == "datasets_lib":
        _run_datasets_lib(payload)
    else:
        raise ValueError(f"unknown worker mode: {mode!r}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_worker_main())
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
