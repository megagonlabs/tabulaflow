import os
from typing import Any, Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ColumnStatsMode = Literal["always_skip", "always_precise", "sample_for_large_tables", "skip_for_large_tables"]
QueryCacheMode = Literal["all", "successful_only"]

_POSITIVE_INT_OR_NONE_FIELDS = (
    "df_max_rows",
    "max_llm_concurrency",
    "max_llm_requests_per_minute",
    "max_embedding_concurrency",
    "max_embedding_requests_per_minute",
    "query_timeout",
    "max_browser_tabs",
)


class _MintqSettings(BaseSettings):
    """Reads ``MINTQ_*`` environment variables with typed defaults."""

    model_config = SettingsConfigDict(env_prefix="MINTQ_")

    cache_dir: str = os.path.join(os.path.expanduser("~"), ".mintq", "cache")
    schema_cache_enabled: bool = True
    schema_cache_overwrite: bool = False
    schema_cache_required: bool = False
    preprocessor_cache_enabled: bool = True
    preprocessor_cache_overwrite: bool = False
    preprocessor_cache_required: bool = False
    query_cache_enabled: bool = True
    query_cache_overwrite: bool = False
    query_cache_mode: QueryCacheMode = "successful_only"
    instrument_enabled: bool = True
    instrument_prefix: str = "exp"
    disable_bigquery_tracing: bool = True
    df_max_rows: int | None = 100000
    max_llm_concurrency: int | None = 64
    max_llm_requests_per_minute: int | None = 600
    max_embedding_concurrency: int | None = 16
    max_embedding_requests_per_minute: int | None = 150
    # Process-wide cap on simultaneously-open browser tabs (Chromium pages),
    # shared across all WebBrowserTool instances. Bounds memory under wide/deep
    # subagent fan-out. None disables the cap.
    max_browser_tabs: int | None = 20
    dataset: str = "bird-sql"
    split: str = "dev"
    query_timeout: int | None = 300
    log_level: str = "WARNING"
    column_stats_mode: ColumnStatsMode = "skip_for_large_tables"

    @field_validator(*_POSITIVE_INT_OR_NONE_FIELDS, mode="before")
    @classmethod
    def _coerce_positive_int_or_none(cls, v: Any) -> int | None:
        if v is None:
            return None
        n = int(v)
        return n if n > 0 else None

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, v: Any) -> str:
        upper = str(v).upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if upper not in valid:
            raise ValueError(f"Invalid log level {v!r}. Must be one of {sorted(valid)}")
        return upper

    @model_validator(mode="after")
    def _validate_cache_flags(self) -> Self:
        for prefix in ("schema", "preprocessor"):
            enabled = getattr(self, f"{prefix}_cache_enabled")
            overwrite = getattr(self, f"{prefix}_cache_overwrite")
            required = getattr(self, f"{prefix}_cache_required")
            label = f"MINTQ_{prefix.upper()}_CACHE"
            if required and overwrite:
                raise ValueError(f"{label}_REQUIRED and {label}_OVERWRITE cannot be 1 at the same time")
            if required and not enabled:
                raise ValueError(f"{label}_REQUIRED cannot be 1 when {label}_ENABLED is 0")
        return self


class MintqConfig:
    """Global configuration for mintq.

    Resolution order for each option: ``configure()`` kwargs > env vars > defaults.
    """

    def __init__(self) -> None:
        self._overrides: dict[str, Any] = {}
        self._settings = _MintqSettings()

    def configure(self, **kwargs: Any) -> None:
        """Set configuration overrides.

        Only supplied kwargs are stored; omitted options keep their current
        resolution (env var > default). Call with no arguments to clear all
        overrides and re-read from environment.
        """
        if not kwargs:
            self._overrides.clear()
        else:
            self._overrides.update(kwargs)
        self._settings = _MintqSettings(**self._overrides)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._settings, name)

    def __repr__(self) -> str:
        items = {name: getattr(self, name) for name in type(self._settings).model_fields}
        return "MintqConfig(" + ", ".join(f"{k}={v!r}" for k, v in items.items()) + ")"


mintq_config = MintqConfig()
