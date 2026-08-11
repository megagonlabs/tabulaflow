# Ultimate Output Model Plan

Status: target architecture plan. This intentionally ignores historical `Q*` / `QS*` / legacy artifact-model burden and describes the clean shape we want to converge to.

## Goal

The output model should be easy to explain:

```text
Output = Parameters + Sources + Artifacts

Parameters describe user-controlled values.
Sources produce materialized results.
Artifacts are views over sources.
Results are runtime materialized data.
```

The core invariant:

```text
Artifact -> Source -> Result
```

No artifact should directly depend on a materialized result. It should depend on a source. A source may always return the same result, or it may produce/cache different results for different selections.

## Core model

All pure, serializable output contracts live in `tabulaflow/core/outputs.py`.

### Id types

Use semantic ids consistently:

```python
ParameterId = str
SourceId = str
ArtifactId = str
ResultId = str
SelectionKey = str
SelectionValue = str | int | float | bool
```

Recommended public id prefixes:

```text
R<n>       ResultId, materialized data
S<n>       SourceId, data provider
CHART<n>   ArtifactId for chart artifacts
MAP<n>     ArtifactId for map artifacts
GRAPH<n>   ArtifactId for graph artifacts
```

A table does not need a separate `render_table` tool. A source id shown through `show_artifacts` is interpreted as an implicit table artifact:

```python
ArtifactSpec(id="S1", label="...", view=TableView(source="S1"))
```

## Parameters

Parameters are the only answer-control model. There should be no separate `AnswerPanel`, `ChoiceControl`, or slider-control model in chat.

```python
class ChoiceOption(BaseModel):
    id: str
    label: str


class ChoiceParameter(BaseModel):
    kind: Literal["choice"] = "choice"
    id: ParameterId
    label: str
    choices: list[ChoiceOption]
    default: str | None = None


class NumberParameter(BaseModel):
    kind: Literal["number"] = "number"
    id: ParameterId
    label: str
    min: float
    max: float
    step: float
    default: float
    display: Literal["slider", "input"] = "slider"
    unit: str | None = None


ParameterDef = ChoiceParameter | NumberParameter
```

Future parameter types can be added only when needed:

```text
DateParameter / DateRangeParameter
TextParameter
BooleanParameter
MultiSelectParameter
```

## Sources

Use a direct source union. Do not keep a separate `SourcePlan` union.

```python
SourceDef = FixedResultSource | ParameterizedSource
```

### Fixed result source

A fixed source always returns one materialized result.

```python
class FixedResultSource(BaseModel):
    kind: Literal["fixed"] = "fixed"
    id: SourceId
    result_id: ResultId
```

This replaces the current `ConstantResultPlan` wrapper shape.

### Parameterized source

A parameterized source produces/cache results under a source-local selection.

```python
class ParameterizedSource(BaseModel):
    kind: Literal["parameterized"] = "parameterized"
    id: SourceId
    parameter_ids: list[ParameterId]
    db_alias: str
    query_template: str
```

This replaces both current `ResultLookupPlan` and `QueryPlan` as core concepts.

The runtime decides whether to prewarm/cache all variants or lazily materialize selections. This is not a separate source kind.

## Results

A result is a materialized data product produced by a source.

Core stores only metadata:

```python
class ResultMetadata(BaseModel):
    id: ResultId
    db_alias: str
    query: str
    parameter_values: dict[ParameterId, SelectionValue] = Field(default_factory=dict)
    row_count: int | None = None
    columns: list[str] | None = None
    latency_seconds: float | None = None
```

Runtime payload stays outside core:

```python
class ResultPayload(BaseModel):
    metadata: ResultMetadata
    df: pd.DataFrame | None = None
    graph: GraphView | None = None
```

`ResultPayload` belongs in `toolhub`, not `core`, because it contains materialized runtime data.

## Artifacts and views

Artifacts are display units. Views declare how to render one or more sources.

