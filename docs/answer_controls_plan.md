# Answer Controls Plan

Status: active implementation plan; ignores earlier interpretation-panel plans. The goal is now the clean end-state architecture, even when that means breaking from repo history rather than preserving old `Q*` / `QS*` / `ArtifactDef` shapes.

## Architecture reset

We are intentionally aiming for the ultimate clean output model instead of incrementally polishing the historical interpretation-panel implementation.

The target core contract is:

```text
OutputSpec = Parameters + Sources + Artifacts + default selection

ParameterDef  = user-adjustable value, with UI/display hints
SourceDef     = declarative, selection-dependent provider of results
SourcePlan    = how a source obtains a result
ArtifactSpec  = display intent; a view over one or more sources
ResultRecord  = metadata/provenance for one materialized query result
```

The key dependency chain is:

```text
selection -> sources -> result records -> artifact views
```

The clean separation is:

- `core.outputs` defines only pure, serializable specifications and metadata.
- Runtime state such as caches, connector access, stored DataFrames, and query execution lives outside `core`.
- The current runtime artifact models are historical compatibility only and should be migrated away, not treated as the target design.

## Current implementation progress

Implemented on `dev` so far:

- `core.outputs` now contains the clean target output-spec model:
  - `OutputSpec`, `ParameterDef`, `SourceDef`, `SourcePlan`, `ArtifactSpec`, `ViewDef`, and `ResultRecord`;
  - semantic id aliases (`ParameterId`, `SourceId`, `ArtifactId`, `ResultId`, `SelectionKey`);
  - source plans split into `ConstantResultPlan`, `ResultLookupPlan`, and `QueryPlan`;
  - legacy runtime artifact definitions have been moved aside as compatibility scaffolding.

- Chat results now carry `ChatResult.output: OutputSpec` as the live output model.
- TUI and browser-pane controls read from `OutputSpec.parameters` / `OutputSpec.default_selection`; the old `AnswerPanel` / `ChoiceControl` chat model has been removed.
- Query history now has source resolution primitives:
  - `source_id="Q1"`
  - `source_id="QS1"`
  - `ResolvedRecordRef`
  - `ResolvedQueryRecord`
  - `SourceNotApplicable`
  - `QueryHistory.resolve_source_id(...)`
  - `QueryHistory.resolve_query_record(...)`
- Chart artifacts are source-backed:
  - chart artifact specs reference a source through `ChartView.source`;
  - `render_chart(source_id=...)` accepts `Q*` and `QS*`.
  - For `QS*`, chart validation checks every source variant and reports all failures by selection key, not internal variant record id.
  - `show_artifacts` treats a chart backed by a `QS*` source as varying over that family.
- Chat output resolution now goes through `OutputResolver`; app and pane renderers consume `ResolvedOutput` directly.
- Source ids are plain `Q*` / `QS*` strings; no separate `ArtifactSource` wrapper.
- `show_artifacts` refs are converted to `OutputSpec` during chat-result construction.
- The tool-facing `show_artifacts` item is named `ArtifactRef`, because it is only an id+label reference.
- Query-history artifact registry entries now store clean `ArtifactSpec` / `ViewDef` models.
- Stored graph artifacts now keep normalized graph specs rather than materialized `GraphView` payloads.
- The browser pane supports finite choice controls via live session-backed resolution.

In progress / next cleanup:

- Migrate runtime code toward the new `core.outputs` model:
  - finish replacing the temporary display `Resolved*Artifact` payloads in tests/debug helpers with a clean renderer-facing model.
- Design true server-side parameterized sources for sliders after the clean source/result runtime boundary is in place; current sliders are model/UI-safe but do not rerun or parameterize queries.

## Product thesis

The control panel should become a first-class answer-level capability, but it should render only when useful. Most answers still have no controls.

The intended mental model is:

```text
answer-level controls -> selected/parameterized sources -> artifacts -> views
```

This is similar to BI dashboards, where filters/dropdowns/sliders drive tables, charts, and maps. The distinctive feature here is that controls can be generated from natural-language semantics, especially ambiguity in the user question.

## Existing product analogs

Traditional BI dashboards commonly have controls that update multiple visuals:

- date ranges
- region/product dropdowns
- metric selectors
- top-N controls
- threshold sliders

These controls are usually manually authored by an analyst or inferred from schema/data types. They are mostly for exploration and parameterization, not ambiguity resolution.

Our app's control panel should support both:

1. **Interpretation controls** — expose consequential ambiguity in the question.
   - Example: "top customers" -> revenue vs order count vs profit.
   - Example: "recent orders" -> last 30 days vs last quarter.
   - Example: "tall players" -> height threshold.

2. **Exploration controls** — let the user interactively refine a clear answer.
   - Example: region dropdown.
   - Example: date range.
   - Example: top-N slider.

Initial automatic use should prioritize interpretation controls. Exploration controls should appear when the user asks for interactivity, or when a small number of controls clearly improves the answer.

## Relationship to Vega-Lite interactions

Answer-level controls and chart-local interactions are different layers.

Use the answer control panel for controls that are:

- global across multiple artifacts;
- semantic/interpretation-level;
- query-affecting;
- shared by tables, charts, maps, and graphs.

Use Vega-Lite interactions for controls that are:

- local to one chart;
- visual-only;
- hover/zoom/brush/legend style interactions;
- not needed by other artifacts.

Rule of thumb:

```text
global / semantic / query-affecting -> answer controls
local / visual / chart-only         -> Vega-Lite
```

## Target architecture

