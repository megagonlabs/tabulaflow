import os


class Config:
    @property
    def cache_dir(self) -> str:
        return os.getenv("MINTQ_CACHE_DIR", "cache")

    @property
    def cache_enabled(self) -> bool:
        return os.getenv("MINTQ_CACHE_ENABLED", "1") == "1"

    @property
    def cache_refresh(self) -> bool:
        return os.getenv("MINTQ_CACHE_REFRESH", "0") == "1"

    @property
    def instrument_enabled(self) -> bool:
        return os.getenv("MINTQ_INSTRUMENT_ENABLED", "1") == "1"

    @property
    def instrument_prefix(self) -> str:
        return os.getenv("MINTQ_INSTRUMENT_PREFIX", "exp")

    @property
    def df_max_rows(self) -> int | None:
        value = int(os.getenv("MINTQ_DF_MAX_ROWS", "-1"))
        return value if value > 0 else None

    @property
    def max_llm_concurrency(self) -> int | None:
        """Maximum number of concurrent LLM calls. Currently this is achieved by limiting the number of concurrent Agent.run() calls."""
        value = int(os.getenv("MINTQ_MAX_LLM_CONCURRENCY", "16"))
        return value if value > 0 else None

    def __repr__(self):
        props = {
            name: getattr(self, name) for name, attr in self.__class__.__dict__.items() if isinstance(attr, property)
        }
        values = ", ".join(f"{k}={v!r}" for k, v in props.items())
        return f"Config({values})"


config = Config()
