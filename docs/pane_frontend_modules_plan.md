# Output-Pane Frontend — Split into ES Modules (no build)

Break the two large hand-written pane scripts into native ES modules — renderers
by artifact, the shell kept whole — with **no bundler, no framework, no npm**.
Add a `contract.d.ts` so the JS side of the Python↔JS boundary is type-checked.

> **Status:** proposed, ready to implement. Pure frontend + a small `server.py`
> loading change; does not touch the Python payload contract (`pane/types.py`).

---

## 1. Current state (accurate)

`tabulaflow/app/pane/assets/pane/`:

- `pane-render.js` — **1675 lines, 77 fns**, one IIFE that ends with
  `window.TF = { renderTable, renderChart, renderMap, renderGraph, renderQuery, … }`.
  Served as a file: `<script src="/assets/pane/pane-render.js?v=__PANE_RENDER_VERSION__">`.
- `pane.js` — **639 lines, 60 fns**, top-level functions (not an IIFE). **Inlined**
  into the page: `index.html` has `<script>__PANE_JS__</script>` and `server.py`
  substitutes the file contents at serve time. Dispatches views via the global,
  e.g. `if (kind === 'map') return TF.renderMap(node, data);`.
- `pane.css` — 455 lines (owns the palette `:root` vars).
- `index.html` — loads vendored libs as **classic global scripts** (`tabulator`,
  `maplibre`, `vega`+`vega-lite`+`vega-embed`, `cytoscape`+`dagre`), then
  `pane-render.js` (file), then inline `pane.js`.

So today: renderers are a global `window.TF` blob; the shell is server-inlined;
vendored libs are globals (`window.Tabulator`, `maplibregl`, `vegaEmbed`,
`cytoscape`). The Python payload contract lives in `pane/types.py` and is untyped
on the JS side.

## 2. Target structure (lean — split by weight, not taxonomy)

```
tabulaflow/app/pane/assets/pane/
├── index.html
├── pane.css
├── contract.d.ts        # JS mirror of pane/types.py — type-check only, never shipped/built
├── pane.js              # THE SHELL (one module): bootstrap + SSE/manifest + turn rail
│                        #   + card tabs + view lifecycle + the kind→renderer dispatch
└── render/
    ├── shared.js        # helpers used across renderers (see §4)
    ├── table.js         # renderTable   (Tabulator)
    ├── chart.js         # renderChart   (Vega)
    ├── map.js           # renderMap     (MapLibre)
    ├── graph.js         # renderGraph   (Cytoscape)
    └── query.js         # renderQuery   (small; may fold into shared.js — implementer's call)
```

**2 files → 7** (one shell + six render modules). Each render module is large and
cohesive and mirrors one Python builder / view kind; the shell stays a single file.

## 3. Key decisions

- **Native ES modules, no build.** `import`/`export` + `<script type="module">`,
  served straight by `server.py`. No bundler, no `node_modules`, no framework — the
  no-build property is the point.
- **Vendored libs stay classic globals.** Do **not** convert Tabulator/MapLibre/
  Vega/Cytoscape to ESM. They remain `<script src>` (classic) and the render
  modules read them off `window` (`window.Tabulator`, `maplibregl`, `vegaEmbed`,
  `cytoscape`). Classic scripts run before deferred module scripts, so the globals
  exist when the module runs — no ordering work, churn stays contained.
- **The shell is one file.** `pane.js` keeps `el()`, SSE, turn rail, card tabs, and
  the view lifecycle together. Split it further *only later* and *only* if it stays
  unwieldy, along its one fault line (the stage/reveal/cache lifecycle). Do **not**
  pre-split into nav/sse/cache/dom.
- **Kill `window.TF`.** Replace the global with `export`/`import`. The dispatch
  (`kind → renderer`) lives in `pane.js`, importing the render functions.
- **Type the JS side** with `contract.d.ts` + `// @ts-check`, mirroring
  `pane/types.py`. No `.ts` sources, no compile step (a `.d.ts` is only read by the
  checker).

## 4. Function → module mapping (for `pane-render.js`)

Move the 77 functions by concern:

- **`render/shared.js`** (export): `escapeHtml`, `escapeAttr`, `formatNumber`,
  `displayValue`, `numberValue`/`numberOr`, `asUrls`, `link`, `tooltipLink`,
  `fieldValue`, `cssVar`, media/format helpers, the color palette + `colorFor` +
  `withDerivedColorDomain` + legend builders, and the tooltip/`detailHtml`
  helpers — everything used by more than one renderer.
- **`render/table.js`**: `renderTable` + table-only helpers (formatter factories,
  `headerMinWidth`, role→Tabulator-formatter mapping, width computation).
