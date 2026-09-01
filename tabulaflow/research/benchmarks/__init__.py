"""Benchmark dataset loaders and registry."""

import importlib

from tabulaflow.research.benchmarks.registry import DatasetLoaderProtocol, dataset_registry

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


def __getattr__(name: str) -> object:
    try:
        module_name = _LOADERS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    return getattr(importlib.import_module(f"{__name__}.{module_name}"), name)


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
