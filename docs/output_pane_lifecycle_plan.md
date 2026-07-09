# Output Pane Renderer Lifecycle — Implementation Plan

Consolidate the three hand-rolled renderer readiness loops (chart, map, graph)
behind a single pane-owned measurability gate.

## Status

The original "proposal" is superseded — most of it already shipped. Renderers
already return lifecycle handles (`afterVisible`/`afterHidden`/`destroy`), and
`setActiveShellView` already defers heavy library init until a node is the active
view. The remaining work is **deduplication and robustness**, not new capability.

## Why change working code

Each lifecycle-sensitive renderer reinvents the same "init once, but the view may
be hidden mid-init" state machine, and they do it inconsistently:

| Renderer | Init guard state | Measurability check | Silent-failure path |
|----------|------------------|---------------------|---------------------|
| `chart.js` | `renderStarted`, `pendingFrame`, `disposed` | `hasMeasurableTarget()` (width, or width+height for `fill`) | `measureAttempts <= 20` then gives up |
| `map.js` | `mapInitPending`, `mapInitToken`, `isConnected` | none — relies on rAF timing + later `syncView` | — |
| `graph.js` | `initPending`, `initToken`, `isConnected` | none — relies on rAF timing + later `fitGraph` | — |

Three consequences:

1. **Duplicated, divergent concurrency bookkeeping.** The `*Token` counters exist
   only to invalidate stale async init when the node disappears mid-flight. That
   is gate-owned state, copied three times, each able to grow its own race.
2. **The target invariant only half-holds.** Only charts verify non-zero
   dimensions before init. Maps and graphs init on rAF timing and paper over a
   bad first measure with a later re-fit — the root cause behind recurring
   "map viewport fitting" / "chart rendering" fixes.
3. **Two concrete bugs.** (a) `chart.js` silently blanks if the container needs
   more than ~20 frames to gain width. (b) No live resize: the window `resize`
   listener (`pane.js`) only re-lays-out card headers; nothing calls
   `view.resize()` / `map.resize()` / `cy.resize()` while a view is visible, so
   all three only re-fit on tab re-activation.

A shared `ResizeObserver` gate fixes all three at once and deletes more code than
it adds. This is not over-abstraction: it collapses three divergent copies of
race-prone logic into one, for a real correctness gain.

## Decisions (locked)

- **Keep destroy-on-hide for map/graph.** MapLibre and Cytoscape are heavy
  (cache weight 3); tearing them down when hidden and rebuilding on return stays.
  Charts stay alive when hidden (weight 1).
- **Convert all three renderers in one change.** The whole value is uniformity;
  a chart-only proof would leave the invariant inconsistent.
- **Three-method handle, not four.** `mount` / `resize` / `destroy`. No separate
  `hide` — teardown-on-hide is expressed by `unmount` (map/graph tear down,
  chart cancels pending work); permanent teardown is `destroy`.
- **`resize()` does not re-fit camera/layout.** On a live resize, call
  `map.resize()` / `cy.resize()` only, preserving the user's pan/zoom. The
  initial fit happens once inside `mount()`.

## Target handle interface

```js
{
  requires: { width: true, height: true },  // when the node is "measurable enough" to mount
  mount:   function () {},                   // node is connected, active, and meets `requires`
  resize:  function () {},                   // node size changed while mounted (no re-fit)
  unmount: function () {},                   // node became inactive/hidden
  destroy: function () {},                   // entry evicted — permanent teardown
}
```

- Missing `requires` → mount immediately on activation (no measurement wait).
- Renderers with no measurement dependency (`table`, `query`) return
  `{ destroy }` only; the gate no-ops the rest. Their DOM is already built in
  `renderKind`.

## Pane-owned gate (`pane.js`)

Replace the `afterVisible`/`afterHidden` indirection with a `ResizeObserver`
driven per active view node. The observer *is* the readiness wait — it fires on
first non-zero layout, so no rAF loop and no attempt cap.

```js
function measurable(node, requires) {
  if (!node.isConnected) return false;
  var r = node.getBoundingClientRect();
  if (requires.width  && !(r.width  > 0)) return false;
  if (requires.height && !(r.height > 0)) return false;
  return true;
}

function gateActivate(entry) {
  var h = entry.handle;
  if (!h || !h.mount || entry.gated) return;
  entry.gated = true;
  var requires = h.requires || { width: false, height: false };
  entry.observer = new ResizeObserver(function () {
    if (!entry.mounted) {
      if (!measurable(entry.node, requires)) return;
      entry.mounted = true;
      h.mount();
    } else if (h.resize) {
      h.resize();
    }
  });
  entry.observer.observe(entry.node);
}

function gateDeactivate(entry) {
  if (!entry.gated) return;
  entry.gated = false;
  if (entry.observer) { entry.observer.disconnect(); entry.observer = null; }
  if (entry.mounted && entry.handle.unmount) entry.handle.unmount();
  entry.mounted = false;
}
```

