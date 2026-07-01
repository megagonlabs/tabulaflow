# MapLibre Vector Maps (v1) — Design & Implementation Plan

## Goal

Replace the current Leaflet + OpenStreetMap **raster** map renderer in the output
pane with **MapLibre GL** **vector** rendering, for a materially nicer UX: crisp
labels at any zoom, smooth GPU-accelerated pan/zoom, retina sharpness, and a
client-side style we control (light, Google-Maps-like) instead of a baked-in
raster basemap.

Hard constraints (unchanged from today's raster setup):

- **No API key** — no signup, no token management.
- **No bundled or self-hosted map data** — tiles/glyphs/sprites fetched at
  runtime, exactly like today's raster tile fetch.
- **Good UX worldwide** — usable latency in Asia and Europe, not just the US/EU.

## Decision summary

| Question | v1 decision | Rationale |
|---|---|---|
| Renderer | **MapLibre GL JS** (bundled locally, BSD-3) | The de-facto open standard for vector maps; the only real choice for keyless vector. |
| Tile source | **OSMF official vector tiles** (`vector.openstreetmap.org`, Shortbread schema) | The only keyless, no-bundle source on a **global CDN** (Fastly edge) → good UX in Asia *and* Europe. Same foundation we already trust for raster. |
| Base style | Light, **Google-Maps-like** custom style JSON on the Shortbread schema | Matches the requested look; client-side style we fully control. |
| Failover | **Deferred to v2** (single provider for v1) | Keeps v1 small. Failover is a MapLibre style-URL swap, not a second renderer — a clean drop-in later. |
| Leaflet | **Dropped entirely (clean break)** | Maps are Leaflet's only consumer; keeping it leaves a dead ~140 KB lib + a second render path. |

## Environment check (done)

The output pane is served by a local HTTP server (`app/pane.py`) and opened in the
**system browser** (`pane.py` → `webbrowser_open.open(url)`), *not* an embedded
webview. A WebGL probe run in the user's default browser reported:

```
HARDWARE-ACCELERATED WebGL
ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)
```

So MapLibre gets real GPU acceleration here; the CPU/RAM cost of vector rendering
is acceptable and is further contained by lazy-init + context disposal (below).
This resolves the one go/no-go risk (software-rendered `SwiftShader` WebGL, a
webview problem that does not apply to a real desktop browser).

## Key architectural facts (current state)

- **Leaflet's only consumer is the map view.** All references live in
  `app/assets/pane/pane-render.js` (the map block, `L.map`/`L.tileLayer`/
  `L.geoJSON`, ~17 refs), `app/assets/pane/pane.css` (`.tf-map-view .leaflet-*`
  rules, ~lines 297–315), `app/assets/pane/index.html` (two `<link>`/`<script>`
  tags), `app/render/maps.py` (the `"provider": "leaflet"` tag), and the bundled
  `app/assets/leaflet/` itself. Nothing outside `app/` touches Leaflet.
- **The agent-facing spec is already renderer-agnostic.** `docs/map_spec.md`
  defines a declarative TabulaFlow map spec (points from lat/lng, GeoJSON,
  semantic color/size encodings, tooltips, viewport) that intentionally does *not*
  expose Leaflet internals. **The `render_map` tool contract and `map_spec` do not
  change.**
- **`app/render/maps.py` normalization is provider-agnostic.** The `_normalize_*`
  helpers rewrite column names to pane field ids and emit a structured layer list.
  Only the `"provider"` tag and the downstream JS renderer are Leaflet-specific.
- **Maps render behind a tab.** The output pane frames each cited result as a card
  with a `Chart | Data | Query` tab strip; the map lives under a tab, so it is not
  visible (and need not be instantiated) until selected.

## Design

### Tile source & style

- Tiles: `https://vector.openstreetmap.org/shortbread_v1/{z}/{x}/{y}.mvt`
  (via the published `tilejson.json`), served over Fastly's global edge.
- Glyphs/sprites: referenced by URL from the style JSON — fetched at runtime, not
  bundled.
- Style: a light, Google-Maps-like style JSON authored against the **Shortbread**
  schema (fork/trim a known light Shortbread style; tune land/road/label colors).
  Presentation constants (point radius, opacity, stroke) stay in the renderer, per
  `docs/map_spec.md`.
- Attribution: OSM attribution shown per the
  [OSMF Vector Tile Usage Policy](https://operations.osmfoundation.org/policies/vector/)
  (bottom-right). MapLibre's attribution control handles this.

### Renderer (`pane-render.js`)

- Construct `maplibregl.Map` with the style URL above.
- Port the two supported layer types from the current Leaflet block:
  - **points** — `lat`/`lng` (or inline `points`) → a GeoJSON source + circle (or
    symbol) layer; honor `marker.type` (`pin`/`circle`), `color` and `size`
    encodings, `label`, and `tooltip`.
  - **geojson** — geometry column → GeoJSON source + fill/line layers with the
    `color` encoding.
- Tooltips/popups → `maplibregl.Popup` (replacing the Leaflet tooltip/popup used by
  `bindMapDetail`).
- Viewport: `view.fit` → `fitBounds` over the data; `center`/`zoom` map directly.

### Resource management (why vector is safe here)

Vector maps cost more browser CPU/RAM than raster (WebGL context + client-side
tessellation + label collision, ~50–150 MB per live map vs ~10–30 MB for Leaflet
raster). Browsers also cap simultaneous WebGL contexts (~16). Mitigation, enabled
by the tab structure:

- **Lazy init**: construct the `maplibregl.Map` only when the Map tab is first
  shown, not when the card renders.
- **Dispose on hide**: call `map.remove()` (releasing the WebGL context) when the
  Map tab is deselected; re-create on re-selection.

This keeps live contexts to ~1–2 even when a response cites many map results.

### Python (`app/render/maps.py`)

- Change the emitted tag `"provider": "leaflet"` → `"provider": "maplibre"`.
- No change to `_normalize_*` logic, the `render_map` tool, or `map_spec`.

## Implementation plan (phased, inspect between phases)

**Phase 1 — Assets + wiring.**
- Add `app/assets/maplibre/` with `maplibre-gl.js` + `maplibre-gl.css` (bundled
  locally, like Leaflet was).
- Delete `app/assets/leaflet/` entirely (`leaflet.js`, `leaflet.css`, `LICENSE`,
  `images/*.png`, `__init__.py`).
- Swap the two `<link>`/`<script>` lines in `index.html`.
- Flip the provider tag in `maps.py`.
- *State after phase:* map area blank (no renderer yet); rest of pane unaffected.

**Phase 2 — Render logic.**
- Rewrite the map block in `pane-render.js` → MapLibre sources/layers/popups for
  the `points` and `geojson` layer types.
- Implement lazy-init-on-tab-show and dispose-on-tab-hide.

**Phase 3 — Style + CSS.**
- Add the light, Google-Maps-like Shortbread style JSON.
- Port `.tf-map-view .leaflet-*` rules in `pane.css` → `.maplibregl-*` equivalents
  (attribution, popup/tooltip, focus outlines).
- Regenerate the debug HTML (`uv run scripts/gen_debug_html.py`) and eyeball the
  map fixtures.

## Non-goals (v1)

- **Provider failover / redundancy** — deferred to v2 (drop-in style-URL swap to
  OpenFreeMap or a self-hosted Protomaps PMTiles file).
- **Dark/mint themed basemap** — v1 ships the light Google-like look as requested;
  theming to the app palette can follow.
- **Changes to the agent-facing `render_map` tool or `map_spec`** — none.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| OSMF policy may throttle/block heavy app traffic without notice. | Fastly fronting makes hard blocks unlikely at research/demo volume; v2 failover (OpenFreeMap / self-hosted Protomaps) is the safety net. |
| Vector CPU/RAM > raster; WebGL context cap (~16). | Lazy-init + dispose-on-hide keeps live contexts to ~1–2. GPU accel confirmed on target machine. |
| Shortbread default styles are lower-contrast / criticized. | We author our own light style; default style is irrelevant. |
| Software-rendered WebGL would negate GPU benefit. | N/A here — pane opens in the system browser; hardware WebGL confirmed. |

## References

- [OSMF Vector Tile Usage Policy](https://operations.osmfoundation.org/policies/vector/)
- [Vector tiles deployed on OpenStreetMap.org (Jul 2025)](https://blog.openstreetmap.org/2025/07/22/vector-tiles-are-deployed-on-openstreetmap-org/)
- [Shortbread tile schema](https://shortbread-tiles.org/)
- [OpenStreetMap + Fastly (global CDN)](https://www.fastly.com/customers/openstreetmap)
- [MapLibre GL JS](https://maplibre.org/projects/gl-js/)
- Internal: `docs/map_spec.md` (agent-facing map contract, renderer-agnostic)
