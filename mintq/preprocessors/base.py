from typing import Any, Protocol, ClassVar, Literal, TypeAlias, TypeVar, Generic, get_origin, get_args
import numpy as np
import numpy.typing as npt
import asyncio
import collections
import os
from mintq.db_connector import NL2QDBConnector
from mintq.config import mintq_config
from pydantic import BaseModel
from mintq.schema import Usage, NL2QDataset
from mintq.registry import Registry


CacheableResult: TypeAlias = BaseModel | npt.NDArray[Any] | tuple[BaseModel | npt.NDArray[Any], ...]


class BaseDBPreprocessor(Protocol):
    name: ClassVar[str]
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"
    output_type: ClassVar[type[CacheableResult]]

    def usage(self) -> Usage | None: ...

    async def preprocess_async(self, db_connector: NL2QDBConnector) -> CacheableResult: ...


class BaseDatasetPreprocessor(Protocol):
    name: ClassVar[str]
    input_type: ClassVar[Literal["dataset"]] = "dataset"
    output_type: ClassVar[type[CacheableResult]]

    def usage(self) -> Usage | None: ...

    async def preprocess_async(self, dataset: NL2QDataset) -> CacheableResult: ...


OutputT = TypeVar("OutputT", bound=CacheableResult)

_cache_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)
_memory_cache: dict[tuple[str, ...], CacheableResult] = {}


class CachedPreprocessorMixin(Generic[OutputT]):
    name: ClassVar[str]
    input_type: ClassVar[Literal["db_connector", "dataset"]]
    output_type: ClassVar[type[CacheableResult]]

    async def _preprocess_impl_async(self, input_data: Any) -> OutputT:
        raise NotImplementedError()

    def _get_cache_id_suffix(self) -> str:
        """Return an optional suffix appended to the cache identifier.

        Subclasses can override this to differentiate cache entries when the
        same preprocessor may produce different results depending on its
        configuration (e.g. the embedding model used). The suffix is appended
        to the base cache id which is either the dataset or db_connector identifier.

        Returns:
            A string to append to the cache id. Defaults to an empty string
            (no suffix).
        """
        return ""

    def _get_cache_id(self, input_data: NL2QDBConnector | NL2QDataset) -> str:
        """Get a unique cache identifier for the input data."""
        if isinstance(input_data, NL2QDataset):
            cache_id = f"{input_data.name}_{input_data.split}"
            if input_data.databases is not None:
                cache_id += "".join(f"_{db}" for db in input_data.databases)
            return cache_id + self._get_cache_id_suffix()
        else:
            return input_data.global_id + self._get_cache_id_suffix()

    def _is_ndarray_type(self, t: type) -> bool:
        """Check if a type is a numpy ndarray type."""
        if t is np.ndarray:
            return True
        return get_origin(t) is np.ndarray

    def _is_tuple_type(self) -> bool:
        """Check if output_type is a tuple type."""
        return get_origin(self.output_type) is tuple

    def _get_tuple_element_types(self) -> tuple[type, ...]:
        """Get element types from tuple output_type."""
        args = get_args(self.output_type)
        if args and args[-1] is ...:
            raise NotImplementedError("Variable length tuples (tuple[X, ...]) are not supported for caching")
        return args

    def _get_element_cache_path(self, cache_dir: str, cache_id: str, elem_type: type, index: int | None = None) -> str:
        """Get cache file path for a single element."""
        suffix = f"_{index}" if index is not None else ""
        if self._is_ndarray_type(elem_type):
            return os.path.join(cache_dir, f"{cache_id}{suffix}.npy")
        else:
            return os.path.join(cache_dir, f"{cache_id}{suffix}.json")

    def _get_cache_paths(self, cache_dir: str, cache_id: str) -> list[str]:
        """Get cache file paths based on output type."""
        if self._is_tuple_type():
            element_types = self._get_tuple_element_types()
            return [
                self._get_element_cache_path(cache_dir, cache_id, elem_type, i)
                for i, elem_type in enumerate(element_types)
            ]
        else:
            return [self._get_element_cache_path(cache_dir, cache_id, self.output_type)]

    def _load_element(self, cache_path: str, elem_type: type) -> BaseModel | npt.NDArray[Any]:
        """Load a single cached element."""
        if self._is_ndarray_type(elem_type):
            return np.load(cache_path, allow_pickle=True)  # type: ignore
        elif isinstance(elem_type, type) and issubclass(elem_type, BaseModel):
            with open(cache_path, "r", encoding="utf-8") as f:
                return elem_type.model_validate_json(f.read())
        else:
            raise NotImplementedError(f"Element type {elem_type} is not supported for caching")

    def _save_element(self, cache_path: str, elem: BaseModel | npt.NDArray[Any], elem_type: type) -> None:
        """Save a single element to cache."""
        if self._is_ndarray_type(elem_type):
            np.save(cache_path, elem)  # type: ignore
        elif isinstance(elem_type, type) and issubclass(elem_type, BaseModel):
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(elem.model_dump_json(indent=2))  # type: ignore
        else:
            raise NotImplementedError(f"Element type {elem_type} is not supported for caching")

    def _load_from_cache(self, cache_paths: list[str]) -> CacheableResult:
        """Load cached result based on output type."""
        if self._is_tuple_type():
            element_types = self._get_tuple_element_types()
            return tuple(self._load_element(path, elem_type) for path, elem_type in zip(cache_paths, element_types))
        else:
            return self._load_element(cache_paths[0], self.output_type)

    def _save_to_cache(self, cache_paths: list[str], result: Any) -> None:
        """Save result to cache based on output type."""
        if self._is_tuple_type():
            element_types = self._get_tuple_element_types()
            for path, elem, elem_type in zip(cache_paths, result, element_types):
                self._save_element(path, elem, elem_type)
        else:
            self._save_element(cache_paths[0], result, self.output_type)

    def _cache_exists(self, cache_paths: list[str]) -> bool:
        """Check if all cache files exist."""
        return all(os.path.exists(path) for path in cache_paths)

    async def preprocess_async(self, input_data: NL2QDBConnector | NL2QDataset) -> OutputT:
        cache_dir = os.path.join(mintq_config.cache_dir, "preprocessors", self.name)
        os.makedirs(cache_dir, exist_ok=True)

        cache_id = self._get_cache_id(input_data)
        cache_paths = self._get_cache_paths(cache_dir, cache_id)

        cache_key = tuple(cache_paths)
        lock = _cache_locks[cache_id]
        async with lock:
            if mintq_config.cache_enabled and not mintq_config.cache_overwrite and self._cache_exists(cache_paths):
                if cache_key in _memory_cache:
                    return _memory_cache[cache_key]  # type: ignore[return-value]
                result = self._load_from_cache(cache_paths)
                _memory_cache[cache_key] = result
                return result  # type: ignore[return-value]

            if mintq_config.cache_required:
                raise FileNotFoundError(f"Cache required (MINTQ_CACHE_REQUIRED=1) but not found at {cache_paths}")

            result = await self._preprocess_impl_async(input_data)
            if mintq_config.cache_enabled:
                self._save_to_cache(cache_paths, result)
                _memory_cache[cache_key] = result
            return result


NL2QPreprocessor: TypeAlias = BaseDBPreprocessor | BaseDatasetPreprocessor

preprocessor_registry = Registry[NL2QPreprocessor]("preprocessor")
