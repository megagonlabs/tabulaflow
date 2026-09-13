# Data

Use `connect_data_source` to open a source, then query it through the
`DataConnector` interface. The caller closes each connector when finished.

## Opening sources

::: tabulaflow.data.connect.connect_data_source

::: tabulaflow.data.connect.connect_url

## Connector interface and registry

Query failures are represented by `ExecResult.error`. Connection setup and
registry validation can raise exceptions directly. `read_only=True` requests
the connector's read-only behavior; database permissions remain the security
boundary for SQL connections.

::: tabulaflow.data.protocols.DataConnector

::: tabulaflow.data.registry.DataConnectorRegistry

::: tabulaflow.data.protocols.validate_global_id

## Connector implementations

`SQLConnector`, `Neo4jConnector`, and `SPARQLConnector` implement the
`DataConnector` interface. Use their `from_url_async(...)` class methods to
construct them directly. `SQLConnector` also supports writing DataFrames to
a writable database.

::: tabulaflow.data.sql.SQLConnector
    options:
      merge_init_into_class: false

::: tabulaflow.data.sql.TableWriteMode

::: tabulaflow.data.neo4j.Neo4jConnector
    options:
      merge_init_into_class: false

::: tabulaflow.data.sparql.SPARQLConnector
    options:
      merge_init_into_class: false

## Execution errors

These errors identify result-size and SPARQL response failures. Query methods
that return `ExecResult` capture execution failures in `error`; lower-level
execution APIs may raise directly.

::: tabulaflow.data.protocols.ResultTooLargeError

::: tabulaflow.data.sparql.InvalidSPARQLResultError

::: tabulaflow.data.sparql.SPARQLResponseTooLargeError

## Configuration

Connector settings use explicit arguments first, then `TABULAFLOW_*`
environment variables, then defaults. Pass `DataSourceConnectorConfigs` to
`connect_data_source` when the source's backend is selected at runtime.

::: tabulaflow.data.config.SQLConnectorConfig

::: tabulaflow.data.config.Neo4jConnectorConfig

::: tabulaflow.data.config.SPARQLConnectorConfig

::: tabulaflow.data.config.DataSourceConnectorConfigs

## Source catalog

::: tabulaflow.data.catalog.DataSourceDefinition

::: tabulaflow.data.catalog.DEFAULT_DATA_SOURCE_DEFINITIONS

::: tabulaflow.data.catalog.resolve_data_source_definition

## File and dataset loaders

`connect_data_source` dispatches to these loaders. Call them directly when you
need loader-specific options.

::: tabulaflow.data.loaders.files.load_files

::: tabulaflow.data.loaders.huggingface.load_hf_dataset

::: tabulaflow.data.loaders.huggingface.HuggingFaceSubsetRequiredError

::: tabulaflow.data.loaders.DATA_FILE_EXTENSIONS

::: tabulaflow.data.loaders.huggingface.build_hf_dataset_url

::: tabulaflow.data.loaders.huggingface.parse_hf_dataset_url

::: tabulaflow.data.loaders.huggingface.is_hf_dataset_url
