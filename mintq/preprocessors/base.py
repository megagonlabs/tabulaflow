from typing import Any, Protocol, ClassVar
import asyncio
import collections
import os
from mintq.db_connector import NL2QDBConnector
from mintq.config import config
from pydantic import BaseModel
from mintq.schema import Usage
from mintq.registry import Registry


class BaseCachedDBPreprocessor(Protocol):
    name: ClassVar[str]
    output_type: ClassVar[type[BaseModel]]

    def usage(self) -> Usage | None: ...

    async def preprocess_async(self, db_connector: NL2QDBConnector) -> BaseModel: ...


_db_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)


class CachedPreprocessorMixin:
    name: ClassVar[str]
    output_type: ClassVar[type[BaseModel]]

    async def _preprocess_impl_async(self, db_connector: NL2QDBConnector) -> BaseModel:
        raise NotImplementedError()

    async def preprocess_async(self, db_connector: NL2QDBConnector) -> Any:
        schema_cache_dir = os.path.join(config.cache_dir, "preprocessors", self.name)
        os.makedirs(schema_cache_dir, exist_ok=True)
        cache_path = os.path.join(schema_cache_dir, f"{db_connector.global_id}.json")

        lock = _db_locks[db_connector.global_id]
        async with lock:
            if config.cache_enabled and os.path.exists(cache_path):
                if config.cache_overwrite:
                    os.remove(cache_path)
                else:
                    # if output type is pydantic
                    if issubclass(self.output_type, BaseModel):
                        with open(cache_path, "r", encoding="utf-8") as f:
                            return self.output_type.model_validate_json(f.read())
                    else:
                        raise NotImplementedError(f"Output type {self.output_type} is not supported for caching")

            if config.cache_required:
                raise FileNotFoundError(f"Cache required (MINTQ_CACHE_REQUIRED=1) but not found at {cache_path}")

            result = await self._preprocess_impl_async(db_connector)
            if issubclass(self.output_type, BaseModel):
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(result.model_dump_json(indent=2))
            else:
                raise NotImplementedError(f"Output type {self.output_type} is not supported for caching")
            return result


preprocessor_registry = Registry[BaseCachedDBPreprocessor]("preprocessor")
