"""Cached models.dev catalog for the interactive model picker."""

from __future__ import annotations

import asyncio
from calendar import monthrange
from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
from functools import cache
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_ai.providers import infer_provider_class

from tabulaflow import __version__
from tabulaflow.core._cache import DEFAULT_CACHE_DIR, cache_lock, read_cached_model, write_cached_model

MODEL_CATALOG_URL = "https://models.dev/api.json"
MODEL_CATALOG_CACHE_PATH = DEFAULT_CACHE_DIR / "model_catalog" / "models.dev.json"
MODEL_CATALOG_BUNDLED_PATH = Path(__file__).parent / "assets" / "model_catalog.json"
MODEL_CATALOG_MAX_AGE = timedelta(days=1)
MIN_MODEL_CONTEXT_TOKENS = 128_000
MODEL_RELEASE_MAX_AGE_MONTHS = 6
_CACHE_SCHEMA_VERSION = 5

_MODELS_DEV_PROVIDER_MAP: Mapping[str, str] = {
    "openai": "openai",
    "deepseek": "deepseek",
    "openrouter": "openrouter",
    "vercel": "vercel",
    "azure": "azure",
    "google": "google",
    "google-vertex": "google-cloud",
    "google-vertex-anthropic": "google-cloud",
    "amazon-bedrock": "bedrock",
    "groq": "groq",
    "anthropic": "anthropic",
    "mistral": "mistral",
    "cerebras": "cerebras",
    "cohere": "cohere",
    "crusoe": "crusoe",
    "xai": "xai",
    "moonshotai": "moonshotai",
    "fireworks-ai": "fireworks",
    "togetherai": "together",
    "huggingface": "huggingface",
    "github-copilot": "github-copilot",
    "nebius": "nebius",
    "ovhcloud": "ovhcloud",
    "alibaba": "alibaba",
    "snowflake-cortex": "snowflake",
    "zai": "zai",
    "ollama-cloud": "ollama",
}
_PYDANTIC_PROVIDER_PREFIXES = frozenset(_MODELS_DEV_PROVIDER_MAP.values())


class _CatalogEntry(BaseModel):
    id: str
    release_date: date


class _CatalogData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = _CACHE_SCHEMA_VERSION
    models: tuple[_CatalogEntry, ...]


class _BundledCatalog(_CatalogData):
    snapshot_date: date
    release_cutoff: date


class _CatalogCache(_CatalogData):
    checked_at: datetime
    etag: str | None = None


class _ModelLimit(BaseModel):
    context: int | None = None


class _ModelModalities(BaseModel):
    output: tuple[str, ...] | None = None


class _CatalogModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    release_date: date
    tool_call: bool = False
    status: str | None = None
    limit: _ModelLimit = Field(default_factory=_ModelLimit)
    modalities: _ModelModalities = Field(default_factory=_ModelModalities)


@cache
def _installed_provider_prefixes() -> frozenset[str]:
    prefixes: set[str] = set()
    for prefix in set(_MODELS_DEV_PROVIDER_MAP.values()):
        try:
            infer_provider_class(prefix)
        except (ImportError, ValueError):
            continue
        prefixes.add(prefix)
    return frozenset(prefixes)


def _release_cutoff(snapshot_date: date) -> date:
    month_index = snapshot_date.year * 12 + snapshot_date.month - 1 - MODEL_RELEASE_MAX_AGE_MONTHS
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return date(year, month, min(snapshot_date.day, monthrange(year, month)[1]))


def _parse_catalog(
    payload: object,
    *,
    release_cutoff: date,
    provider_prefixes: frozenset[str] | None = None,
) -> tuple[_CatalogEntry, ...]:
    if not isinstance(payload, dict):
        raise ValueError("models.dev returned a non-object catalog")

    supported = provider_prefixes if provider_prefixes is not None else _PYDANTIC_PROVIDER_PREFIXES
    models: dict[str, _CatalogEntry] = {}
    for catalog_provider, provider_prefix in _MODELS_DEV_PROVIDER_MAP.items():
        if provider_prefix not in supported or catalog_provider not in payload:
            continue
        provider = payload[catalog_provider]
        if not isinstance(provider, dict) or not isinstance(provider.get("models"), dict):
            continue
        for raw_model in provider["models"].values():
            try:
                model = _CatalogModel.model_validate(raw_model)
            except ValidationError:
                continue
            outputs = model.modalities.output
            if (
                model.tool_call
                and model.status not in {"deprecated", "alpha"}
                and model.limit.context is not None
                and model.limit.context >= MIN_MODEL_CONTEXT_TOKENS
                and outputs is not None
                and set(outputs) == {"text"}
                and model.release_date >= release_cutoff
            ):
                model_id = f"{provider_prefix}:{model.id}"
                existing = models.get(model_id)
                if existing is None or model.release_date > existing.release_date:
                    models[model_id] = _CatalogEntry(id=model_id, release_date=model.release_date)
    return tuple(sorted(models.values(), key=lambda model: model.id))


def _available_models(
    models: tuple[_CatalogEntry, ...],
    *,
    release_cutoff: date,
    provider_prefixes: frozenset[str] | None = None,
) -> tuple[str, ...]:
    installed = provider_prefixes if provider_prefixes is not None else _installed_provider_prefixes()
    return tuple(
        model.id
        for model in models
        if model.id.partition(":")[0] in installed and model.release_date >= release_cutoff
    )


