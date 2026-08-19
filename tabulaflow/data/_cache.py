"""Safe filesystem mechanics and keys for data-layer model caches."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import uuid
import weakref
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from tabulaflow.core.serialization import json_ready
from tabulaflow.data.protocols import validate_global_id

_SCHEMA_CACHE_VERSION = "v1"
_QUERY_CACHE_VERSION = "v1"
_ModelT = TypeVar("_ModelT", bound=BaseModel)
_locks: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[Path, asyncio.Lock]] = weakref.WeakKeyDictionary()


def cache_lock(path: Path) -> asyncio.Lock:
    """Return the current event loop's lock for a cache path."""
    loop = asyncio.get_running_loop()
    locks = _locks.setdefault(loop, {})
    return locks.setdefault(path.resolve(), asyncio.Lock())


async def read_cached_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    """Read and validate a cached model without blocking the event loop."""

    def read() -> _ModelT:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    return await asyncio.to_thread(read)


async def remove_cached_file(path: Path) -> None:
    """Remove a cached file without blocking the event loop."""
    await asyncio.to_thread(path.unlink, missing_ok=True)


async def write_cached_model(path: Path, model: BaseModel) -> None:
    """Atomically write a cached model without blocking the event loop."""

    def write() -> None:
        content = model.model_dump_json(indent=2)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    await asyncio.to_thread(write)


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
