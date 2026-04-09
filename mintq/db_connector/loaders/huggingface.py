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
from typing import TYPE_CHECKING

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


def _fetch_configs_from_api(dataset_id: str) -> list[str]:
    """Fetch available config names via the HuggingFace datasets-server API.

    This is the only function that calls the HF API — used as a fallback
    when DuckDB cannot determine the config name.
    """
    import json
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    url = f"https://datasets-server.huggingface.co/splits?{urlencode({'dataset': dataset_id})}"
    req = Request(url, headers={"User-Agent": "mintq"})
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    splits = data.get("splits", [])
    if not splits:
        raise ValueError(
            f"No splits found for dataset '{dataset_id}'. "
            "The dataset may be gated, private, or not yet indexed."
        )
    return sorted({s["config"] for s in splits})


def get_hf_dataset_info(dataset_url: str) -> tuple[int | None, bool]:
    """Return (total_parquet_size_bytes, False) for a HuggingFace dataset.

    The second element is always False since remote parquet loading does not
    use a local cache.
    """
    import duckdb as _duckdb

    dataset_id, subset, _split = parse_hf_dataset_url(dataset_url)
    config = subset or "default"
    try:
        conn = _duckdb.connect()
        conn.execute("INSTALL httpfs; LOAD httpfs;")
        glob_pat = _hf_parquet_glob(dataset_id, config)
        row = conn.sql(
            f"SELECT SUM(file_size_bytes) FROM parquet_file_metadata('{glob_pat}')"
        ).fetchone()
        conn.close()
        total = row[0] if row and row[0] else None
        return total, False
    except Exception:
        return None, False


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


def _resolve_config(
    conn: duckdb.DuckDBPyConnection, dataset_id: str, subset: str | None
) -> str:
    """Resolve which config to use, probing via DuckDB first.

    Args:
        conn: An initialised DuckDB connection with httpfs loaded.
        dataset_id: HuggingFace dataset identifier.
        subset: User-specified config, or None.

    Returns:
        The config name to use.

    Raises:
        ValueError: If the config doesn't exist or multiple configs exist
            and none was specified.
    """
    if subset is not None:
        # User specified a config — verify it exists with a fast probe.
        probe = f"hf://datasets/{dataset_id}@~parquet/{subset}/train/0000.parquet"
        try:
            conn.sql(f"SELECT 1 FROM '{probe}' LIMIT 1").fetchone()
        except Exception:
            # Probe failed — could be a different split name or bad config.
            # Try glob to be sure.
            glob_pat = _hf_parquet_glob(dataset_id, subset)
            try:
                files = conn.sql(f"SELECT file FROM glob('{glob_pat}')").fetchall()
                if not files:
                    raise ValueError(f"No parquet files found for config '{subset}'.")  # noqa: TRY301
            except Exception:
                configs = _fetch_configs_from_api(dataset_id)
                if subset not in configs:
                    raise ValueError(
                        f"Subset '{subset}' not found. Available subsets: {', '.join(configs)}"
                    ) from None
                raise
        return subset

    # No subset specified — try "default" with a fast probe.
    probe = f"hf://datasets/{dataset_id}@~parquet/default/train/0000.parquet"
    try:
        conn.sql(f"SELECT 1 FROM '{probe}' LIMIT 1").fetchone()
        return "default"
    except Exception:
        pass

    # "default" doesn't exist — check if there's a different single config
    # or multiple configs. We must use the API here because globbing all
    # configs is too slow for large datasets.
    configs = _fetch_configs_from_api(dataset_id)
    if len(configs) == 1:
        return configs[0]

    listing = ", ".join(configs[:20])
    if len(configs) > 20:
        listing += f", ... ({len(configs)} total)"
    raise ValueError(
        f"Dataset '{dataset_id}' has {len(configs)} subsets: {listing}\n"
        f"Specify one via: https://huggingface.co/datasets/{dataset_id}/viewer/<subset>"
    )


def _discover_splits_and_size(
    conn: duckdb.DuckDBPyConnection, dataset_id: str, config: str
) -> tuple[list[str], int]:
    """Discover splits and total size in a single query via parquet_file_metadata.

    Returns:
        A tuple of (sorted split names, total parquet size in bytes).
    """
    glob_pat = _hf_parquet_glob(dataset_id, config)
    rows = conn.sql(
        f"SELECT "
        f"  regexp_extract(file_name, '.*@~parquet/[^/]+/([^/]+)/', 1) AS split, "
        f"  SUM(file_size_bytes) AS total_bytes "
        f"FROM parquet_file_metadata('{glob_pat}') "
        f"GROUP BY split"
    ).fetchall()
    if not rows:
        raise ValueError(f"No parquet files found for '{dataset_id}' config '{config}'.")
    splits = sorted(r[0] for r in rows if r[0])
    total_size = sum(int(r[1]) for r in rows if r[1])
    return splits, total_size


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

    All discovery (config resolution, split listing, size estimation) is done
    via DuckDB's native ``hf://`` protocol.  The HF datasets-server API is
    only used as a fallback for config discovery when ``default`` doesn't exist.

    Returns:
        A tuple of (table_names, materialized).
    """
    conn = _init_duckdb(db_path)
    try:
        config = _resolve_config(conn, dataset_id, subset)
        splits, total_size = _discover_splits_and_size(conn, dataset_id, config)

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