async def _available_models_async(
    models: tuple[_CatalogEntry, ...],
    *,
    release_cutoff: date,
) -> tuple[str, ...]:
    return await asyncio.to_thread(_available_models, models, release_cutoff=release_cutoff)


def llm_model_catalog(
    *, current: str, recommended: tuple[str, ...], available: tuple[str, ...] = ()
) -> tuple[str, ...]:
    """Order available models after recommendations and the current selection."""
    current_provider = current.partition(":")[0]
    current_provider_models = tuple(
        model for model in available if model.partition(":")[0] == current_provider
    )
    other_models = tuple(model for model in available if model.partition(":")[0] != current_provider)
    return tuple(dict.fromkeys((*recommended, current, *current_provider_models, *other_models)))


async def _read_cache(path: Path) -> _CatalogCache | None:
    try:
        cache_entry = await read_cached_model(path, _CatalogCache)
    except (OSError, ValidationError):
        return None
    return cache_entry if cache_entry.schema_version == _CACHE_SCHEMA_VERSION else None


async def _read_bundled_catalog(path: Path) -> _BundledCatalog | None:
    try:
        catalog = await read_cached_model(path, _BundledCatalog)
    except (OSError, ValidationError):
        return None
    return catalog if catalog.schema_version == _CACHE_SCHEMA_VERSION else None


async def load_local_model_catalog(
    *,
    path: Path = MODEL_CATALOG_CACHE_PATH,
    bundled_path: Path = MODEL_CATALOG_BUNDLED_PATH,
) -> tuple[str, ...]:
    """Return the user cache or bundled catalog without accessing the network."""
    bundled = await _read_bundled_catalog(bundled_path)
    if bundled is None:
        return ()
    catalog: _CatalogData = await _read_cache(path) or bundled
    return await _available_models_async(catalog.models, release_cutoff=bundled.release_cutoff)


async def load_model_catalog(
    *,
    path: Path = MODEL_CATALOG_CACHE_PATH,
    bundled_path: Path = MODEL_CATALOG_BUNDLED_PATH,
    now: datetime | None = None,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, ...]:
    """Conditionally refresh the catalog, retaining local data on failure."""
    checked_at = now or datetime.now(timezone.utc)
    async with cache_lock(path):
        bundled = await _read_bundled_catalog(bundled_path)
        if bundled is None:
            return ()
        cached = await _read_cache(path)
        local: _CatalogData = cached or bundled
        if cached is not None and checked_at - cached.checked_at.astimezone(timezone.utc) < MODEL_CATALOG_MAX_AGE:
            return await _available_models_async(
                cached.models,
                release_cutoff=bundled.release_cutoff,
            )

        headers = {"Accept": "application/json", "User-Agent": f"tabulaflow/{__version__}"}
        if cached is not None and cached.etag is not None:
            headers["If-None-Match"] = cached.etag

        owns_client = client is None
        http_client = client or httpx.AsyncClient(follow_redirects=True, timeout=10)
        try:
            response = await http_client.get(MODEL_CATALOG_URL, headers=headers)
            if response.status_code == 304 and cached is not None:
                refreshed = cached.model_copy(update={"checked_at": checked_at})
            else:
                response.raise_for_status()
                models = await asyncio.to_thread(
                    lambda: _parse_catalog(
                        response.json(),
                        release_cutoff=bundled.release_cutoff,
                    )
                )
                refreshed = _CatalogCache(
                    checked_at=checked_at,
                    etag=response.headers.get("etag"),
                    models=models,
                )
            await write_cached_model(path, refreshed)
            return await _available_models_async(
                refreshed.models,
                release_cutoff=bundled.release_cutoff,
            )
        except (httpx.HTTPError, ValueError, ValidationError):
            return await _available_models_async(
                local.models,
                release_cutoff=bundled.release_cutoff,
            )
        finally:
            if owns_client:
                await http_client.aclose()


class ModelCatalog:
    """Process-local model catalog with local-first background refresh."""

    def __init__(
        self,
        *,
        path: Path = MODEL_CATALOG_CACHE_PATH,
        bundled_path: Path = MODEL_CATALOG_BUNDLED_PATH,
    ) -> None:
        self._path = path
        self._bundled_path = bundled_path
        self._models: tuple[str, ...] | None = None
        self._load_lock = asyncio.Lock()
        self._warm_lock = asyncio.Lock()
        self._refresh_attempted = False

    async def get(self) -> tuple[str, ...]:
        """Return local models without waiting for a network refresh."""
        async with self._load_lock:
            if self._models is None:
                self._models = await load_local_model_catalog(
                    path=self._path,
                    bundled_path=self._bundled_path,
                )
            return self._models

    async def warm(self) -> tuple[str, ...]:
        """Load local models, then refresh them at most once for this process."""
        await self.get()
        async with self._warm_lock:
            if not self._refresh_attempted:
                self._refresh_attempted = True
                self._models = await load_model_catalog(
                    path=self._path,
                    bundled_path=self._bundled_path,
                )
            assert self._models is not None
            return self._models
