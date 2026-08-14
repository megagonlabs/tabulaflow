# App-layer output render pipeline — plan

Status: target architecture, implemented for the clean output data model.

## Goal

The render pipeline is:

```text
selection -> resolve -> present -> swap
             ^^^^^^^    ^^^^^^^   ^^^^
             toolhub    app       app
             async      sync      per surface
```

`resolve` is the only step that touches `OutputStore`, connectors, source caches, or disk. After resolution, terminal and browser presenters render from data already in hand.

## Runtime resolved model

`toolhub/output_resolver.py` exposes the app-facing runtime contract:

```python
@dataclass(frozen=True)
class ResolvedTableArtifact:
    artifact_id: ArtifactId
    source_id: SourceId
    payload: ResultPayload
    label: str | None = None


@dataclass(frozen=True)
class ResolvedChartArtifact:
    artifact_id: ArtifactId
    source_id: SourceId
    payload: ResultPayload
    spec: dict[str, object]
    label: str | None = None


@dataclass(frozen=True)
class ResolvedMapArtifact:
    artifact_id: ArtifactId
    spec: dict[str, object]
    payload_by_source: Mapping[SourceId, ResultPayload]
    label: str | None = None


@dataclass(frozen=True)
class ResolvedGraphArtifact:
    artifact_id: ArtifactId
    graph: GraphView
    layout: str = "force"
    label: str | None = None


@dataclass(frozen=True)
class UnavailableArtifact:
    artifact_id: ArtifactId
    reason: str = "unavailable"
    label: str | None = None
    status: Literal["error", "not_applicable", "no_data"] = "error"


ResolvedArtifact = (
    ResolvedTableArtifact
    | ResolvedChartArtifact
    | ResolvedMapArtifact
    | ResolvedGraphArtifact
    | UnavailableArtifact
)


@dataclass(frozen=True)
class ResolvedOutput:
    selection: Selection
    artifacts: list[ResolvedArtifact]
```

This is the missing nominal type. Presenters dispatch on resolved artifact classes, not on core specs and not on a separate `CardPlan`.

## Why no CardPlan

A separate app-layer `CardPlan` would duplicate the resolved union:

```text
ResolvedTableArtifact -> TableViewPlan
ResolvedChartArtifact -> ChartViewPlan
ResolvedMapArtifact   -> MapViewPlan
ResolvedGraphArtifact -> GraphViewPlan
UnavailableArtifact   -> ErrorViewPlan
```

That extra layer adds naming and conversion without adding ownership. The clean contract is:

```text
core ArtifactSpec      = declared intent
resolved artifact      = runtime data ready for presentation
app presenter          = surface-specific rendering
```

Small app-local helper dataclasses are fine for presenter internals, but there is no broad output-planning hierarchy.

## Presenter responsibilities

Terminal presenter:

- `ResolvedTableArtifact` -> data/query card, plus graph view when the payload itself is a property-graph result.
- `ResolvedChartArtifact` -> chart/data/query card.
- `ResolvedMapArtifact` -> browser placeholder card.
- `ResolvedGraphArtifact` -> browser placeholder card.
- `UnavailableArtifact` -> visible info/error card.

Browser presenter:

- `ResolvedTableArtifact` -> table/query JSON payload, plus graph tab when the payload itself is a property-graph result.
- `ResolvedChartArtifact` -> chart/table/query JSON payload.
- `ResolvedMapArtifact` -> map JSON payload built from all source DataFrames.
- `ResolvedGraphArtifact` -> graph JSON payload from the already-materialized `GraphView`.
- `UnavailableArtifact(status="error")` -> visible error data card.
- `UnavailableArtifact(status="not_applicable")` -> neutral message card.
- `UnavailableArtifact(status="no_data")` -> neutral message card.

The surfaces differ only at presentation boundaries. They no longer duplicate source resolution or graph materialization.

## Graph materialization

Graph materialization belongs in `OutputResolver`.

Reason:

- it is runtime resolution of a declared graph artifact, not browser presentation;
- terminal and browser both need to know whether the graph is renderable;
- duplicating `materialize_graph_view` in both presenters caused drift and silent failures.

`ResolvedGraphArtifact` therefore carries a materialized `GraphView`. If materialization or size validation fails, the resolver returns `UnavailableArtifact(reason=...)` for that graph artifact.

## Availability and errors

Per-artifact unavailability:

- parameterized source template calls `not_applicable(reason)` for the selection;
- a source succeeds but returns no displayable payload;
- parameterized source cache/materialization failure;
- payload loading failure;
- missing DataFrame for a visual source;
- graph materialization failure;
- graph size validation failure.

For multi-source artifacts, any required source failure makes the whole artifact unavailable. Partial map/graph rendering is intentionally not implicit.

Whole-output `OutputResolutionError` remains for invalid requests/specs:

- unknown selected parameter;
- invalid parameter value;
- source references unknown parameter;
- artifact references unknown source;
- unsupported source/artifact type.

## Dataclass policy

`ResultPayload`, `ResolvedOutput`, and resolved artifact classes are frozen dataclasses. They are in-process runtime values, not serialized schemas. Core declarative models remain Pydantic models.

No `kind` discriminator is needed on resolved dataclasses unless they become serialized. Python class identity is the discriminator.

## Control projection

`ParameterSpec` is the answer-control model. The app should not wrap parameters in a duplicate `Control` dataclass hierarchy unless a future presenter needs fields that do not belong in core.

Surface-specific projection is still useful at the boundary:

- terminal currently supports `ChoiceParameter` navigation;
- browser-pane JSON projects `ParameterSpec` into `PaneChoiceControl | PaneNumberControl`;
- `NumberParameter` renders as a slider;
- number controls are part of the pane contract but are not drawn yet.

## Remaining cleanup opportunities

- Share more small presenter helpers for query lexer selection and table/chart payload construction.
- Decide whether terminal and browser selection state should be shared through one turn object or remain surface-local.
- Add browser/terminal support for `NumberParameter` controls.
