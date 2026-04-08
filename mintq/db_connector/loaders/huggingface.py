"""HuggingFace dataset loader that produces SQLConnector instances."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile

logger = logging.getLogger(__name__)

_HF_DATASET_RE = re.compile(
    r"^https?://huggingface\.co/datasets/"
    r"(?P<owner>[^/]+)/(?P<dataset>[^/]+)"
    r"(?:/viewer/(?P<subset>[^/]+)(?:/(?P<split>[^/]+))?)?"
)


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


def _load_hf_to_parquet(
    dataset_id: str,
    subset: str | None,
    split: str | None,
    output_dir: str,
) -> list[str]:
    """Download a HuggingFace dataset and save splits as parquet files.

    Returns a list of parquet file paths.
    """
    from datasets import get_dataset_config_names, load_dataset

    # If no subset specified, check if the dataset has multiple configs.
    if subset is None:
        try:
            configs = get_dataset_config_names(dataset_id)
        except Exception:
            configs = []
        if len(configs) > 1:
            listing = ", ".join(configs[:20])
            if len(configs) > 20:
                listing += f", ... ({len(configs)} total)"
            raise ValueError(
                f"Dataset '{dataset_id}' has multiple subsets: {listing}\n"
                f"Specify one via: https://huggingface.co/datasets/{dataset_id}/viewer/<subset>"
            )

    kwargs: dict[str, object] = {}
    if subset is not None:
        kwargs["name"] = subset
    if split is not None:
        kwargs["split"] = split

    ds = load_dataset(dataset_id, **kwargs)  # type: ignore[arg-type]

    paths: list[str] = []

    # load_dataset returns a Dataset (single split) or DatasetDict (multiple splits)
    from datasets import Dataset, DatasetDict

    if isinstance(ds, Dataset):
        name = split or "data"
        path = os.path.join(output_dir, f"{name}.parquet")
        ds.to_parquet(path)
        paths.append(path)
    elif isinstance(ds, DatasetDict):
        for split_name, split_ds in ds.items():
            path = os.path.join(output_dir, f"{split_name}.parquet")
            split_ds.to_parquet(path)
            paths.append(path)
    else:
        raise TypeError(f"Unexpected dataset type: {type(ds)}")

    return paths


async def load_hf_dataset(
    dataset_url: str,
    *,
    global_id: str,
    db_name: str | None = None,
    data_dir: str | None = None,
    read_only: bool = True,
) -> "SQLConnector":
    """Load a HuggingFace dataset into a DuckDB-backed SQLConnector.

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

    tmp_dir = tempfile.mkdtemp(prefix="mintq_hf_")
    try:
        loop = asyncio.get_running_loop()
        parquet_paths = await loop.run_in_executor(
            None, _load_hf_to_parquet, dataset_id, subset, split, tmp_dir,
        )

        connector = await SQLConnector.from_files_async(
            global_id=global_id,
            file_paths=parquet_paths,
            db_name=db_name,
            data_dir=data_dir,
            read_only=read_only,
            enable_schema_caching=False,
            enable_query_caching=False,
        )
    finally:
        # Clean up temp parquet files; DuckDB has its own copy.
        for f in os.listdir(tmp_dir):
            try:
                os.unlink(os.path.join(tmp_dir, f))
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    return connector
