# Core

Shared types are available from `tabulaflow.core`. They describe data and
results independently of a live connection, agent, or frontend.

## Schema and language unions

::: tabulaflow.core.schema.DataSourceSchema

::: tabulaflow.core.schema.SQLDialect

::: tabulaflow.core.schema.GraphQueryLanguage

::: tabulaflow.core.schema.QueryLanguage

## SQL schemas

`SQLSchema` contains tables and columns; `TableRef` and `ColumnRef` identify
parts of a schema without copying their metadata.

::: tabulaflow.core.schema.SQLSchema

::: tabulaflow.core.schema.SQLTableSchema

::: tabulaflow.core.schema.SQLColumnSchema

::: tabulaflow.core.schema.ForeignKeySchema

::: tabulaflow.core.schema.TableRef

::: tabulaflow.core.schema.ColumnRef

## Graph and RDF schemas

::: tabulaflow.core.schema.PropertyGraphSchema

::: tabulaflow.core.schema.NodeSchema

::: tabulaflow.core.schema.RelationshipSchema

::: tabulaflow.core.schema.RelationshipEndpoint

::: tabulaflow.core.schema.GraphPropertySchema

::: tabulaflow.core.schema.RDFSchema

## Execution results

`ExecResult` represents a successful statement or an execution error. Check
`error` before consuming a payload. A successful statement can have no
DataFrame, for example when executing DDL. A graph result also carries its
tabular representation.

::: tabulaflow.core.results.ExecResult

::: tabulaflow.core.results.ErrorInfo

::: tabulaflow.core.results.GraphResult

::: tabulaflow.core.results.GraphResultNode

::: tabulaflow.core.results.GraphResultEdge

## DataFrame serialization

These functions normalize and serialize result DataFrames, including supported
binary and nested values. `ExecResult` uses this serialization when exporting
its DataFrame through Pydantic.

::: tabulaflow.core.dataframe.normalize_dataframe

::: tabulaflow.core.dataframe.dataframe_to_arrow

::: tabulaflow.core.dataframe.serialize_dataframe

::: tabulaflow.core.dataframe.deserialize_dataframe

## JSON serialization

Import these helpers from `tabulaflow.core.serialization`.

::: tabulaflow.core.serialization.json_ready

::: tabulaflow.core.serialization.dumps_strict_json

## Class registry

`ClassRegistry` stores named implementation classes. Use
[`DataConnectorRegistry`][tabulaflow.data.registry.DataConnectorRegistry] for
live connector instances.

::: tabulaflow.core.registry.ClassRegistry
