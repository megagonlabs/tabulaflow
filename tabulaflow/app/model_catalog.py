"""Cached models.dev catalog for the interactive model picker."""

from __future__ import annotations

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
MODEL_CATALOG_MAX_AGE = timedelta(days=1)
MIN_MODEL_CONTEXT_TOKENS = 128_000
MODEL_RELEASE_MAX_AGE_YEARS = 1
_CACHE_SCHEMA_VERSION = 3

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


class _CatalogCache(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = _CACHE_SCHEMA_VERSION
    checked_at: datetime
    etag: str | None = None
    models: tuple[_CatalogEntry, ...]


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


def _release_cutoff(today: date) -> date:
    try:
        return today.replace(year=today.year - MODEL_RELEASE_MAX_AGE_YEARS)
    except ValueError:
        return today.replace(year=today.year - MODEL_RELEASE_MAX_AGE_YEARS, day=28)


def _parse_catalog(
    payload: object,
    *,
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
            ):
                model_id = f"{provider_prefix}:{model.id}"
                existing = models.get(model_id)
                if existing is None or model.release_date > existing.release_date:
                    models[model_id] = _CatalogEntry(id=model_id, release_date=model.release_date)
    return tuple(models.values())


def _available_models(
    models: tuple[_CatalogEntry, ...],
    *,
    today: date,
    provider_prefixes: frozenset[str] | None = None,
) -> tuple[str, ...]:
    installed = provider_prefixes if provider_prefixes is not None else _installed_provider_prefixes()
    cutoff = _release_cutoff(today)
    return tuple(
        model.id
        for model in models
        if model.id.partition(":")[0] in installed and model.release_date >= cutoff
    )


async def _read_cache(path: Path) -> _CatalogCache | None:
    try:
        cache_entry = await read_cached_model(path, _CatalogCache)
    except (OSError, ValidationError):
        return None
    return cache_entry if cache_entry.schema_version == _CACHE_SCHEMA_VERSION else None


async def load_model_catalog(
    *,
    path: Path = MODEL_CATALOG_CACHE_PATH,
    now: datetime | None = None,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, ...]:
    """Return the cached catalog, conditionally refreshing it once per day."""
    checked_at = now or datetime.now(timezone.utc)
    async with cache_lock(path):
        cached = await _read_cache(path)
        if cached is not None and checked_at - cached.checked_at.astimezone(timezone.utc) < MODEL_CATALOG_MAX_AGE:
            return _available_models(cached.models, today=checked_at.date())

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
                models = _parse_catalog(response.json())
                refreshed = _CatalogCache(
                    checked_at=checked_at,
                    etag=response.headers.get("etag"),
                    models=models,
                )
            await write_cached_model(path, refreshed)
            return _available_models(refreshed.models, today=checked_at.date())
        except (httpx.HTTPError, ValueError, ValidationError):
            return _available_models(cached.models, today=checked_at.date()) if cached is not None else ()
        finally:
            if owns_client:
                await http_client.aclose()
