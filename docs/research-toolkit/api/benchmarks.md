# Benchmarks

## Loader registry and contract

Look up loaders with `get_class(name)`, list them with `list_names()`, or add one
with `register`, inherited from [`ClassRegistry`][tabulaflow.core.registry.ClassRegistry].

::: tabulaflow.research.benchmarks.registry.dataset_registry

::: tabulaflow.research.benchmarks.registry.DatasetLoaderProtocol

::: tabulaflow.research.benchmarks.registry.DatasetRegistry

## Implement a loader

For reusable splits, implement `DatasetLoaderProtocol`:

- Declare `name`, available `splits`, `default_metrics`, and a
  `BenchmarkInstallation` describing the required local data.
- Implement `get_databases`, `get_tasks_async`, and `get_db_connectors_async`.
- Implement `get_split_async` to select tasks first, then open only the needed
  connectors and return an `NL2QDataset`. Reuse `select_tasks` for QID filtering
  and deterministic sampling, and `selected_databases` to find required databases.

Register the loader with `dataset_registry.register(YourLoader)`. Registrations
apply to the current Python process. For managed database services, supply a
`BenchmarkRuntime` with start, stop, and readiness callbacks.

## Task selection

QID filtering precedes deterministic sampling. Unknown QIDs and invalid sample
sizes raise `ValueError`.

::: tabulaflow.research.benchmarks.registry.select_tasks

::: tabulaflow.research.benchmarks.registry.selected_databases

## Built-in loaders

Loaders are re-exported from `tabulaflow.research.benchmarks`. See
[Benchmarks](../benchmarks.md) for setup requirements.

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

## Installation and runtime callbacks

Custom installations supply a fetch callback. Custom runtimes supply start,
stop, and readiness callbacks. Progress callbacks receive status messages.

::: tabulaflow.research.benchmarks.installation.ProgressCallback

::: tabulaflow.research.benchmarks.installation.FetchFunction

::: tabulaflow.research.benchmarks.runtime.RuntimeAction

::: tabulaflow.research.benchmarks.runtime.RuntimeCheck

::: tabulaflow.research.benchmarks.runtime.ReadinessCheck
