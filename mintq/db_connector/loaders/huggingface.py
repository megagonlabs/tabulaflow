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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

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
        _hf_client = (httpx.AsyncClient(timeout=30, headers={"User-Agent": "mintq"}), loop)
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


async def _build_hf_operations(
    dataset_id: str,
    config: str,
    split_sizes: dict[str, int],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Build the subprocess-worker operation list for an HF dataset.

    Uses the HuggingFace datasets-server ``/parquet`` API to get direct
    download URLs, avoiding DuckDB ``hf://`` glob resolution which triggers
    HTTP HEAD requests that are easily rate-limited (429).

    Returns ``(operations, table_names)``.  ``table_names`` is the
    best-guess list of tables that should exist after loading (a sample
    table with ``allow_fail=True`` may be silently dropped by the worker
    if DESCRIBE or CREATE fails).
    """
    operations: list[dict[str, Any]] = [
        {"type": "exec", "sql": "INSTALL httpfs; LOAD httpfs;"},
    ]
    table_names: list[str] = []

    for split_name, size in split_sizes.items():
        urls = await _fetch_parquet_urls(dataset_id, config, split_name)
        if not urls:
            raise ValueError(f"No parquet files found for '{dataset_id}' config '{config}' split '{split_name}'.")
        url_list = ", ".join(f"'{u}'" for u in urls)
        source = f"read_parquet([{url_list}])"

        base_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
        materialize = size > 0 and size < MATERIALIZE_THRESHOLD_BYTES
        if materialize:
            logger.info("Queueing TABLE '%s' from %d parquet files", base_name, len(urls))
            operations.append(
                {"type": "exec", "sql": f'CREATE TABLE "{base_name}" AS SELECT * FROM {source}'}
            )
            table_names.append(base_name)
        else:
            logger.info("Queueing VIEW '%s' from %d parquet files", base_name, len(urls))
            operations.append(
                {"type": "exec", "sql": f'CREATE VIEW "{base_name}" AS SELECT * FROM {source}'}
            )
            table_names.append(base_name)
            sample_name = f"{base_name}_sample"
            operations.append(
                {
                    "type": "create_sample",
                    "target": sample_name,
                    "source": f"read_parquet('{urls[0]}')",
                    "limit": 1000,
                    "allow_fail": True,
                }
            )
            table_names.append(sample_name)

    return operations, table_names


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

    Downloads via ``datasets.load_dataset()``, exports each split to parquet,
    and loads them into DuckDB via a subprocess.

    Returns:
        A tuple of (db_path, table_names).
    """
    import tempfile

    import datasets as ds

    from mintq.db_connector.loaders.runner import run_loader_subprocess

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
    # library), but the DuckDB work below runs in a subprocess that we can
    # kill cleanly on cancellation.
    loaded = await asyncio.to_thread(ds.load_dataset, dataset_id, **kwargs)

    if isinstance(loaded, ds.DatasetDict):
        split_dict: dict[str, ds.Dataset] = dict(loaded)
    else:
        # Single split returned when split_filter is specified.
        split_name = split_filter or "data"
        split_dict = {split_name: loaded}

    config_label = subset or "default"
    db_file = _db_path(cache_dir, dataset_id, config_label, split_filter)

    with tempfile.TemporaryDirectory() as tmpdir:
        operations: list[dict[str, Any]] = []
        table_names: list[str] = []
        for split_name, split_ds in sorted(split_dict.items()):
            base_name = re.sub(r"[^a-zA-Z0-9_]", "_", split_name).lower()
            parquet_path = os.path.join(tmpdir, f"{base_name}.parquet")
            await asyncio.to_thread(split_ds.to_parquet, parquet_path)
            logger.info("Queueing TABLE '%s' from datasets library", base_name)
            # Use create_sample so BLOB columns (images, audio) are
            # stripped from the table preview sent to the LLM.
            operations.append(
                {
                    "type": "create_sample",
                    "target": base_name,
                    "source": f"read_parquet('{parquet_path}')",
                    # No limit → materialize full split (use a huge cap).
                    "limit": 2**63 - 1,
                }
            )
            table_names.append(base_name)
        await run_loader_subprocess(
            "mintq.db_connector.loaders.huggingface",
            {"db_path": db_file, "operations": operations},
        )

    return db_file, table_names


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
    from mintq.config import mintq_config
    from mintq.db_connector.loaders.runner import run_loader_subprocess

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
        config = await _resolve_config(dataset_id, subset)
        split_sizes = await _discover_splits_and_size(dataset_id, config)
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

    operations, table_names = await _build_hf_operations(dataset_id, config, loaded_sizes)
    try:
        await run_loader_subprocess(
            "mintq.db_connector.loaders.huggingface",
            {"db_path": db_path, "operations": operations},
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


# ---------------------------------------------------------------------------
# Subprocess worker
# ---------------------------------------------------------------------------


def _dtype_has_blob(dtype: str) -> bool:
    return "BLOB" in dtype.upper()


def _build_sample_create_sql(conn: Any, target: str, source: str, limit: int) -> str:
    """CREATE TABLE <target> from <source> LIMIT <limit>, replacing BLOB
    columns with a placeholder literal so images/audio aren't materialized
    into the sample preview."""
    cols = conn.execute(f"DESCRIBE SELECT * FROM {source} LIMIT 0").fetchall()
    parts: list[str] = []
    for row in cols:
        name, dtype = row[0], row[1]
        quoted = f'"{name}"'
        if _dtype_has_blob(dtype):
            parts.append(f"'<binary: skipped>' AS {quoted}")
        else:
            parts.append(quoted)
    columns = ", ".join(parts) if parts else "*"
    return f'CREATE TABLE "{target}" AS SELECT {columns} FROM {source} LIMIT {limit}'


def _worker_main() -> int:
    """Subprocess entry point.

    Payload schema::

        {
            "db_path": str,
            "operations": [
                {"type": "exec", "sql": str, "allow_fail": bool?},
                {"type": "create_sample", "target": str, "source": str,
                 "limit": int?, "allow_fail": bool?},
                ...
            ]
        }
    """
    import duckdb  # deferred — only the worker needs this

    payload = json.loads(sys.stdin.read())
    db_path: str = payload["db_path"]
    operations: list[dict[str, Any]] = payload["operations"]

    conn = duckdb.connect(db_path)
    try:
        for op in operations:
            op_type = op["type"]
            try:
                if op_type == "exec":
                    conn.execute(op["sql"])
                elif op_type == "create_sample":
                    sql = _build_sample_create_sql(
                        conn, op["target"], op["source"], op.get("limit", 1000)
                    )
                    conn.execute(sql)
                else:
                    raise ValueError(f"unknown operation type: {op_type}")
            except Exception as exc:
                if op.get("allow_fail"):
                    target = op.get("target") or op.get("sql", "")[:80]
                    print(
                        f"WARN: operation failed (allow_fail): {target}: {exc}",
                        file=sys.stderr,
                    )
                    if "target" in op:
                        try:
                            conn.execute(f'DROP TABLE IF EXISTS "{op["target"]}"')
                        except Exception:
                            pass
                    continue
                raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_worker_main())
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