The long-term model should not prebuild a full artifact copy for every selection. Instead, the answer declares parameters, sources, and artifact views. The active selection resolves sources to concrete results, and artifacts render views over those results.

```text
OutputSpec
├── parameters
├── sources
│   └── source plans
├── artifacts
│   └── table/chart/map/graph views over source ids
└── default_selection

Runtime
└── active selection
    └── source resolver
        └── result records + stored payloads
            └── artifact renderers
```

A chart/map/graph should reference source ids, not concrete DataFrames. A source may point to a fixed existing result, a precomputed lookup of existing results, or a query plan that can materialize a new result for the active selection.

The core source-plan split is intentionally intuitive:

- `ConstantResultPlan` — always returns one already-materialized result.
- `ResultLookupPlan` — maps normalized source-local selections to already-materialized results.
- `QueryPlan` — can produce a new result by executing a parameterized query.

Concrete query provenance belongs on `ResultRecord`, not duplicated into plans that simply reference existing results.

## Controls

The panel should generalize from finite dimensions to typed controls.

Initial control types:

- choice control
- slider control

Future possible controls:

- date range
- numeric range
- text search
- multi-select
- toggle

Selection state should support typed values, not only strings.

```text
selection = {
  "ranking": "net_revenue",
  "height_threshold_cm": 200,
}
```

## Sliders

Sliders make sense for threshold-type questions:

- tall players
- expensive houses
- recent/high-value transactions
- nearby restaurants
- large customers

A slider should usually represent a runtime parameter, not a precomputed list of every possible value.

Important distinction, deferred for later detailed design:

1. **Client-side slider**
   - frontend already has data;
   - slider filters/transforms locally;
   - good for small/static data and standalone pane exports.

2. **Server-side slider**
   - slider value changes a query parameter;
   - backend/session runs or fetches the result;
   - better for large data, aggregation, joins, and database semantics.

The primary semantic model should be server-side. Client-side behavior can be an optimization for simple cases.

## Browser pane

The browser pane should eventually support the same answer-level controls as the TUI.

It needs to render:

- controls;
- active selection;
- artifacts dependent on that selection;
- chart/map/graph/table updates when selection changes.

There are two likely modes:

1. Static/precomputed bundle for finite choice controls.
2. Session-backed API for lazy/server-side parameterized controls.

Detailed server-vs-client mechanics are intentionally deferred.

## Phased plan

### Phase 1 — First-class control model

Define the answer-level model for controls and selection state.

Goals:

- Generalize from `dimensions` to controls, or introduce controls alongside dimensions during migration.
- Represent choice controls and slider controls.
- Make empty controls the normal no-panel case.
- Keep controls answer-level, not artifact-local.
- Preserve current choice-only panel behavior during migration.

Open design points:

- Whether to rename `dimensions` immediately or bridge with compatibility.
- Exact Pydantic model shape for typed selection values.
- Whether `ChatResult.panel` becomes `ChatResult.controls` plus state, or whether `panel` remains as a wrapper.

### Phase 2 — Source resolution

Introduce logical sources and a resolver:

```text
control selection + source id -> concrete record/result
```

Sources may include:

- fixed query records;
- query families;
- later, parameterized query definitions.

Artifacts should reference sources rather than embedding only one selected DataFrame.

### Phase 3 — TUI dynamic controls

Make the TUI follow the target chain:

```text
control state -> resolved sources -> artifacts -> views
```

Changing a control should rebuild the relevant cards/views while preserving user context where possible.

### Phase 4 — Browser pane finite controls

Extend the browser pane payload and frontend to support answer-level controls for already-materialized finite choices.

Goals:

- Include `OutputSpec.parameters` and `OutputSpec.artifacts` in the pane turn payload.
- Resolve the default selection and finite choice changes through the live session/runtime.
- Update table/chart/map/graph cards when choice controls change.
- Keep this phase to precomputed `Q*` / `QS*` sources; do not add lazy query execution yet.

This phase should validate the public runtime API:

```python
await OutputResolver(result_store).resolve(result.output, selection)
```

### Phase 5 — Shared artifact-definition model

After browser-pane finite controls prove the runtime-resolution model, consolidate artifact definitions before adding parameterized/lazy sources.

Goals:

- Keep the tool-facing `ArtifactRef` separate because it is only an id+label reference.
- Use `OutputSpec`, `ArtifactSpec`, and `ViewDef` as the chat output contract.
- Keep graph/map/chart specs lightweight; materialize render payloads through app/pane renderers consuming `ResolvedOutput`.
- Treat current `Resolved*Artifact` payloads as temporary display compatibility models; do not move resolved DataFrames or graph payloads into `core.outputs`.

Target long-term taxonomy:

```text
ArtifactRef      # tool input: id + label
OutputSpec       # declarative output contract
ResolvedOutput   # source-result resolution
Display payloads # renderer compatibility layer, temporary
```

### Phase 6 — Parameterized/lazy results

Support true runtime parameters, especially sliders.

Add caching by normalized selection/source definition, so repeated selections reuse stored results.

Server-side vs client-side slider execution should be decided in detail here.

### Phase 7 — Agent/tool policy

Update tool and system-prompt guidance.

Policy:

- use controls automatically for consequential ambiguity;
- use exploration controls when requested or clearly valuable;
- avoid turning simple answers into dashboards;
- avoid adding every possible schema-derived filter.

### Phase 8 — Cleanup

After the new model is stable:

- remove compatibility paths;
- settle naming;
- consolidate tests around the dynamic dependency chain;
- consider renaming `QueryHistory` if its role has clearly become an artifact/source registry.
