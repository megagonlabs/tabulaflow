# App-layer output render pipeline — plan

Status: target architecture plan. This is the app-layer sequel to
[`ultimate_output_model_plan.md`](./ultimate_output_model_plan.md), which specifies the
clean shape of `core/outputs.py` and the `toolhub` runtime but stops at `ResolvedOutput`.
Everything below the resolver — turning a resolved output into something a user sees, and
turning a user gesture back into a selection — is currently unspecified and has grown two
independent implementations. This plan describes the shape to converge to. It intentionally
ignores historical burden.

Scope note: `NumberParameter` has no control on either surface today. That gap is a
*symptom* of the diagnosis below, not a separate work item; Phase 4 creates the seam it
needs, but actually drawing sliders is out of scope here.

## Goal

The app layer should express the render pipeline exactly once:

```text
selection -> resolve -> plan -> present -> swap
             ^^^^^^^    ^^^^    ^^^^^^^
             toolhub    app     app, per surface
```

Only the last step may differ per surface. Today the middle step is duplicated and the
first and last are each hand-rolled twice.

## Diagnosis (current state)

### One pipeline, two copies

Two functions do the same traversal against different output types:

| | terminal | browser |
|---|---|---|
| entry | `display.py:420` `build_resolved_output_card_views` | `pane/cards.py:169` `render_resolved_output` |
| walks | `resolved_output.artifacts` | `resolved_output.artifacts` |
| dispatches on | `TableView \| ChartView \| MapView \| GraphViewSpec` | same four |
| fetches | `store.get_payload(metadata.id)` | `store.get_payload(metadata.id)` |
| produces | `CardGroup` / `ViewItem` | `PaneCard` + `<card_id>.data.json` |

Adding a fifth view kind means editing both, and nothing makes you. They have **already
diverged**: the terminal's `MapView` branch never touches the store at all (it renders an
"open in browser" placeholder from `view.spec`, `display.py:452`), and its `GraphViewSpec`
branch fetches payloads and calls `materialize_graph_view` purely to validate, then discards
the graph and renders a placeholder (`display.py:460`).

That divergence is **legitimate** — a terminal cannot draw a map — and any unification
that erases it is wrong. The problem is not that the surfaces differ; it is that they differ
in the middle of a duplicated traversal rather than at a declared presenter boundary.

### Root cause: the missing type

`ResolvedOutput` carries `ResultMetadata` — ids, row counts, column names — and no data.
That is the right contract for a serializable resolver result and should not change. But it
means every consumer must independently perform the same two steps: `isinstance`-dispatch on
the view kind, then `await store.get_payload(...)` to obtain the DataFrame.

There is no type that represents "an artifact, dispatched, with its data attached". The
absence shows up directly in the code:

- `pane/cards.py:53-76` declares three structural `Protocol`s — `ResultMetadataLike`,
  `MapArtifactLike`, `GraphArtifactLike` — that exist only to name a shape that has no class.
- `pane/cards.py` then constructs four `SimpleNamespace(...)` objects (lines 184, 197, 213,
  228) to satisfy those Protocols.

Hand-written structural Protocols over `SimpleNamespace` are the signature of a missing
nominal type. Introduce it and all seven of those constructs delete themselves.

### Control projection is duplicated too

Both surfaces independently project `OutputSpec.parameters` down to drawable controls by
filtering `isinstance(parameter, ChoiceParameter)`:

- `tui.py:95` `_pane_panel` → the `PanePanel` JSON payload
- `widgets.py:1743` `_choice_controls_from_result` → the Textual panel

and the browser filters a *third* time in JS (`pane.js:76`, `control.kind === 'choice'`),
against a `PaneChoiceControl` TypedDict (`pane/types.py:25`) that can only express choices.

This is why number parameters are half-implemented. Adding a slider today means touching a
TypedDict, two Python projections, a JS filter, and two renderers, with no single place that
fails loudly if you miss one.

### Selection lifecycle is duplicated too

Both surfaces solve "supersede the in-flight request" independently:

- terminal: mutate `_applied_selection` (`widgets.py:1785`), then
  `run_worker(..., exclusive=True)` (`widgets.py:1787`)
- browser: mutate `state.selection`, then guard with a monotonic `state.resolveSeq` plus a
  `sameSelection` recheck on arrival (`pane.js:98`, `pane.js:119`)

