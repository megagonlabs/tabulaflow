"""Benchmark dataset loaders and registry."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

from tabulaflow.research.benchmarks.registry import DatasetLoaderProtocol, dataset_registry


if TYPE_CHECKING:
    from tabulaflow.research.benchmarks.ambrosia_s import AmbrosiaSDatasetLoader
    from tabulaflow.research.benchmarks.arcs import ARCSDatasetLoader
    from tabulaflow.research.benchmarks.beaver import BeaverDatasetLoader
    from tabulaflow.research.benchmarks.bird_sql import BirdSQLDatasetLoader
    from tabulaflow.research.benchmarks.cypherbench import CypherBenchDatasetLoader
    from tabulaflow.research.benchmarks.spider2_dbt import Spider2DbtDatasetLoader
    from tabulaflow.research.benchmarks.spider2_lite import Spider2LiteDatasetLoader
    from tabulaflow.research.benchmarks.spider2_snow import Spider2SnowDatasetLoader

_LOADERS = {
    "AmbrosiaSDatasetLoader": "ambrosia_s",
    "ARCSDatasetLoader": "arcs",
    "BeaverDatasetLoader": "beaver",
    "BirdSQLDatasetLoader": "bird_sql",
    "CypherBenchDatasetLoader": "cypherbench",
    "Spider2DbtDatasetLoader": "spider2_dbt",
    "Spider2LiteDatasetLoader": "spider2_lite",
    "Spider2SnowDatasetLoader": "spider2_snow",
}


def __getattr__(name: str) -> Any:
    try:
        module_name = _LOADERS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(f"{__name__}.{module_name}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LOADERS})


__all__ = [
    "DatasetLoaderProtocol",
    "BirdSQLDatasetLoader",
    "Spider2SnowDatasetLoader",
    "Spider2LiteDatasetLoader",
    "Spider2DbtDatasetLoader",
    "BeaverDatasetLoader",
    "ARCSDatasetLoader",
    "AmbrosiaSDatasetLoader",
    "CypherBenchDatasetLoader",
    "dataset_registry",
]
