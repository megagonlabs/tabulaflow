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

For choice parameters, the first choice is the default. Put the preferred initial reading first.

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

`query_template` is a Jinja template rendered with validated source-local parameter values. For the initial supported parameter set:

```text
ChoiceParameter -> fixed allowed ids, suitable for Jinja conditionals / structural branches
NumberParameter -> finite numeric values, suitable for direct unquoted numeric literals
```

The rendered SQL is the executed SQL and is stored in `ResultMetadata.query`, so the query view shows copy-paste executable SQL for the active selection.

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

## Parameter registration

`ParameterId` is semantic and agent-chosen, not store-assigned. It should be globally unique within one `OutputStore` / chat session.

```text
same ParameterId -> same control
different meaning -> different ParameterId
```

`OutputStore` should register parameter definitions and reject conflicting reuse:

```python
class OutputStore:
    _parameters: dict[ParameterId, ParameterDef]

    def register_parameter(self, parameter: ParameterDef) -> None:
        existing = self._parameters.get(parameter.id)
        if existing is None:
            self._parameters[parameter.id] = parameter
        elif existing != parameter:
            raise ValueError(f"parameter {parameter.id!r} already exists with a different definition")
```

The store assigns opaque ids for runtime entities:

```text
ResultId
SourceId
ArtifactId
```

The agent assigns semantic ids for parameters:

```text
metric
period
min_spend
region
```

This lets multiple sources share one UI control by using the same `ParameterId`.

Do **not** add a separate agent-facing `register_parameter` tool. Parameter registration should happen as part of source creation.

The source-creation tool should accept full parameter definitions:

```python
create_parameterized_source(
    db_alias="workspace",
    parameters=[
        ChoiceParameter(id="metric", ...),
        NumberParameter(id="min_spend", ...),
    ],
    query_template="...",
)
```

The tool/store then:

```text
1. registers/validates parameter definitions;
2. creates a ParameterizedSource with parameter_ids=[...];
3. optionally prewarms cache;
4. returns source id S<n>.
```

`OutputSpec.parameters` remains necessary because `OutputSpec` is a self-contained snapshot for one answer. It should be assembled from the registered parameters required by the selected sources/artifacts.

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
    async def add_fixed_result_source(...) -> FixedResultSource
    def add_parameterized_source(...) -> ParameterizedSource
    async def cache_parameterized_result(...) -> ResultId
    async def resolve_source(...) -> ResultMetadata

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

The tool should register parameters in `OutputStore`; it should not require a prior parameter-registration call.

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

`show_artifacts` should not define controls/dimensions. It only selects and labels source/artifact ids. The output spec is assembled by collecting dependencies from the store:

```text
selected source/artifact refs
-> ArtifactSpec(s)
-> SourceDef(s)
-> ParameterDef(s)
-> OutputSpec
```

Therefore the final `show_artifacts` API should not have a `dimensions` argument. Controls are defined when parameterized sources are created.

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

If all source parameters are finite choices and the total combinations are small enough, prewarm all variants. If numeric parameters are present, prewarm only default and lazily materialize other selections.

## Query template semantics

Decision: use Jinja rendering for the currently supported parameter types (`ChoiceParameter` and `NumberParameter`).

Runtime rules:

- Validate every selected parameter value before rendering.
- `ChoiceParameter` values must be one of the declared option ids.
- `NumberParameter` values must be numeric, not boolean, finite, and within min/max.
- Render `ParameterizedSource.query_template` with the validated source-local selection.
- Execute the rendered query.
- Store the rendered query in `ResultMetadata.query`.
- Store selected source-local values in `ResultMetadata.parameter_values`.

Agent/template conventions:

- Use `ChoiceParameter` mainly for Jinja branching and fixed structural alternatives.
- Use `NumberParameter` directly as an unquoted numeric literal.
- Do not quote `NumberParameter` values in SQL templates.
- Do not add text/date/list parameters to raw Jinja rendering without a separate safe literalization design.

Example:

```jinja
SELECT *
FROM customers
WHERE spend >= {{ min_spend }}
ORDER BY
{% if metric == "revenue" %} revenue_usd
{% elif metric == "profit" %} profit_usd
{% elif metric == "order_count" %} order_count
{% endif %} DESC
```

With `metric="profit"` and `min_spend=50000`, the materialized `ResultMetadata.query` is the rendered SQL for that selection, not a placeholder query plus a separate parameter bag.

## Not-applicable handling

We do not add `ArtifactSpec.applies_when` in the minimal core model.

Artifacts always exist in the output. Applicability is handled at source-resolution time.

For intentional source-level non-applicability, support an explicit Jinja helper in `ParameterizedSource.query_template`:

```jinja
{% if quarter != "q3" %}
  {{ not_applicable("only applies when Quarter = Q3") }}
{% endif %}

SELECT ...
```

The helper should raise a specific runtime exception, not rely on accidental Jinja/render/SQL errors:

```python
class SourceNotApplicable(Exception):
    reason: str
```

Runtime behavior:

```text
1. OutputResolver resolves each artifact independently.
2. Source materialization can return metadata or raise SourceNotApplicable.
3. A non-applicable source makes that artifact unavailable for the active selection.
4. Other artifacts still resolve/render.
```

Generic template errors or SQL execution failures are bugs/errors, not not-applicable signals.

This preserves expressibility without adding a separate artifact predicate model. If only one artifact should be conditional but its source is generally applicable, the agent can create a separate parameterized source for that artifact.

Eventually `ResolvedOutput` should represent unavailable artifacts explicitly, for example:

```python
ResolvedArtifact = AvailableArtifact | UnavailableArtifact
```

or an equivalent minimal runtime shape. The core `ArtifactSpec` should remain predicate-free for now.

## Deferred design choices

### 1. Future non-numeric scalar parameters

Raw Jinja rendering is not safe enough for arbitrary strings, dates, arrays, or multi-select values. Before adding parameter types such as:

```text
TextParameter
DateParameter / DateRangeParameter
MultiSelectParameter
```

we need one of:

```text
- dialect-aware safe literalization;
- bound-parameter execution plus a query+parameters display;
- explicit restrictions preventing those params from being interpolated raw.
```

### 2. Structural bindings model

For finite choices that change SQL structure, e.g. ranking by revenue/profit/order_count, Jinja conditionals over `ChoiceParameter` ids are acceptable for now. A more structured whitelist model may be useful later if we want to validate or transform structural SQL branches programmatically.

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
6. Update `show_artifacts` and render tools to consume only source/artifact ids from the new model.
7. Remove stale plan classes and tests.
