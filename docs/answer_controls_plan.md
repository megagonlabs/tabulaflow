# Answer Controls Plan

Status: active implementation plan; ignores earlier interpretation-panel plans.

## Current implementation progress

Implemented on `dev` so far:

- Answer controls are first-class in the chat result model:
  - `AnswerControl = ChoiceControl | SliderControl`.
  - `ChatResultPanel.controls` exists.
  - Legacy `ChatResultPanel.dimensions` still exists as a compatibility bridge for current tools.
  - `ChatResultCombination.selection` supports typed values (`str | int | float | bool`).
- The TUI result widget reads choice controls from `panel.controls` instead of treating `dimensions` as the primary UI model.
  Slider controls are accepted by the model but are not yet interactive.
- Query history now has source resolution primitives:
  - `ArtifactSource(kind="record", id="Q1")`
  - `ArtifactSource(kind="family", id="QS1")`
  - `ResolvedRecordRef`
  - `SourceNotApplicable`
  - `QueryHistory.resolve_artifact_source(...)`
- Chart artifacts are source-backed:
  - `ChartArtifact.source: ArtifactSource`
  - `render_chart(source_id=...)` accepts `Q*` and `QS*`.
  - For `QS*`, chart validation checks every source variant and reports all failures by selection key, not internal variant record id.
  - `show_artifacts` treats a chart backed by a `QS*` source as varying over that family.
- Current chart/table source resolution still happens while building `ChatResult` in the chat layer. This is transitional: `ChatResult` remains display-ready, not an unresolved artifact graph.

In progress / next cleanup:

- Rename resolved table payloads from `ChatResultRecord`/`kind="record"` to `ChatResultTable`/`kind="table"`.
  This preserves agent ergonomics: there is intentionally no `render_table`; `Q*` and `QS*` remain directly showable as implicit table cards.
- After that cleanup, the next architectural step is to stop resolving all artifacts in the chat layer and move toward frontend/runtime resolution of unresolved artifact definitions under the active selection.

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

### Phase 4 — Parameterized/lazy results

Support true runtime parameters, especially sliders.

Add caching by normalized selection/source definition, so repeated selections reuse stored results.

Server-side vs client-side slider execution should be decided in detail here.

### Phase 5 — Browser pane controls

Extend the browser pane payload and frontend to support answer-level controls.

Start with precomputed finite choices if simpler, then add session-backed lazy controls.

### Phase 6 — Agent/tool policy

Update tool and system-prompt guidance.

Policy:

- use controls automatically for consequential ambiguity;
- use exploration controls when requested or clearly valuable;
- avoid turning simple answers into dashboards;
- avoid adding every possible schema-derived filter.

### Phase 7 — Cleanup

After the new model is stable:

- remove compatibility paths;
- settle naming;
- consolidate tests around the dynamic dependency chain;
- consider renaming `QueryHistory` if its role has clearly become an artifact/source registry.
