"""Immutable configuration for agent runtimes and modules."""

from pathlib import Path
from typing import Literal

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CACHE_DIR = Path.home() / ".tabulaflow" / "cache"


class AgentRuntimeConfig(BaseSettings):
    """Operational policy shared by the process-wide agent runtime."""

    model_config = SettingsConfigDict(
        env_prefix="TABULAFLOW_",
        frozen=True,
        extra="forbid",
        env_parse_none_str="none",
    )

    cache_dir: Path = DEFAULT_CACHE_DIR
    preprocessor_cache_mode: Literal["off", "read_write", "refresh", "cache_only"] = "read_write"
    max_llm_concurrency: PositiveInt | None = 64
    max_llm_requests_per_minute: PositiveInt | None = 600
    max_embedding_concurrency: PositiveInt | None = 16
    max_embedding_requests_per_minute: PositiveInt | None = 150
    browser_max_tabs: PositiveInt | None = 20
    browser_headless: bool = True


__all__ = ["AgentRuntimeConfig"]
