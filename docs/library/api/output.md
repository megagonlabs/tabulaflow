# Output

Define tables, charts, maps, and graphs as structured outputs, then resolve
them into data and specifications for your frontend. These APIs also provide
result storage and text formatting.

## Output specifications

Import specification models from `tabulaflow.output.specs`. Models can be
serialized with Pydantic's `model_dump_json()` and reconstructed with
`model_validate_json()`.

Serializing an `OutputSpec` saves its declaration, not the underlying
DataFrames or live connectors. Keep the store and required connectors
available for later resolution.

::: tabulaflow.output.specs.OutputSpec

::: tabulaflow.output.specs.FixedArtifactSource

::: tabulaflow.output.specs.ParameterizedArtifactSource

::: tabulaflow.output.specs.TableArtifactSpec

::: tabulaflow.output.specs.ChartArtifactSpec

::: tabulaflow.output.specs.MapArtifactSpec

::: tabulaflow.output.specs.GraphArtifactSpec

::: tabulaflow.output.specs.ArtifactSpecError

::: tabulaflow.output.specs.ArtifactSource

::: tabulaflow.output.specs.ArtifactSpec

::: tabulaflow.output.specs.artifact_source_ids

## Parameters and selections

`NumberParameter` describes a range, step, and default for a slider or numeric
input. `ChoiceParameter` describes a fixed set of options. The frontend sends
the selected values to `OutputResolver`; changing a selection needs no model call.

Query templates render text rather than SQL bind parameters. Keep templates
under application control and use validated parameters instead of unchecked input.

::: tabulaflow.output.specs.ChoiceOption

::: tabulaflow.output.specs.ChoiceParameter

::: tabulaflow.output.specs.NumberParameter

::: tabulaflow.output.specs.default_selection

::: tabulaflow.output.specs.parameter_default

::: tabulaflow.output.specs.validate_parameter_value

::: tabulaflow.output.specs.Selection

::: tabulaflow.output.specs.SelectionValue

::: tabulaflow.output.specs.canonical_selection_key

::: tabulaflow.output.specs.ParameterSpec

## Result storage

`OutputStore` assigns result and source IDs, retains query provenance, and
materializes parameterized sources. Configure `spill_dir` to persist result
DataFrames; otherwise they remain in memory.

Declaring a parameterized source does not execute its query. Results are
cached by selection and reused across artifacts. They are not automatically
refreshed when the underlying database changes.

::: tabulaflow.output.store.OutputStore

::: tabulaflow.output.store.MaterializedResult

::: tabulaflow.output.store.ResultMetadata

::: tabulaflow.output.store.ArtifactSourceResolutionError

::: tabulaflow.output.store.ArtifactSourceNotApplicable

::: tabulaflow.output.store.render_parameterized_query

## Resolving outputs

`OutputResolver.resolve(...)` returns data and specifications for a frontend.
Invalid output structure raises `OutputResolutionError`; expected failures
of individual artifacts become `UnavailableArtifact` entries. Browser
rendering belongs to the application layer.

::: tabulaflow.output.resolver.OutputResolver

::: tabulaflow.output.resolver.ResolvedOutput

::: tabulaflow.output.resolver.ResolvedArtifact

::: tabulaflow.output.resolver.ResolvedTableArtifact

::: tabulaflow.output.resolver.ResolvedChartArtifact

::: tabulaflow.output.resolver.ResolvedMapArtifact

::: tabulaflow.output.resolver.ResolvedGraphArtifact

::: tabulaflow.output.resolver.UnavailableArtifact

::: tabulaflow.output.resolver.OutputResolutionError

## Chart specifications

Chart artifacts carry Vega-Lite dictionaries. These helpers validate their
data references and identify their chart type.

::: tabulaflow.output.charts.validate_chart_spec

::: tabulaflow.output.charts.chart_type_label

::: tabulaflow.output.charts.ChartSpecError

## Map specifications

These models define the contents of `MapArtifactSpec.spec`. Parsing
validates structure; normalization resolves the specification against data.

::: tabulaflow.output.maps.MapSpec

::: tabulaflow.output.maps.MapViewSpec

::: tabulaflow.output.maps.MapLayerSpec

::: tabulaflow.output.maps.PointsLayerSpec

::: tabulaflow.output.maps.GeoJsonLayerSpec

::: tabulaflow.output.maps.InlinePointSpec

::: tabulaflow.output.maps.MarkerSpec

::: tabulaflow.output.maps.ColorEncodingSpec

::: tabulaflow.output.maps.SizeEncodingSpec

::: tabulaflow.output.maps.MapScalar

::: tabulaflow.output.maps.parse_map_spec

::: tabulaflow.output.maps.normalize_map_spec

::: tabulaflow.output.maps.referenced_source_ids

::: tabulaflow.output.maps.MapSpecError

## Graph specifications

These models define the contents of `GraphArtifactSpec.spec`. Sources
can refer to stored data or provide inline node and edge rows.

::: tabulaflow.output.graphs.GraphSpec

::: tabulaflow.output.graphs.GraphNodeSourceSpec

::: tabulaflow.output.graphs.GraphEdgeSourceSpec

::: tabulaflow.output.graphs.GraphLiteralValueSpec

::: tabulaflow.output.graphs.parse_graph_spec

::: tabulaflow.output.graphs.normalize_graph_spec

::: tabulaflow.output.graphs.referenced_source_ids

::: tabulaflow.output.graphs.materialize_graph_result

::: tabulaflow.output.graphs.GraphSize

::: tabulaflow.output.graphs.graph_size

::: tabulaflow.output.graphs.validate_graph_size

::: tabulaflow.output.graphs.GRAPH_MAX_NODES

::: tabulaflow.output.graphs.GRAPH_MAX_EDGES

::: tabulaflow.output.graphs.GraphSpecError

## Formatting

These formatters produce text for people or models. Import them from
`tabulaflow.output.formatting`.

::: tabulaflow.output.formatting.format_dataframe

::: tabulaflow.output.formatting.format_exec_result_markdown

::: tabulaflow.output.formatting.format_connector_summary

::: tabulaflow.output.formatting.format_json_schema_type

::: tabulaflow.output.formatting.format_single_line_text

::: tabulaflow.output.formatting.summarize_binary_values

::: tabulaflow.output.formatting.SQLDDLSchemaFormatter

::: tabulaflow.output.formatting.SQLCompactSchemaFormatter

::: tabulaflow.output.formatting.CypherSchemaFormatter

::: tabulaflow.output.formatting.SPARQLSchemaFormatter

## Custom schema formatters

Implement the protocol for the source's schema kind, declare its `schema_kind`
(such as `"sql"`), and register the class with `schema_formatter_registry`.
`get_schema_formatter_class` selects and validates a class by kind; construct
it with the options you need.

::: tabulaflow.output.formatting.get_schema_formatter_class

::: tabulaflow.output.formatting.SQLSchemaFormatter

::: tabulaflow.output.formatting.PropertyGraphSchemaFormatter

::: tabulaflow.output.formatting.RDFSchemaFormatter

::: tabulaflow.output.formatting.schema_formatter_registry

## Identifiers

These aliases name the string identifiers used in specifications and stores.

::: tabulaflow.output.specs.ResultId

::: tabulaflow.output.specs.ArtifactSourceId

::: tabulaflow.output.specs.ArtifactId

::: tabulaflow.output.specs.ParameterId
