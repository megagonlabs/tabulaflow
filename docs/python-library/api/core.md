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

Import these APIs from `tabulaflow.core.dataframe`. They normalize and serialize
DataFrames, including supported binary and nested values. `ExecResult.df` and
`SQLTableSchema.sampled_df` use `SerializableDataFrame` for Pydantic validation
and serialization.

::: tabulaflow.core.dataframe.SerializableDataFrame
    options:
      show_attribute_values: false

::: tabulaflow.core.dataframe.normalize_dataframe

::: tabulaflow.core.dataframe.dataframe_to_arrow

::: tabulaflow.core.dataframe.serialize_dataframe

::: tabulaflow.core.dataframe.deserialize_dataframe

## JSON serialization

Import these helpers from `tabulaflow.core.serialization`.

::: tabulaflow.core.serialization.json_ready

::: tabulaflow.core.serialization.dumps_strict_json

## Media values

Import media detection and extraction helpers from `tabulaflow.core.media`.
These APIs work with bytes and encoded values independently of model providers.

::: tabulaflow.core.media.MediaFormat

::: tabulaflow.core.media.Base64DataUri

::: tabulaflow.core.media.detect_media

::: tabulaflow.core.media.parse_base64_data_uri

::: tabulaflow.core.media.extract_media_bytes

::: tabulaflow.core.media.extract_media_items

## Class registry

`ClassRegistry` stores named implementation classes. Use
[`DataConnectorRegistry`][tabulaflow.data.registry.DataConnectorRegistry] for
live connector instances.

::: tabulaflow.core.registry.ClassRegistry