```python
class TableView(BaseModel):
    kind: Literal["table"] = "table"
    source: SourceId


class ChartView(BaseModel):
    kind: Literal["chart"] = "chart"
    source: SourceId
    spec: dict[str, Any]


class MapView(BaseModel):
    kind: Literal["map"] = "map"
    sources: list[SourceId]
    spec: dict[str, Any]


class GraphViewSpec(BaseModel):
    kind: Literal["graph"] = "graph"
    sources: list[SourceId]
    spec: dict[str, Any]


ViewDef = TableView | ChartView | MapView | GraphViewSpec


class ArtifactSpec(BaseModel):
    id: ArtifactId
    label: str | None = None
    view: ViewDef
```

Use `GraphViewSpec` rather than `GraphArtifactView`: `GraphView` already names the materialized graph payload in `core.types`, while `GraphViewSpec` is the declarative view spec.

## Output spec

```python
class OutputSpec(BaseModel):
    parameters: list[ParameterDef] = Field(default_factory=list)
    sources: list[SourceDef] = Field(default_factory=list)
    artifacts: list[ArtifactSpec] = Field(default_factory=list)
    default_selection: dict[ParameterId, SelectionValue] = Field(default_factory=dict)
```

`OutputSpec.default_selection` should be completed from parameter defaults during validation.

## Runtime model

Runtime belongs in `toolhub`, not `core`.

Recommended files:

```text
tabulaflow/toolhub/output_store.py
  OutputStore
  ResultPayload
  private result storage/cache implementation

tabulaflow/toolhub/output_resolver.py
  OutputResolver
  ResolvedOutput
  ResolvedArtifact
```

### OutputStore responsibilities

`OutputStore` owns state and side effects:

```text
- result id allocation
- source id allocation
- artifact id allocation
- materialized result metadata
- materialized result payloads / DataFrames / graph payloads
- source cache
- artifact registry
- query execution for parameterized sources, when configured
```

Minimal public API target:

```python
class OutputStore:
    async def add_result(...) -> FixedResultSource
    async def add_parameterized_source(...) -> ParameterizedSource

    def get_source(source_id: SourceId) -> SourceDef

    async def get_metadata(result_id: ResultId) -> ResultMetadata
    async def get_payload(result_id: ResultId) -> ResultPayload

    def add_artifact(prefix: str, view: ViewDef, label: str | None = None) -> ArtifactSpec
    def get_artifact(artifact_id: ArtifactId) -> ArtifactSpec
```

### Source cache

Cache belongs to `OutputStore`, not `SourceDef`, not `OutputResolver`, and not a separate materializer object.

```python
_source_cache: dict[tuple[SourceId, SelectionKey], ResultId]
```

`SourceDef` should remain declarative. Runtime cache is session state.

### OutputResolver responsibilities

`OutputResolver` is the resolution algorithm:

```text
OutputSpec + selection -> ResolvedOutput
```

It should not own query execution, connector lookup, id allocation, or caches.

For fixed sources:

```python
metadata = await output_store.get_metadata(source.result_id)
```

For parameterized sources:

```python
metadata = await output_store.resolve_parameterized_source(source, projected_selection)
```

This method can check cache and materialize the query if needed.

## Agent-facing tools

### `run_query`

`run_query` executes immediately and returns a source id:

```text
[source_id=S1]
```

Internally it creates:

```text
R1 = materialized result
S1 = FixedResultSource(result_id="R1")
```

### `create_parameterized_source`

Add an agent-facing tool that creates a parameterized source:

```python
create_parameterized_source(
    db_alias="workspace",
    parameters=[...],
    query_template="...",
    max_warm_variants=10,
)
```

It returns:

```text
[source_id=S2]
```

and its tool metadata should include the `ParameterDef`s and `SourceDef`, so chat output construction can include them in `OutputSpec`.

### `run_query_for_each_combination`

Eventually replace or implement as a wrapper over `create_parameterized_source`.

### `render_chart`, `render_map`, `render_graph`

These accept source ids and create artifact ids:

