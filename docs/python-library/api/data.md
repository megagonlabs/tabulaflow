# Data

Connect to SQL databases, Neo4j, SPARQL endpoints, files, and datasets through
a common async interface. Work with structured schemas and query results
while keeping each backend's query language.

Import connector classes, `connect_data_source`, and `DataConnectorRegistry`
from `tabulaflow.data`.

## Connector interface

Implement `DataConnector` to add a custom backend.

Query failures are represented by `ExecResult.error`. `read_only=True`
requests the connector's read-only behavior; database permissions remain the
security boundary for SQL connections.

The caller closes each connector when finished.

Check `ExecResult.error` before using its payload. Successful statements such
as `CREATE TABLE` can have no DataFrame. DataFrame writes and connection
setup can raise exceptions directly.

::: tabulaflow.data.protocols.DataConnector

## Opening sources

Connection setup can raise exceptions directly.

::: tabulaflow.data.connect.connect_data_source

::: tabulaflow.data.connect.connect_url

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

## Configuration

Connector settings use explicit arguments first, then `TABULAFLOW_*`
environment variables, then defaults. Pass `DataSourceConnectorConfigs` to
`connect_data_source` when the source's backend is selected at runtime.

SQL connectors support both sync and async drivers through the same awaited
API. A query's `timeout` argument overrides the configured deadline and
requests cancellation of the underlying query. Timeouts appear in
`ExecResult.error`, while task cancellation propagates as
`asyncio.CancelledError`.

Schema and query caches are off by default. Enable them for reusable database
snapshots; call `refresh_schema_async()` to refresh the schema explicitly.
Query caching requires a read-only connector. Share a `dbms_semaphore` across
SQL connectors to limit concurrency against the same warehouse.

::: tabulaflow.data.config.DataSourceConnectorConfigs

::: tabulaflow.data.config.SQLConnectorConfig

::: tabulaflow.data.config.Neo4jConnectorConfig

::: tabulaflow.data.config.SPARQLConnectorConfig

## Connector registry

Registry validation can raise exceptions directly.

::: tabulaflow.data.registry.DataConnectorRegistry

::: tabulaflow.data.protocols.validate_global_id

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

## Source catalog

Catalog entries are named source definitions, not live connectors.
`connect_data_source` resolves an entry to its `source`, then dispatches to
the appropriate loader or connector. An entry can name a local file, a
Hugging Face dataset, or a connection URL. The connector registry instead
holds live connector instances.

::: tabulaflow.data.catalog.DataSourceDefinition

::: tabulaflow.data.catalog.DEFAULT_DATA_SOURCE_DEFINITIONS

::: tabulaflow.data.catalog.resolve_data_source_definition

## Execution errors

These errors identify result-size and SPARQL response failures. Query methods
that return `ExecResult` capture execution failures in `error`; lower-level
execution APIs may raise directly.

::: tabulaflow.data.protocols.ResultTooLargeError

::: tabulaflow.data.sparql.InvalidSPARQLResultError

::: tabulaflow.data.sparql.SPARQLResponseTooLargeError