Both are correct. Neither is shared. The *policy* (last write wins, drop superseded
responses, preserve card/view cursor across a swap) is a property of the pipeline, not of a
widget toolkit.

### Defect: `/resolve` runs on a foreign event loop

`server.py:210` calls `asyncio.run(pane.resolve_turn(...))` inside a
`ThreadingHTTPServer` handler thread — a **fresh event loop per request**. The `OutputStore`
it reaches into holds connectors whose `ThrottledEngine` owns `asyncio.Semaphore` and
`asyncio.Lock` objects created on the TUI's loop (`sql_conn.py:1012-1014`), and, for async
drivers, a connection pool bound to that loop.

It works today because the uncontended `Semaphore.acquire()` fast path never creates a
future and DuckDB is a sync driver. The reachable failure paths are not exotic:

- a cache miss goes to `connector.run_query_async` (`output_store.py:325`);
- a cache *hit* whose frame was evicted from the 5-entry LRU re-reads through the spill
  connector (`output_store.py:94`);
- two concurrent resolves, or any async-driver DB (Snowflake, Postgres), contend the
  semaphore.

This is the only item in this document that is a defect rather than a design preference.

### Vestigial lazy imports

Five call sites import `OutputResolver` / `OutputStore` / view classes inside function
bodies (`display.py:426-431`, `pane/cards.py:171-174`, `tui.py:1141-1142`,
`widgets.py:1713-1714`, `server.py:556`), and two public functions are typed
`(resolved_output: object, output_store: object)` with an `assert isinstance(...)` in the
body to compensate.

The usual justification would be cold-start cost — importing `tabulaflow.toolhub` does take
~1.3s. But the app package **already** imports it eagerly: `app/pane/graphs.py:9` imports
`tabulaflow.toolhub.render_graph` at module scope, and `app/widgets.py:49` imports
`tabulaflow.chat` (which sits above toolhub). Measured:

```text
import tabulaflow.app.pane            -> 1.039s
  tabulaflow.toolhub                  already loaded: True
  tabulaflow.toolhub.output_resolver  already loaded: True
  tabulaflow.toolhub.output_store      already loaded: True
```

The deferral buys nothing. There is no cycle either — `import-linter` already forbids
`toolhub` from importing `app`, and `grep` confirms none exists. These imports are vestige,
and the `object` signatures are lying to preserve it.

## Decisions (settled — do not relitigate)

1. **`core/outputs.py` and the `toolhub` runtime are unchanged.** `OutputSpec`,
   `OutputStore`, `OutputResolver`, and `ResolvedOutput` keep their current contracts.
   `ResolvedOutput` continues to carry metadata only — attaching DataFrames to it would put
   runtime data in a serializable pydantic model and break the layering that
   `ultimate_output_model_plan.md` establishes.
2. **Full recompute stays.** A selection change re-resolves and rebuilds every card. No
   incremental patching, no per-artifact diffing. At this data scale it is correct and it
   eliminates a class of state bugs.
3. **Immutable card files stay.** Each render mints `card_<hex>` and writes a fresh
   `.data.json`; the client fetches by id (`pane.js:580`). No invalidation protocol, stale
   ids stay valid.
4. **Presenters keep their freedom to differ.** The terminal may render a placeholder where
   the browser renders a map. The plan builder attaches data; what a presenter does with it
   is the presenter's business.
5. **The shared pipeline lives in `app/`, not `toolhub/`.** It needs `OutputStore` (toolhub)
   and encodes presentation intent. `app` may import `toolhub` at module scope.
6. **Existing presenters stay where they are.** `display.py` remains the terminal presenter
   and `pane/cards.py` the browser presenter. This plan reduces them to presentation; it does
   not move them.
7. **`CardPlan` carries eager payloads, not lazy handles.** A lazy `load()` callable would
   push store coupling back into presenters, which is the coupling being removed. The cost is
   that the terminal now fetches map/graph payloads it renders as placeholders; that cost is
   near zero because `get_payload` hits the in-memory LRU that the same turn's browser push
   has already warmed.

## Target structure

