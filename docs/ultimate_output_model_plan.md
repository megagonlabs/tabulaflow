# Ultimate Output Model Plan

Status: target architecture, implemented as the clean output data model.

## Core idea

```text
OutputSpec = Parameters + Sources + Artifacts

Parameters describe user-controlled values.
Sources produce materialized results.
Artifacts declare table/chart/map/graph displays over sources.
Results are runtime materializations produced by sources.
```

The core invariant is:

```text
ArtifactSpec -> SourceSpec -> ResultMetadata / ResultPayload
```

`core/outputs.py` owns only the declarative, serializable contract. Runtime payloads stay outside core.

## Ids and selections

```python
ParameterId = str
SourceId = str
ArtifactId = str
ResultId = str
SelectionValue = str | int | float | bool
Selection = dict[ParameterId, SelectionValue]
```

Public id prefixes:

```text
R<n>       ResultId, materialized data
S<n>       SourceId, source/table artifact id
CHART<n>   chart artifact id
MAP<n>     map artifact id
GRAPH<n>   graph artifact id
```

A source id shown through `show_artifacts` is represented as an explicit table artifact:

```python
TableArtifactSpec(id="S1", label="...", source_id="S1")
```

There is no separate `TableView` or `render_table` tool.

## Parameters

```python
class ChoiceOption(BaseModel):
    id: str
    label: str


class ChoiceParameter(BaseModel):
    kind: Literal["choice"] = "choice"
    id: ParameterId
    label: str
    choices: list[ChoiceOption]


class NumberParameter(BaseModel):
    kind: Literal["number"] = "number"
    id: ParameterId
    label: str
    min: float
    max: float
    step: float
    default: float
    unit: str | None = None


ParameterSpec = ChoiceParameter | NumberParameter
```

For choice parameters, the first choice is the default. `OutputSpec` fills `default_selection` from parameter defaults and validates overrides.

`ParameterId` is semantic and agent-chosen. Reusing a parameter id means reusing the same control.

## Sources

```python
class FixedResultSource(BaseModel):
    kind: Literal["fixed"] = "fixed"
    id: SourceId
    result_id: ResultId


class ParameterizedSource(BaseModel):
    kind: Literal["parameterized"] = "parameterized"
    id: SourceId
    parameter_ids: list[ParameterId]
    db_alias: str
    query_template: str


SourceSpec = FixedResultSource | ParameterizedSource
```

`SourceSpec` is declarative. Runtime cache state belongs to `OutputStore`, not the source model.

A parameterized source renders `query_template` with validated source-local parameter values. The rendered SQL is stored on the resulting `ResultMetadata.query` so the query view is copy-paste executable.

Templates may declare that the source intentionally does not apply for the active selection:

```jinja
{% if metric != "revenue" %}
  {{ not_applicable("Revenue detail only applies when Metric is Revenue") }}
{% endif %}

SELECT ...
```

`not_applicable(...)` is semantic control flow, not a SQL error. The source is not materialized for that selection, and artifacts depending on it resolve to a not-applicable `UnavailableArtifact`.

## Results

Core stores metadata only:

```python
class ResultMetadata(BaseModel):
    id: ResultId
    db_alias: str
    query: str
    connector_type: Literal["sql", "property_graph"] = "sql"
    source_selection: Selection = Field(default_factory=dict)
    row_count: int | None = None
    columns: list[str] | None = None
    latency_seconds: float | None = None
```

Runtime payload stays in `toolhub/output_store.py`:

```python
@dataclass(frozen=True)
class ResultPayload:
    metadata: ResultMetadata
    df: pd.DataFrame | None = None
    graph: GraphView | None = None
```

`ResultPayload` is intentionally not in core because it carries runtime data.

## Artifacts

Artifacts are view-specific specs. There is no separate `ViewDef` layer.

```python
class TableArtifactSpec(BaseModel):
    kind: Literal["table"] = "table"
    id: ArtifactId
    label: str | None = None
    source_id: SourceId


class ChartArtifactSpec(BaseModel):
    kind: Literal["chart"] = "chart"
    id: ArtifactId
    label: str | None = None
    source_id: SourceId
    spec: dict[str, Any]


class MapArtifactSpec(BaseModel):
    kind: Literal["map"] = "map"
    id: ArtifactId
    label: str | None = None
    source_ids: list[SourceId]
    spec: dict[str, Any]


class GraphArtifactSpec(BaseModel):
    kind: Literal["graph"] = "graph"
    id: ArtifactId
    label: str | None = None
    source_ids: list[SourceId]
    spec: dict[str, Any]


ArtifactSpec = TableArtifactSpec | ChartArtifactSpec | MapArtifactSpec | GraphArtifactSpec
```

Use `source_id` / `source_ids`, not `source` / `sources`, for model fields that refer to output sources. Renderer-internal specs such as Vega-Lite or map layer grammar may still use their own vocabulary.

## Output spec

```python
class OutputSpec(BaseModel):
    parameters: list[ParameterSpec] = Field(default_factory=list)
    sources: list[SourceSpec] = Field(default_factory=list)
    artifacts: list[ArtifactSpec] = Field(default_factory=list)
    default_selection: Selection = Field(default_factory=dict)
```

Validation rules:

- parameter ids are unique;
- source ids are unique;
- artifact ids are unique;
- default selections refer to known parameters and valid values;
- parameterized sources reference known parameters;
- artifacts reference known sources.

## Runtime ownership

`OutputStore` owns side effects and mutable session state:

```text
- result/source/artifact id allocation
- materialized result metadata
- DataFrame / graph payload storage
- source cache
- parameter registry
- artifact registry
- lazy materialization for parameterized sources
```

`OutputResolver` owns resolution:

```text
OutputSpec + selection -> ResolvedOutput
```

It does not allocate ids or own caches; it asks `OutputStore` for payloads and turns artifact specs into resolved runtime artifacts.

## Agent-facing tools

- `run_query` returns a fixed source id `S<n>`.
- `create_parameterized_source` returns a parameterized source id `S<n>`.
- `render_chart` creates `ChartArtifactSpec` and returns `CHART<n>`.
- `render_map` creates `MapArtifactSpec` and returns `MAP<n>`.
- `render_graph` creates `GraphArtifactSpec` and returns `GRAPH<n>`.
- `show_artifacts` declares a list of source/artifact ids to include in the answer; source ids become `TableArtifactSpec` entries in the `OutputSpec`.

## Non-goals

- No compatibility aliases such as `ParameterDef`, `SourceDef`, `ViewDef`, `TableView`, `ChartView`, `MapView`, or `GraphViewSpec`.
- No `CardPlan` layer unless a future requirement introduces a real distinction between resolved artifacts and presentation cards.
- No core runtime payloads.
