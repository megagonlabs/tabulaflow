import logging
import os
from typing import Literal, get_args

ColumnStatsMode = Literal["always_precise", "sample_for_large_tables", "skip_for_large_tables"]


class MintqConfig:
    DEFAULT_CACHE_DIR = "cache"
    DEFAULT_CACHE_ENABLED = True
    DEFAULT_CACHE_OVERWRITE = False
    DEFAULT_CACHE_REQUIRED = False
    DEFAULT_INSTRUMENT_ENABLED = True
    DEFAULT_INSTRUMENT_PREFIX = "exp"
    DEFAULT_DF_MAX_ROWS = None
    DEFAULT_MAX_LLM_CONCURRENCY = 16
    DEFAULT_MAX_LLM_REQUESTS_PER_MINUTE = 600
    DEFAULT_MAX_EMBEDDING_CONCURRENCY = 4
    DEFAULT_MAX_EMBEDDING_REQUESTS_PER_MINUTE = 150
    DEFAULT_DATASET = "bird-sql"
    DEFAULT_SPLIT = "dev"
    DEFAULT_QUERY_TIMEOUT = 90
    DEFAULT_LOG_LEVEL = "WARNING"
    DEFAULT_COLUMN_STATS_MODE: ColumnStatsMode = "skip_for_large_tables"
    # DEFAULT_MAX_LLM_CONCURRENCY = 4
    # DEFAULT_MAX_LLM_REQUESTS_PER_MINUTE = 150
    # DEFAULT_MAX_EMBEDDING_CONCURRENCY = 1
    # DEFAULT_MAX_EMBEDDING_REQUESTS_PER_MINUTE = 40

    def __init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.cache_required and self.cache_overwrite:
            raise ValueError("MINTQ_CACHE_REQUIRED and MINTQ_CACHE_OVERWRITE cannot be 1 at the same time")

        if self.cache_required and not self.cache_enabled:
            raise ValueError("MINTQ_CACHE_REQUIRED cannot be 1 when MINTQ_CACHE_ENABLED is 0")

    @property
    def cache_dir(self) -> str:
        if (value := os.getenv("MINTQ_CACHE_DIR")) is not None:
            return value
        return self.DEFAULT_CACHE_DIR

    @property
    def cache_enabled(self) -> bool:
        if (value := os.getenv("MINTQ_CACHE_ENABLED")) is not None:
            return value == "1"
        return self.DEFAULT_CACHE_ENABLED

    @property
    def cache_overwrite(self) -> bool:
        """Overwrite existing cache files."""
        if (value := os.getenv("MINTQ_CACHE_OVERWRITE")) is not None:
            return value == "1"
        return self.DEFAULT_CACHE_OVERWRITE

    @property
    def cache_required(self) -> bool:
        """Raise an error if cache is not found."""
        if (value := os.getenv("MINTQ_CACHE_REQUIRED")) is not None:
            return value == "1"
        return self.DEFAULT_CACHE_REQUIRED

    @property
    def instrument_enabled(self) -> bool:
        if (value := os.getenv("MINTQ_INSTRUMENT_ENABLED")) is not None:
            return value == "1"
        return self.DEFAULT_INSTRUMENT_ENABLED

    @property
    def instrument_prefix(self) -> str:
        if (value := os.getenv("MINTQ_INSTRUMENT_PREFIX")) is not None:
            return value
        return self.DEFAULT_INSTRUMENT_PREFIX

    @property
    def df_max_rows(self) -> int | None:
        if (value := os.getenv("MINTQ_DF_MAX_ROWS")) is not None:
            return int(value) if int(value) > 0 else None
        return self.DEFAULT_DF_MAX_ROWS

    @property
    def max_llm_concurrency(self) -> int | None:
        """Maximum number of concurrent LLM calls."""
        if (value := os.getenv("MINTQ_MAX_LLM_CONCURRENCY")) is not None:
            return int(value) if int(value) > 0 else None
        return self.DEFAULT_MAX_LLM_CONCURRENCY

    @property
    def max_llm_requests_per_minute(self) -> int | None:
        """Maximum number of LLM requests per minute."""
        if (value := os.getenv("MINTQ_MAX_LLM_REQUESTS_PER_MINUTE")) is not None:
            return int(value) if int(value) > 0 else None
        return self.DEFAULT_MAX_LLM_REQUESTS_PER_MINUTE

    @property
    def max_embedding_concurrency(self) -> int | None:
        """Maximum number of concurrent embedding calls."""
        if (value := os.getenv("MINTQ_MAX_EMBEDDING_CONCURRENCY")) is not None:
            return int(value) if int(value) > 0 else None
        return self.DEFAULT_MAX_EMBEDDING_CONCURRENCY

    @property
    def max_embedding_requests_per_minute(self) -> int | None:
        """Maximum number of embedding requests per minute."""
        if (value := os.getenv("MINTQ_MAX_EMBEDDING_REQUESTS_PER_MINUTE")) is not None:
            return int(value) if int(value) > 0 else None
        return self.DEFAULT_MAX_EMBEDDING_REQUESTS_PER_MINUTE

    @property
    def default_dataset(self) -> str:
        if (value := os.getenv("MINTQ_DATASET")) is not None:
            return value
        return self.DEFAULT_DATASET

    @property
    def default_split(self) -> str:
        if (value := os.getenv("MINTQ_SPLIT")) is not None:
            return value
        return self.DEFAULT_SPLIT

    @property
    def default_query_timeout(self) -> int | None:
        if (value := os.getenv("MINTQ_DEFAULT_QUERY_TIMEOUT")) is not None:
            return int(value) if int(value) > 0 else None
        return self.DEFAULT_QUERY_TIMEOUT

    @property
    def log_level(self) -> int:
        """Log level for the mintq logger.

        Set via ``MINTQ_LOG_LEVEL`` (e.g. ``DEBUG``, ``INFO``, ``WARNING``).
        """
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if (value := os.getenv("MINTQ_LOG_LEVEL")) is not None:
            value = value.upper()
            if value not in valid_levels:
                raise ValueError(f"Invalid MINTQ_LOG_LEVEL={value!r}. Must be one of {valid_levels}")
            return int(getattr(logging, value))
        return int(getattr(logging, self.DEFAULT_LOG_LEVEL))

    @property
    def column_stats_mode(self) -> ColumnStatsMode:
        """Column statistics collection mode for schema building.

        Controls how column-level statistics (null ratio, unique count) are
        collected for large tables:
        - ``"always_precise"``: Always compute exact statistics.
        - ``"sample_for_large_tables"``: Sample large tables before computing.
        - ``"skip_for_large_tables"``: Skip statistics for large tables.
        """
        if (value := os.getenv("MINTQ_COLUMN_STATS_MODE")) is not None:
            if value not in get_args(ColumnStatsMode):
                raise ValueError(
                    f"Invalid MINTQ_COLUMN_STATS_MODE={value!r}. Must be one of {sorted(get_args(ColumnStatsMode))}"
                )
            return value  # type: ignore[return-value]
        return self.DEFAULT_COLUMN_STATS_MODE

    def __repr__(self) -> str:
        props = {
            name: getattr(self, name) for name, attr in self.__class__.__dict__.items() if isinstance(attr, property)
        }
        values = ", ".join(f"{k}={v!r}" for k, v in props.items())
        return f"MintqConfig({values})"

    def setup_logging(self) -> None:
        """Configure logging for the mintq package.

        Sets the root logger to WARNING and the ``mintq`` logger to the level
        specified by ``MINTQ_LOG_LEVEL`` (default ``WARNING``).
        """
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("mintq").setLevel(self.log_level)

    def reload_from_env(self) -> None:
        """Re-validate the config from environment variables."""
        self._validate()


mintq_config = MintqConfig()
