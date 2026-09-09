"""Immutable configuration for agent runtime capabilities."""

from pathlib import Path
from typing import Literal, TypeAlias

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

from tabulaflow.core._cache import DEFAULT_CACHE_DIR

AgentCacheMode: TypeAlias = Literal["off", "read_write", "refresh", "cache_only"]


class AgentRuntimeConfig(BaseSettings):
    """Immutable process-wide policy for shared agent resources.

    Explicit values override ``TABULAFLOW_*`` environment variables, which
    override defaults. Optional limits use ``None`` for unlimited capacity.

    Attributes:
        cache_dir: Root for persistent preprocessing caches.
        preprocessing_cache_mode: Read/write policy for derived agent inputs.
        max_llm_concurrency: Maximum simultaneous model requests.
        max_llm_requests_per_minute: Process-wide model request rate.
        max_embedding_concurrency: Maximum simultaneous embedding requests.
        max_embedding_requests_per_minute: Process-wide embedding request rate.
        browser_max_tabs: Process-wide open-page limit.
        browser_headless: Whether the shared Chromium process is headless.
    """

    model_config = SettingsConfigDict(
        env_prefix="TABULAFLOW_",
        frozen=True,
        extra="forbid",
        env_parse_none_str="none",
    )

    cache_dir: Path = DEFAULT_CACHE_DIR
    preprocessing_cache_mode: AgentCacheMode = "off"
    max_llm_concurrency: PositiveInt | None = 64
    max_llm_requests_per_minute: PositiveInt | None = 600
    max_embedding_concurrency: PositiveInt | None = 16
    max_embedding_requests_per_minute: PositiveInt | None = 150
    browser_max_tabs: PositiveInt | None = 20
    browser_headless: bool = True


__all__ = ["AgentRuntimeConfig"]
