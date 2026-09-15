"""Safe filesystem mechanics and keys for data-layer model caches."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tabulaflow.core._cache import (
    cache_lock as cache_lock,
    read_cached_model as read_cached_model,
    remove_cached_file as remove_cached_file,
    write_cached_model as write_cached_model,
)
from tabulaflow.core.serialization import json_ready
from tabulaflow.data.protocols import validate_global_id

_SCHEMA_CACHE_VERSION = "v4"
_QUERY_CACHE_VERSION = "v2"


def schema_cache_path(cache_dir: Path, global_id: str, *, variant: str | None = None) -> Path:
    """Return the versioned schema cache path for a connector."""
    validate_global_id(global_id)
    if variant is not None and re.fullmatch(r"[a-zA-Z0-9._+-]+", variant) is None:
        raise ValueError(f"Invalid schema cache variant: {variant!r}")
    parts = [_SCHEMA_CACHE_VERSION]
    if variant is not None:
        parts.append(variant)
    parts.append(global_id)
    return cache_dir / "schemas" / f"{'@'.join(parts)}.json"


def query_cache_key(
    query: str,
    parameters: Sequence[Any] | Mapping[str, Any],
    timeout: int | None,
    max_rows: int | None,
) -> str:
    """Return a deterministic cache key for a SQL query execution."""
    normalized_parameters: object
    if isinstance(parameters, Mapping):
        normalized_parameters = dict(sorted(parameters.items()))
    else:
        normalized_parameters = list(parameters)
    payload = json_ready(
        {
            "query": query.strip(),
            "parameters": normalized_parameters,
            "timeout": timeout,
            "max_rows": max_rows,
        }
    )
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


def query_cache_path(cache_dir: Path, global_id: str, key: str) -> Path:
    """Return the versioned query-result cache path for a connector and key."""
    validate_global_id(global_id)
    if re.fullmatch(r"[0-9a-f]{64}", key) is None:
        raise ValueError(f"Invalid query cache key: {key!r}")
    return cache_dir / "query_results" / f"{_QUERY_CACHE_VERSION}@{global_id}@{key}.json"