```text
tabulaflow/app/
├── output/                  # NEW — the shared pipeline, defined once
│   ├── __init__.py
│   ├── plan.py              #   CardPlan, ViewPlan union, build_plans(resolved, store)
│   ├── controls.py          #   Control union, controls_for(spec)
│   └── turn.py              #   TurnOutput(spec, store, selection).apply(selection)
├── display.py               # terminal presenter: CardPlan -> CardGroup
├── widgets.py               # terminal input: keypress -> TurnOutput.apply
├── tui.py                   # wiring
└── pane/
    ├── cards.py             # browser presenter: CardPlan -> PaneCard + json
    ├── server.py            # browser transport: POST /resolve -> TurnOutput.apply
    └── types.py             # Control -> JSON projection lives here
```

## Key types

```python
# app/output/plan.py

@dataclass(frozen=True)
class TableViewPlan:
    df: pd.DataFrame
    query: str
    query_lexer: str            # "sql" | "cypher", already derived from connector_type

@dataclass(frozen=True)
class ChartViewPlan:
    df: pd.DataFrame
    spec: dict[str, Any]
    query: str
    query_lexer: str

@dataclass(frozen=True)
class MapViewPlan:
    sources: dict[SourceId, pd.DataFrame]
    spec: dict[str, Any]

@dataclass(frozen=True)
class GraphViewPlan:
    graph: GraphView
    layout: str

ViewPlan = TableViewPlan | ChartViewPlan | MapViewPlan | GraphViewPlan

@dataclass(frozen=True)
class CardPlan:
    artifact_id: ArtifactId
    label: str
    view: ViewPlan
    error: str | None = None    # see Phase 6

async def build_plans(resolved: ResolvedOutput, store: OutputStore) -> list[CardPlan]:
    """The only place that dispatches on ViewDef and fetches payloads."""
```

Both presenters then collapse to a single dispatch over `ViewPlan` with no store access, no
`await`, and no `SimpleNamespace`:

```python
# app/display.py
def present(plan: CardPlan, width: int) -> CardGroup | None: ...

# app/pane/cards.py
def present(plan: CardPlan, pane_dir: Path) -> PaneCard | None: ...
```

Controls get the same treatment — one projection, two renderings:

```python
# app/output/controls.py

@dataclass(frozen=True)
class ChoiceControl:
    id: ParameterId
    label: str
    choices: list[ChoiceOption]

@dataclass(frozen=True)
class NumberControl:                 # declared now, drawn later
    id: ParameterId
    label: str
    min: float
    max: float
    step: float
    unit: str | None
    display: Literal["slider", "input"]

Control = ChoiceControl | NumberControl

def controls_for(spec: OutputSpec) -> list[Control]: ...
```

And the lifecycle gets one owner:

```python
# app/output/turn.py

class TurnOutput:
    """Owns (spec, store, selection) for one turn and the supersede policy."""

    def __init__(self, spec: OutputSpec, store: OutputStore) -> None: ...

    @property
    def controls(self) -> list[Control]: ...

    @property
    def selection(self) -> Selection: ...

    async def apply(self, selection: Selection) -> list[CardPlan]:
        """resolve -> plan. Last call wins; superseded calls raise Superseded."""
```

The terminal keeps `run_worker(..., exclusive=True)` and the browser keeps its `resolveSeq`
on the wire — those are transport concerns. What stops being reimplemented is the
resolve→plan sequence and the "is this response still current" decision.

## Phases

Stop at the end of each phase for user inspection before starting the next.

Verify after every phase: `make lint`, `make mypy`, `make lint-arch`, `make test`.

### Phase 1 — fix the foreign event loop

Independent of the refactor; ship it first.

- Capture the TUI's running loop when `OutputPane` starts and store it on the pane.
- Replace `asyncio.run(pane.resolve_turn(...))` (`server.py:210`) with
  `asyncio.run_coroutine_threadsafe(pane.resolve_turn(...), loop).result(timeout=...)`.
- On timeout, return the existing 500 JSON body rather than blocking the handler thread.
- Add a regression test that resolves a turn whose result frame has been evicted from the
  LRU, so the spill-connector read is exercised from the handler thread.

### Phase 2 — import and typing hygiene

Mechanical, no behavior change. Do it before Phase 3 so the new code is not written against
`object`.

- Hoist the function-local `toolhub` imports in `display.py`, `pane/cards.py`, `tui.py`,
  `widgets.py`, and `server.py` to module scope.
