from typing import Any, Protocol, ClassVar, Literal, TypeAlias
import numpy as np
import numpy.typing as npt
import asyncio
import collections
import os
from mintq.db_connector import NL2QDBConnector
from mintq.config import config
from pydantic import BaseModel
from mintq.schema import Usage, NL2QDataset
from mintq.registry import Registry


class BaseDBPreprocessor(Protocol):
    name: ClassVar[str]
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"
    output_type: ClassVar[type[BaseModel]]

    def usage(self) -> Usage | None: ...

    async def preprocess_async(self, db_connector: NL2QDBConnector) -> BaseModel: ...


class BaseDatasetPreprocessor(Protocol):
    name: ClassVar[str]
    input_type: ClassVar[Literal["dataset"]] = "dataset"
    output_type: ClassVar[type[BaseModel] | type[npt.NDArray[Any]]]

    def usage(self) -> Usage | None: ...

    async def preprocess_async(self, dataset: NL2QDataset) -> BaseModel | npt.NDArray[Any]: ...


_cache_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)


class CachedPreprocessorMixin:
    name: ClassVar[str]
    input_type: ClassVar[Literal["db_connector", "dataset"]]
    output_type: ClassVar[type[BaseModel] | type[npt.NDArray[Any]]]

    async def _preprocess_impl_async(self, input_data: NL2QDBConnector | NL2QDataset) -> Any:
        raise NotImplementedError()

    def _get_cache_id(self, input_data: NL2QDBConnector | NL2QDataset) -> str:
        """Get a unique cache identifier for the input data."""
        if isinstance(input_data, NL2QDataset):
            return f"{input_data.name}_{input_data.split}"
        else:
            return input_data.global_id

    def _get_cache_path(self, cache_dir: str, cache_id: str) -> str:
        """Get the cache file path based on output type."""
        if self.output_type is np.ndarray:
            return os.path.join(cache_dir, f"{cache_id}.npy")
        else:
            return os.path.join(cache_dir, f"{cache_id}.json")

    def _load_from_cache(self, cache_path: str) -> Any:
        """Load cached result based on output type."""
        if self.output_type is np.ndarray:
            return np.load(cache_path, allow_pickle=True)
        elif issubclass(self.output_type, BaseModel):
            with open(cache_path, "r", encoding="utf-8") as f:
                return self.output_type.model_validate_json(f.read())
        else:
            raise NotImplementedError(f"Output type {self.output_type} is not supported for caching")

    def _save_to_cache(self, cache_path: str, result: Any) -> None:
        """Save result to cache based on output type."""
        if self.output_type is np.ndarray:
            np.save(cache_path, result)
        elif issubclass(self.output_type, BaseModel):
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))
        else:
            raise NotImplementedError(f"Output type {self.output_type} is not supported for caching")

    async def preprocess_async(self, input_data: NL2QDBConnector | NL2QDataset) -> Any:
        cache_dir = os.path.join(config.cache_dir, "preprocessors", self.name)
        os.makedirs(cache_dir, exist_ok=True)

        cache_id = self._get_cache_id(input_data)
        cache_path = self._get_cache_path(cache_dir, cache_id)

        lock = _cache_locks[cache_id]
        async with lock:
            if config.cache_enabled and os.path.exists(cache_path):
                if config.cache_overwrite:
                    os.remove(cache_path)
                else:
                    return self._load_from_cache(cache_path)

            if config.cache_required:
                raise FileNotFoundError(f"Cache required (MINTQ_CACHE_REQUIRED=1) but not found at {cache_path}")

            result = await self._preprocess_impl_async(input_data)
            self._save_to_cache(cache_path, result)
            return result


NL2QPreprocessor: TypeAlias = BaseDBPreprocessor | BaseDatasetPreprocessor

preprocessor_registry = Registry[NL2QPreprocessor]("preprocessor")