Touch points:

- `setActiveShellView` — for the active node call `gateActivate(entry)`; for the
  rest call `gateDeactivate(entry)`. Replaces the `afterVisible`/`afterHidden`
  calls.
- `hideViewNode` / `stageViewNode` — call `gateDeactivate(node._tfViewEntry)`.
- `cacheTouch` eviction — before `handle.destroy()`, `gateDeactivate(entry)` so a
  mounted view unmounts and stops observing first.
- Delete `afterVisible(entry)` and `afterHidden(entry)` helpers.
- Extend the entry shape (`{ node, handle, data, kind }`) with `gated`,
  `mounted`, `observer`. `gateActivate` must be idempotent — `setActiveShellView`
  is called redundantly (e.g. `revealStagedView` fires it twice via rAF).

## Per-renderer conversion

### `chart.js`
- **Delete:** `renderWhenReady`, `hasMeasurableTarget`, `measureAttempts`,
  `pendingFrame`, `clearPendingFrame`, the `afterVisible`/`afterHidden` handle.
- **`requires`:** `{ width: true, height: wrapClass === 'fill' }`.
- **`mount()`:** if not yet embedded, `vegaEmbed(...)` (node is measurable — no
  loop); else `resizeView()`.
- **`resize()`:** `view.resize().runAsync()`.
- **`unmount()`:** no-op (view stays alive; nothing pending to cancel).
- **`destroy()`:** `disposed = true; if (view) view.finalize()`.

### `map.js`
- **Delete:** `mapInitPending` and the `isConnected` guard inside `initMap` (the
  gate guarantees connected + measurable); the double-rAF `syncView` in the old
  `afterVisible`.
- **Keep:** `mapInitToken` — still needed to discard a stale async style `fetch`
  across an unmount/mount cycle.
- **`requires`:** `{ width: true, height: true }`.
- **`mount()`:** `initMap()` (its `load` handler runs `addDataLayers` + initial
  `syncView` with fit).
- **`resize()`:** `map.resize()` only — no re-fit.
- **`unmount()`:** `destroyMap()`.
- **`destroy()`:** `destroyMap(); container.innerHTML = ''`.

### `graph.js`
- **Delete:** `initToken`, `initPending`, the `requestAnimationFrame` wrapper and
  `isConnected` guard in `initGraph` — build Cytoscape synchronously in `mount()`
  since the gate guarantees a measurable container.
- **`requires`:** `{ width: true, height: true }`.
- **`mount()`:** build Cytoscape; `fitGraph` on `layoutstop`.
- **`resize()`:** `cy.resize()` only — no re-fit.
- **`unmount()`:** `destroyGraph()`.
- **`destroy()`:** `destroyGraph(); container.innerHTML = ''`.

## Unchanged

- `renderTable` / `renderQuery` — no measurement dependency, no `mount`.
- `renderLoadedView` / `renderKind` — still build DOM + return a handle eagerly;
  only the post-activation path changes.
- Cache weights, LRU eviction, `prewarmDataView`, scroll memory.

## Migration order

1. Add `measurable` + `gateActivate`/`gateDeactivate` and the entry-state fields
   in `pane.js`; rewire `setActiveShellView`, `hideViewNode`, `stageViewNode`,
   `cacheTouch`; delete `afterVisible`/`afterHidden`.
2. Convert `chart.js` (removes the 20-frame cap; smallest blast radius).
3. Convert `map.js`.
4. Convert `graph.js`.
5. Grep the tree for any remaining `afterVisible`/`afterHidden` references.

Land as one change (uniformity is the point), but stage the commits per file so
each renderer conversion is separately reviewable.

## Verification

- `make lint` / existing Python payload-contract tests (unchanged).
- Serve the debug pane on `127.0.0.1:8765` and check, via DOM geometry:
  - first chart in a multi-chart turn has non-zero SVG bounds;
  - returning to a chart after visiting many others stays non-zero;
  - switching Chart/Data/Query never mounts a hidden chart at zero size;
  - a map fits its features on first activation and re-inits cleanly after hide;
  - a graph renders non-blank after tab switching;
  - resizing the window resizes the visible chart/map/graph without a re-fit jump
    and without a duplicate mount;
  - cache eviction unmounts then destroys the third-party instance.
