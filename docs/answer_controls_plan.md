# Answer Controls Plan

Status: active implementation plan; ignores earlier interpretation-panel plans.

## Current implementation progress

Implemented on `dev` so far:

- Answer controls are first-class in the chat result model:
  - `AnswerControl = ChoiceControl | SliderControl`.
  - `AnswerPanel.controls` exists.
  - `AnswerPanel.default_selection` supports typed values (`str | int | float | bool`).
- The TUI result widget reads choice controls from `panel.controls` instead of treating `dimensions` as the primary UI model.
  Slider controls are accepted by the model but are not yet interactive.
- Query history now has source resolution primitives:
  - `source_id="Q1"`
  - `source_id="QS1"`
  - `ResolvedRecordRef`
  - `ResolvedQueryRecord`
  - `SourceNotApplicable`
  - `QueryHistory.resolve_source_id(...)`
  - `QueryHistory.resolve_query_record(...)`
- Chart artifacts are source-backed:
  - `ChartArtifact.source_id: str`
  - `render_chart(source_id=...)` accepts `Q*` and `QS*`.
  - For `QS*`, chart validation checks every source variant and reports all failures by selection key, not internal variant record id.
  - `show_artifacts` treats a chart backed by a `QS*` source as varying over that family.
- Chat results now carry only logical artifacts:
  - `ChatResult.artifacts` is the source-backed artifact graph for the turn.
  - `TableArtifact` models implicit `Q*` / `QS*` table cards; there is intentionally no `render_table`.
  - `ChartArtifact` models source-backed charts.
  - `MapArtifact` carries lightweight `map_spec`; `GraphArtifact` remains fixed by `graph_id` for now.
  - `ChatAgent.artifact_resolver.resolve(result, selection=None)` resolves default or active selections.
  - Resolved payloads are separate `Resolved*Artifact` models, plus `ArtifactPlaceholder` for not-applicable selections.
- Source ids are plain `Q*` / `QS*` strings; no separate `ArtifactSource` wrapper.
- `ArtifactResolver` now only materializes logical chat artifacts; query-record payload lookup lives in `QueryHistory`, and `show_artifacts` refs are converted to logical artifacts during chat-result construction.
- The tool-facing `show_artifacts` item is named `ArtifactRef`, because it is only an id+label reference.
- Query-history artifact registry entries are named `StoredChartArtifact`, `StoredMapArtifact`, and `StoredGraphArtifact` to distinguish session storage from answer-level logical artifacts.
- The browser pane supports finite choice controls via live session-backed resolution.

In progress / next cleanup:

- Continue hardening the artifact definition model before adding lazy/server-side sliders:
  - move toward one shared lightweight/spec-backed `ArtifactDef` shape when graph can also be spec-backed;
  - refactor graph from stored materialized `GraphView` toward a source/spec-backed definition, if feasible.
- Design true server-side parameterized sources for sliders after the shared artifact-definition shape is settled; current sliders are model/UI-safe but do not rerun or parameterize queries.

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

The long-term model should not prebuild a full artifact copy for every selection. Instead, selection should resolve sources, and artifacts should derive from those sources.

```text
Turn
└── controls and active selection
    └── logical sources
        └── concrete query records/results
            └── artifact views: table, chart, map, graph
```

A chart/map/graph should be able to reference a logical source such as a fixed result, a query family, or eventually a parameterized query. The active control selection resolves that logical source to concrete data.

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

- Include `AnswerPanel` and logical `ChatResult.artifacts` in the pane turn payload.
- Resolve the default selection and finite choice changes through the live session/runtime.
- Update table/chart/map/graph cards when choice controls change.
- Keep this phase to precomputed `Q*` / `QS*` sources; do not add lazy query execution yet.

This phase should validate the public runtime API:

```python
await chat_agent.artifact_resolver.resolve(result, selection)
```

### Phase 5 — Shared artifact-definition model

After browser-pane finite controls prove the runtime-resolution model, consolidate artifact definitions before adding parameterized/lazy sources.

Goals:

- Rename the tool-facing `show_artifacts.Artifact` to `ArtifactRef` because it is only an id+label reference.
- Clarify stored session artifacts versus answer-level logical artifacts, e.g. `StoredChartArtifact` vs `ChartArtifact`, if separate classes still exist.
- Prefer one shared lightweight/spec-backed `ArtifactDef` family once all artifact types can fit it.
- Carry lightweight specs in logical artifacts where appropriate, especially map specs.
- Refactor graph artifacts toward source/spec-backed definitions rather than stored materialized `GraphView`, if feasible.
- Keep `ResolvedArtifact` payloads in the chat/frontend contract; do not move resolved DataFrames or graph payloads into the shared definition layer.

Target long-term taxonomy:

```text
ArtifactRef      # tool input: id + label
ArtifactDef      # logical/spec-backed artifact definition
ResolvedArtifact # materialized payload for rendering
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
