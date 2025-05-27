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


config = Config()
