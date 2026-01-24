import os


class Config:
    DEFAULT_CACHE_DIR = "cache"
    DEFAULT_CACHE_ENABLED = True
    DEFAULT_CACHE_REFRESH = False
    DEFAULT_INSTRUMENT_ENABLED = True
    DEFAULT_INSTRUMENT_PREFIX = "exp"
    DEFAULT_DF_MAX_ROWS = None
    DEFAULT_MAX_LLM_CONCURRENCY = 16
    DEFAULT_MAX_LLM_REQUESTS_PER_MINUTE = 600

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
    def cache_refresh(self) -> bool:
        if (value := os.getenv("MINTQ_CACHE_REFRESH")) is not None:
            return value == "1"
        return self.DEFAULT_CACHE_REFRESH

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

    def __repr__(self) -> str:
        props = {
            name: getattr(self, name) for name, attr in self.__class__.__dict__.items() if isinstance(attr, property)
        }
        values = ", ".join(f"{k}={v!r}" for k, v in props.items())
        return f"Config({values})"


config = Config()
