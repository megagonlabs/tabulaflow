"""Safe shared filesystem operations for connector schema caches."""

from __future__ import annotations

import asyncio
import os
import re
import uuid
import weakref
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from tabulaflow.data.protocols import validate_global_id

_SCHEMA_CACHE_VERSION = "v1"
_ModelT = TypeVar("_ModelT", bound=BaseModel)
_locks: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[Path, asyncio.Lock]] = weakref.WeakKeyDictionary()


def schema_cache_path(cache_dir: Path, global_id: str, *, variant: str | None = None) -> Path:
    """Return a versioned, filename-safe schema cache path."""
    validate_global_id(global_id)
    if variant is not None and re.fullmatch(r"[a-zA-Z0-9._+-]+", variant) is None:
        raise ValueError(f"Invalid schema cache variant: {variant!r}")
    parts = [_SCHEMA_CACHE_VERSION]
    if variant is not None:
        parts.append(variant)
    parts.append(global_id)
    return cache_dir / "schemas" / f"{'@'.join(parts)}.json"


def schema_cache_lock(path: Path) -> asyncio.Lock:
    """Return the current event loop's lock for a schema cache path."""
    loop = asyncio.get_running_loop()
    locks = _locks.setdefault(loop, {})
    return locks.setdefault(path.resolve(), asyncio.Lock())


async def read_schema_cache(path: Path, model_type: type[_ModelT]) -> _ModelT:
    """Read and validate a schema cache without blocking the event loop."""

    def read() -> _ModelT:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    return await asyncio.to_thread(read)


async def write_schema_cache(path: Path, schema: BaseModel) -> None:
    """Atomically write a schema cache without blocking the event loop."""

    def write() -> None:
        content = schema.model_dump_json(indent=2)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    await asyncio.to_thread(write)