- **`render/chart.js`**: `renderChart` + `vegaDarkConfig` + chart theming.
- **`render/map.js`**: `renderMap` + map helpers (`mapLayers`, `buildPointFeatures`,
  `buildGeoJsonFeatures`, `addCircleLayer`, `addGeoJsonLayers`, `bindLayerDetails`,
  marker/popup builders, `destroyMap`, bounds/`fitBounds` logic).
- **`render/graph.js`**: `renderGraph` + Cytoscape setup.
- **`render/query.js`**: `renderQuery` (small).

Each render module starts with `// @ts-check` and imports its helpers from
`./shared.js`; each `export function render<X>(node, data) { … }`.

## 5. Migration steps

1. **Extract `render/shared.js`** from `pane-render.js` (the helpers in §4), as ESM
   exports. Read vendored libs off `window` where needed.
2. **Split the renderers** into `render/{table,chart,map,graph,query}.js`, each
   importing from `./shared.js` and `export`ing its `render<X>`. Delete
   `pane-render.js` and the `window.TF` block.
3. **Convert `pane.js` to a served ES module.** Keep it one file. Replace the
   `TF.render*` dispatch with imports:
   `import { renderTable } from './render/table.js'` … and a local
   `renderView(kind, node, data)` switch. It stays top-level (module scope is
   already isolated — the old IIFE-vs-global distinction disappears).
4. **`index.html`**: remove `<script src="pane-render.js?v=…">` and the inline
   `<script>__PANE_JS__</script>`; add a single
   `<script type="module" src="/assets/pane/pane.js?v=__PANE_VERSION__"></script>`.
   Keep the vendored `<script src>` (classic) lines as-is, before the module.
5. **`server.py`**: stop inlining `pane.js` (drop the `__PANE_JS__` substitution)
   and drop `__PANE_RENDER_VERSION__`; serve `pane.js` and `render/*.js` as static
   files. Keep one cache-bust token (`__PANE_VERSION__`, e.g. a content hash) on the
   module entry. **Confirm the `/assets/` handler serves nested paths**
   (`/assets/pane/render/*.js`) — the module's relative `./render/x.js` resolves
   there.
6. **`contract.d.ts`**: mirror `pane/types.py` — `CardData`, `TableData`,
   `ChartData`, `MapData`, `GraphData`, `QueryData`, `ColumnDesc`, `PaneTurn`,
   `PaneCard`, `ViewKind`. Reference from modules via
   `/** @param {import('./contract.js').CardData} data */` (or a `<reference>`),
   with `// @ts-check` at the top of each module.

## 6. Test fallout (important — plan for it)

`tests/test_output_pane.py` still has source-string assertions that snapshot the
JS: `assert "…" in _PANE_HTML` (the inlined page) and `assert "…" in renderer`
(the `pane-render.js` blob). **The split invalidates both**: `pane.js` is no longer
inlined into `_PANE_HTML`, and `pane-render.js`/`renderer` ceases to exist as one
blob.

Do **not** re-pin new strings against the new files (that just relocates the
brittleness). Instead:

- Drop the `in renderer` / `in _PANE_HTML` **JS-source** assertions (function
  signatures, internal lines) — they're the same anti-pattern already retired once.
- Keep coverage where it's real: the `CardData` **contract test**
  (`test_pane_contract.py`) for the payload shape, and any **behavior/CSS** checks
  that don't snapshot JS internals. If a genuine guard is worth keeping (e.g.
  "no Leaflet"), assert it against the specific module file's served content, not a
  concatenated blob.
- Update the pane test fixture that reads `renderer` to read the module file(s) it
  actually needs, or delete it if it only fed source-string asserts.

## 7. Verification

- `node --check` each `render/*.js` and `pane.js` (syntax; note it won't resolve
  imports — that's fine).
- Optional: `npx tsc --noEmit --checkJs --allowJs` over `assets/pane/` to exercise
  `contract.d.ts` + `// @ts-check` (no install needed if `tsc` is available; skip if
  not — it's a bonus, not a gate).
- **Preview smoke (the real gate):** `uv run scripts/preview_output_pane.py
  --port 61211`, then confirm the module + each `render/*.js` serve **200** under
  `/assets/pane/…`, and eyeball that table/chart/map/graph/query cards render (the
  `type="module"` + relative-import + nested-path change is exactly what silently
  404s or fails to load).
- `make test` green (after the §6 test fixup).

## 8. Non-goals / out of scope

- No bundler, framework (React/Preact/lit), `package.json`, or `.ts` sources.
- No further shell split (nav/sse/cache) — deferred until proven necessary.
- No `assets/pane/ → ui/` + `assets/vendor/` reorg — optional polish, separate PR;
  it's a git-move of the vendored blobs + a `/assets/` path change, churn for
  cosmetics. This plan keeps the current `assets/pane/` + `assets/<lib>/` layout.
