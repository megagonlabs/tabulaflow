# Output

Output APIs separate data storage from presentation. A source supplies data;
an artifact describes a table or visualization; an `OutputSpec` declares the
sources, artifacts, and parameters to present together.

## Result storage

`OutputStore` assigns result and source IDs, retains query provenance, and
materializes parameterized sources. Configure `spill_dir` to persist result
DataFrames; otherwise they remain in memory.

::: tabulaflow.output.store.OutputStore

::: tabulaflow.output.store.MaterializedResult

::: tabulaflow.output.store.ResultMetadata

::: tabulaflow.output.store.ArtifactSourceResolutionError

::: tabulaflow.output.store.ArtifactSourceNotApplicable

## Output specifications

Import specification models from `tabulaflow.output.specs`. Models can be
serialized with Pydantic's `model_dump_json()` and reconstructed with
`model_validate_json()`.

::: tabulaflow.output.specs.OutputSpec

::: tabulaflow.output.specs.FixedArtifactSource

::: tabulaflow.output.specs.ParameterizedArtifactSource

::: tabulaflow.output.specs.TableArtifactSpec

::: tabulaflow.output.specs.ChartArtifactSpec

::: tabulaflow.output.specs.MapArtifactSpec

::: tabulaflow.output.specs.GraphArtifactSpec

::: tabulaflow.output.specs.ArtifactSpecError

## Parameters

```python
from tabulaflow.output.specs import ChoiceOption, ChoiceParameter, default_selection

region = ChoiceParameter(
    id="region",
    label="Region",
    choices=[ChoiceOption(id="west", label="West"), ChoiceOption(id="east", label="East")],
)
print(default_selection([region]))
```

::: tabulaflow.output.specs.ChoiceOption

::: tabulaflow.output.specs.ChoiceParameter

::: tabulaflow.output.specs.NumberParameter

::: tabulaflow.output.specs.default_selection

::: tabulaflow.output.specs.validate_parameter_value

::: tabulaflow.output.specs.Selection

::: tabulaflow.output.specs.ArtifactSource

::: tabulaflow.output.specs.ArtifactSpec

::: tabulaflow.output.specs.ParameterSpec

## Resolving outputs

`OutputResolver.resolve(...)` returns data and specifications for a frontend.
Invalid output structure raises `OutputResolutionError`; expected failures
of individual artifacts become `UnavailableArtifact` entries. Browser
rendering belongs to the application layer.

::: tabulaflow.output.resolver.OutputResolver

::: tabulaflow.output.resolver.ResolvedOutput

::: tabulaflow.output.resolver.ResolvedTableArtifact

::: tabulaflow.output.resolver.ResolvedChartArtifact

::: tabulaflow.output.resolver.ResolvedMapArtifact

::: tabulaflow.output.resolver.ResolvedGraphArtifact

::: tabulaflow.output.resolver.UnavailableArtifact

::: tabulaflow.output.resolver.OutputResolutionError

## Formatting

These formatters produce text for people or models. Import them from
`tabulaflow.output.formatting`.

::: tabulaflow.output.formatting.format_dataframe

::: tabulaflow.output.formatting.format_exec_result_markdown

::: tabulaflow.output.formatting.format_connector_summary

::: tabulaflow.output.formatting.SQLDDLSchemaFormatter

::: tabulaflow.output.formatting.SQLBasicSchemaFormatter

::: tabulaflow.output.formatting.CypherSchemaFormatter

::: tabulaflow.output.formatting.SPARQLSchemaFormatter
