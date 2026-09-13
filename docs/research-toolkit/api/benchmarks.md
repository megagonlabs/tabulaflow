# Benchmarks

Loaders provide tasks, their database connectors, and dataset-specific default
metrics. Use `dataset_registry` to select a loader by its benchmark key.

## Loader registry and contract

The registry supports `get_class(name)`, `list_names()`, and the `register`
decorator inherited from
[`ClassRegistry`][tabulaflow.core.registry.ClassRegistry]. Construct the
selected loader, then await `get_split_async(...)` to load tasks and connectors.

::: tabulaflow.research.benchmarks.registry.dataset_registry

::: tabulaflow.research.benchmarks.registry.DatasetLoaderProtocol

::: tabulaflow.research.benchmarks.registry.DatasetRegistry

## Task selection

QID filtering precedes deterministic sampling. Unknown QIDs and invalid sample
sizes raise `ValueError`.

::: tabulaflow.research.benchmarks.registry.select_tasks

::: tabulaflow.research.benchmarks.registry.selected_databases

## Built-in loaders

Loaders are also available from `tabulaflow.research.benchmarks`. Construction
and database access have dataset-specific prerequisites.

::: tabulaflow.research.benchmarks.bird_sql.BirdSQLDatasetLoader

::: tabulaflow.research.benchmarks.spider2_snow.Spider2SnowDatasetLoader

::: tabulaflow.research.benchmarks.spider2_lite.Spider2LiteDatasetLoader

::: tabulaflow.research.benchmarks.spider2_dbt.Spider2DbtDatasetLoader

::: tabulaflow.research.benchmarks.beaver.BeaverDatasetLoader

::: tabulaflow.research.benchmarks.arcs.ARCSDatasetLoader

::: tabulaflow.research.benchmarks.ambrosia_s.AmbrosiaSDatasetLoader

::: tabulaflow.research.benchmarks.cypherbench.CypherBenchDatasetLoader

## Installation and runtime requirements

`preflight_benchmark` checks local installation and managed runtime readiness.
It does not download data or start database services.

::: tabulaflow.research.benchmarks.registry.preflight_benchmark

::: tabulaflow.research.benchmarks.installation.BenchmarkInstallation

::: tabulaflow.research.benchmarks.installation.BenchmarkInstallationError

::: tabulaflow.research.benchmarks.runtime.BenchmarkRuntime

::: tabulaflow.research.benchmarks.runtime.BenchmarkRuntimeError
