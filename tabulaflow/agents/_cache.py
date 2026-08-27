"""Cache-mode orchestration for expensive agent capabilities."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from tabulaflow.agents.config import AgentCacheMode
from tabulaflow.core._cache import cache_lock, read_cached_model, remove_cached_file, write_cached_model

_T = TypeVar("_T")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class InvalidCacheEntry(ValueError):
    """A cache file exists but cannot be decoded as its expected value."""


async def load_or_compute(
    *,
    path: Path,
    mode: AgentCacheMode,
    load: Callable[[Path], Awaitable[_T]],
    compute: Callable[[], Awaitable[_T]],
    store: Callable[[Path, _T], Awaitable[None]],
) -> _T:
    """Resolve one cache entry according to the configured cache mode."""
    if mode == "off":
        return await compute()

    async with cache_lock(path):
        if mode in ("read_write", "cache_only") and path.exists():
            try:
                return await load(path)
            except InvalidCacheEntry:
                if mode == "cache_only":
                    raise
                await remove_cached_file(path)

        if mode == "cache_only":
            raise FileNotFoundError(f"Cache entry not found: {path}")

        value = await compute()
        if mode in ("read_write", "refresh"):
            await store(path, value)
        return value


async def load_or_compute_model(
    *,
    path: Path,
    mode: AgentCacheMode,
    model_type: type[_ModelT],
    compute: Callable[[], Awaitable[_ModelT]],
) -> _ModelT:
    """Load or compute a Pydantic model under the configured cache policy."""

    async def load(cache_path: Path) -> _ModelT:
        try:
            return await read_cached_model(cache_path, model_type)
        except ValidationError as exc:
            raise InvalidCacheEntry(f"Invalid cache entry: {cache_path}") from exc

    return await load_or_compute(
        path=path,
        mode=mode,
        load=load,
        compute=compute,
        store=write_cached_model,
    )
