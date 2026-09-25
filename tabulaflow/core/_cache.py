"""Safe, non-blocking filesystem mechanics for internal caches."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import uuid
import weakref
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from tabulaflow._paths import DEFAULT_HOME_DIR
from tabulaflow.core.serialization import json_ready

_ModelT = TypeVar("_ModelT", bound=BaseModel)
_locks: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[Path, asyncio.Lock]] = weakref.WeakKeyDictionary()
DEFAULT_CACHE_DIR = DEFAULT_HOME_DIR / "cache"


def cache_lock(path: Path) -> asyncio.Lock:
    """Return the current event loop's lock for a resolved cache path."""
    loop = asyncio.get_running_loop()
    locks = _locks.setdefault(loop, {})
    return locks.setdefault(path.resolve(), asyncio.Lock())


async def read_bytes(path: Path) -> bytes:
    return await asyncio.to_thread(path.read_bytes)


async def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Atomically write bytes without blocking the event loop."""

    def write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_bytes(content)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    await asyncio.to_thread(write)


async def remove_cached_file(path: Path) -> None:
    await asyncio.to_thread(path.unlink, missing_ok=True)


async def read_cached_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    content = await read_bytes(path)
    return await asyncio.to_thread(model_type.model_validate_json, content)


async def write_cached_model(path: Path, model: BaseModel) -> None:
    content = await asyncio.to_thread(lambda: model.model_dump_json(indent=2).encode())
    await atomic_write_bytes(path, content)


def stable_cache_key(payload: object) -> str:
    normalized = json_ready(payload)
    serialized = json.dumps(normalized, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(serialized.encode()).hexdigest()