- Retype `build_resolved_output_card_views` and `render_resolved_output` from
  `(resolved_output: object, output_store: object)` to real types; delete the
  `assert isinstance(...)` lines and the `cast(OutputStore, ...)` calls they enabled.
- Confirm `make lint-arch` still passes (it should — `app` may import `toolhub`).

### Phase 3 — introduce `CardPlan`

The core of the plan.

- Add `app/output/plan.py` with the types above and `build_plans`, moving the four-branch
  dispatch and every `get_payload` call into it.
- Rewrite `display.py:build_resolved_output_card_views` as `present(plan, width)` over
  `ViewPlan`, preserving today's terminal behavior exactly: `MapViewPlan` and
  `GraphViewPlan` still render placeholders, and a `GraphViewPlan` that fails
  `materialize_graph_view` is still skipped (that check moves into `build_plans`).
- Rewrite `pane/cards.py:render_resolved_output` as `present(plan, pane_dir)`.
- Delete `ResultMetadataLike`, `MapArtifactLike`, `GraphArtifactLike`, and all four
  `SimpleNamespace` constructions.
- Update the callers in `tui.py:1145-1153` and `server.py:558` to
  `build_plans(...)` → `present(...)`.

### Phase 4 — unify controls

- Add `app/output/controls.py` with `Control` and `controls_for`.
- Delete `_pane_panel` (`tui.py:95`) and `_choice_controls_from_result`
  (`widgets.py:1743`); both call `controls_for`.
- Move the `Control` → JSON projection into `pane/types.py` next to `PanePanel`, and widen
  `PaneChoiceControl` into a discriminated `PaneControl` union so the JS filter has
  something to switch on rather than a single hardcoded kind.
- `NumberControl` is produced by `controls_for` from this phase on; both presenters skip it
  explicitly with a comment pointing at the follow-up, so the gap is visible in one place
  instead of implicit in four.

### Phase 5 — `TurnOutput`

- Add `app/output/turn.py`.
- `AgentResultWidget` drops `_result` / `_output_store` / `_applied_selection` in favour of
  one `TurnOutput`; `_resolve_cards_for_selection` (`widgets.py:1710`) becomes a call to
  `apply` plus `_rebuild_cards_for_selection` (which keeps its cursor-preservation logic —
  that is genuinely terminal-specific).
- `OutputPane._live_results` stores `TurnOutput` instead of the `(result, output_store)`
  tuple; `resolve_turn` becomes `apply` plus `present`.
- Decide explicitly whether the two surfaces share one `TurnOutput` per turn (selection
  syncs between terminal and browser) or hold one each (today's behavior). Recommendation:
  share it. Per-surface selection is currently an accident of two implementations, not a
  decision, and a shared `TurnOutput` makes sharing the default with divergence available as
  an opt-out.

### Phase 6 — error cards instead of silent drops

- `pane/cards.py:237` wraps each artifact in `except Exception: card = None`, so an artifact
  the user explicitly asked to see can vanish with no message.
- Populate `CardPlan.error` in `build_plans` and have both presenters render a visible error
  card. Silent is worse than ugly for a card the agent chose to show.
- This is the app-side counterpart of the `SourceNotApplicable` /
  `ResolvedArtifact = AvailableArtifact | UnavailableArtifact` direction sketched in
  `ultimate_output_model_plan.md`. If that lands first, `CardPlan.error` should carry the
  distinction between "not applicable for this selection" and "failed to render".

## Deferred / explicitly out of scope

1. **Drawing number controls.** Phase 4 creates the seam; the slider widget, its debounce
   policy (every drag position is a cache miss), and the JS range input are separate work.
2. **Persisting interactivity across restarts.** `_live_results` is in-memory, so a restored
   turn renders from its on-disk `.data.json` but returns 404 from `/resolve`. Making this
   survive is closer than it looks — `OutputSpec` already round-trips through JSON exactly
   and result frames already spill to the workspace DuckDB; what is missing is persisting the
   spec and the `(source_id, selection_key) -> result_id` map. Until then, the manifest should
   at least mark a turn non-live so controls render disabled with a reason instead of failing
   on click.
3. **Cross-filtering and view-shape parameterization.** A Vega selection cannot feed back
   into a `ParameterId`, and `ChartView.spec` is fixed. Both are core-model changes and belong
   in `ultimate_output_model_plan.md`, not here.
