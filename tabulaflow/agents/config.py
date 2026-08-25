"""Immutable configuration for agent runtime capabilities."""

from pathlib import Path
from typing import Literal, TypeAlias

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

from tabulaflow.core._cache import DEFAULT_CACHE_DIR

AgentCacheMode: TypeAlias = Literal["off", "read_write", "refresh", "cache_only"]


class AgentRuntimeConfig(BaseSettings):
    """Immutable process-wide policy for agent caches, provider limits, and the shared browser runtime."""

    model_config = SettingsConfigDict(
        env_prefix="TABULAFLOW_",
        frozen=True,
        extra="forbid",
        env_parse_none_str="none",
    )

    cache_dir: Path = DEFAULT_CACHE_DIR
    preprocessing_cache_mode: AgentCacheMode = "read_write"
    max_llm_concurrency: PositiveInt | None = 64
    max_llm_requests_per_minute: PositiveInt | None = 600
    max_embedding_concurrency: PositiveInt | None = 16
    max_embedding_requests_per_minute: PositiveInt | None = 150
    browser_max_tabs: PositiveInt | None = 20
    browser_headless: bool = True


__all__ = ["AgentRuntimeConfig"]