```text
render_chart(source_id="S1") -> CHART1
render_map(...) -> MAP1
render_graph(...) -> GRAPH1
```

### `show_artifacts`

Accepts source ids and artifact ids:

```text
S<n>                 implicit table artifact
CHART<n> / MAP<n> / GRAPH<n> explicit artifacts
```

No `render_table` tool is needed.

## Handling choice + numeric slider examples

For a question like:

> Show top customers; let me choose ranking metric and adjust minimum spend.

Use shared parameters:

```python
parameters=[
    ChoiceParameter(id="metric", ...),
    NumberParameter(id="min_spend", ...),
]
```

Use a single `ParameterizedSource`:

```python
ParameterizedSource(
    id="S1",
    parameter_ids=["metric", "min_spend"],
    db_alias="workspace",
    query_template="...",
)
```

The runtime uses one code path:

```text
selection -> canonical selection key -> cache -> materialize if miss -> ResultMetadata
```

If all source parameters are finite choices and the total combinations are small enough, prewarm all variants. If numeric/range/text parameters are present, prewarm only default and lazily materialize other selections.

## Deferred design choices

### 1. Query template binding semantics

We still need to choose how `ParameterizedSource.query_template` handles parameters.

Options:

```text
A. Jinja for all parameters
B. Bound scalar parameters only
C. Hybrid: whitelisted structural bindings + bound scalar parameters
```

Preferred long-term: hybrid.

Example:

```text
metric -> structural binding from whitelist
min_spend -> bound scalar value
```

Do not allow arbitrary raw string interpolation for scalar values in the final design.

### 2. Structural bindings model

For finite choices that change SQL structure, e.g. ranking by revenue/profit/order_count, we need a safe representation.

Possible future shape:

```python
structural_bindings={
    "metric_expr": {
        "parameter": "metric",
        "choices": {
            "revenue": "revenue_usd",
            "profit": "profit_usd",
            "order_count": "order_count",
        },
    }
}
```

Defer until `ParameterizedSource` execution exists.

### 3. Cache warming policy

Initial policy:

```text
if all parameters are finite choices and combinations <= the runtime warm-cache limit:
    prewarm all variants
else:
    prewarm default only
```

Deferred details:

```text
- whether warming happens at source creation or first resolution
- how to report warming failures
```

### 4. Source id/result id public formatting

Target prefixes:

```text
R<n> results
S<n> sources
CHART<n>/MAP<n>/GRAPH<n> artifacts
```

Deferred:

```text
- whether direct result ids should ever be shown to the agent
- whether result ids should appear in query/data tabs for debugging
```

### 5. Result failure logging

Failed executions should not become materialized results. If we need durable failure introspection, add a separate query/execution log.

Do not put failures into `OutputSpec` or `ResultMetadata`.

### 6. Graph payload storage

Current minimal runtime shape:

```python
_StoredResult(graph: GraphView | None)
```

This is acceptable because native graph extraction is capped.

Future option:

```text
graph payload store keyed by ResultId
```

Only add if graph payloads become large enough to need spill/dedup.

### 7. Native graph extraction location

Native graph database result extraction belongs in the graph connector implementation. The connector converts database-native nodes/relationships/paths into canonical `GraphView`.

Declared graph artifacts from tabular data are different: they are view materialization and belong in toolhub/app rendering logic, not connector code.

## Migration steps from current state

1. Replace current `SourceDef + SourcePlan` shape with `FixedResultSource | ParameterizedSource`.
2. Replace `ConstantResultPlan` with `FixedResultSource.result_id`.
3. Replace `ResultLookupPlan` and `QueryPlan` with `ParameterizedSource` plus runtime source cache.
4. Add `OutputStore.resolve_parameterized_source(...)`.
5. Add `create_parameterized_source` tool.
6. Reimplement `run_query_for_each_combination` as a wrapper or compatibility path over `create_parameterized_source`.
7. Update `show_artifacts` and render tools to consume only source/artifact ids from the new model.
8. Remove stale plan classes and tests.
