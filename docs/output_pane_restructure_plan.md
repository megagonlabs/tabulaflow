# Output-Pane Restructure & Python↔Frontend Boundary — Implementation Plan

Consolidate the browser output-pane code into a single `app/pane/` package, make
the Python↔JS boundary an explicit typed contract, and push presentation policy
out of Python into the frontend. Keep the TUI flat at the `app/` root — it's the
app's trunk, not a peer surface.

> **Status:** proposed. Prereq (HTML page-dump removal) is **done**
> (`render_table_html` / `render_chart_html` / `render_query_html` / `render_page`
> / `gen_debug_html.py` are gone). Leftovers to clean up in Phase 0.

---

## 1. Motivation

The output pane is Python-produces-JSON, browser-consumes-JSON, over HTTP. Two
problems have accumulated:

1. **Scatter.** Pane code lives in `app/render/` (payload builders) + `app/pane.py`
   (server) + `app/pane_types.py` (wire types) + `app/page.py` (palette). A
   consumer wiring the pane imports from three roots. Once the divergent HTML-dump
   renderer was removed, `render/` is *exclusively* pane payload-building — no
   reason to remain a separate top-level thing.
2. **The boundary is implicit and hand-synced.** The `.data.json` card payload has
   no single definition — ad-hoc dicts on the Python side, read by convention in
   `pane-render.js`. Every recent drift bug is a symptom: the `records → cards`
   wire-key rename (flip both sides by hand), the map card 404 (the `rec_` prefix
   encoded in three places that must agree), the `core`/`growth` color collision
   (a rendering decision living un-specified on the JS side).
3. **Presentation policy leaks into Python, inconsistently.** The table payload
   ships Python-computed pixel widths (`minWidth`/`widthGrow`), formatter names,
   and `rowHeaderWidth`; the palette is Python-injected into the browser `:root`
   (`pane.py::_pane_css_vars`) and baked into Vega specs server-side
   (`charts.py`). Meanwhile the **map** path (per `map_spec.md`) already keeps
   presentation in the renderer — semantic layers in, palette/radius chosen in JS.
   Same subsystem, two philosophies.

## 2. Key Decisions

- **Package the pane; keep the TUI flat.** A package should mark a *seam you could
  cut*. The pane passes the delete test — remove it and the app still runs
  TUI-only; it's independently servable with its own JS contract, assets, and
  lifecycle. The TUI fails the delete test — it *is* the app's trunk, the mandatory
  interaction surface, not a peer. So the structure is **deliberately asymmetric**:
  `app/` root = the TUI (the app), `app/pane/` = the one optional, detachable
  subsystem. This mirrors the runtime asymmetry (TUI mandatory, pane optional
  viewer) rather than imposing a false `tui/`+`pane/` symmetry. It also composes
  with the top-level layering — `app/` is already the delivery layer (core logic
  is in `chat/`/`toolhub/`/`core/`), so inside `app/` the only real split is
  primary-UI vs optional-viewer.
- **Shared binary utils stay neutral.** `sniff_binary` / `try_decode_base64` are
  used by both the pane's `tables.py` *and* the TUI cell inspector
  (`screens.py`). They move to a neutral `app/media.py`, **not** into `pane/`
  (that would create a TUI→pane import for a util — a dependency smell).
- **`pane/types.py` is the interface** (A+B). Both contracts — the turn manifest
  (`PaneTurn`/`PaneCard`, already typed) *and* the card-data payload (`CardData`
  and its `TableData`/`ChartData`/`MapData`/`QueryData` sub-shapes, currently
  ad-hoc) — are typed in one file. `ViewKind` and the `rec_` id convention are
  defined once there and imported by the producer (`cards.py`) and the server
  (`server.py`), killing the "N places must agree" class.
- **The boundary is semantic** (D). Python emits *what* (rows + column roles +
  specs + map layers); the frontend owns *how* (widths, formatters, palette,
  Vega/MapLibre theming). The palette becomes static CSS custom properties in
  `pane.css`; the Vega theme is applied client-side via `cssVar()` (as the map
  renderer already does); table column widths/formatters are chosen in
  `pane-render.js` from the rows it already has. `page.py` is deleted.
- **Contract test, not source-string test** (C). Replace the brittle
  `assert "function buildCard…" in _PANE_HTML` assertions with a real shape test:
  build a representative payload and validate it against `CardData`. Drift fails a
  test instead of the browser.

## 3. Non-Goals

- No codegen / JSON-Schema / protobuf / runtime schema validation in prod. This is
  a single-user, ephemeral, localhost tool ("not a web app"); TypedDicts +
  a shape test are the right weight.
- No `tui/` package (see §2 — the TUI is the trunk, not a subsystem).
- No change to the serving model (Option 2: self-contained files + polled/SSE
  manifest) or the turn-navigator UI.
- No new pane features. Pure restructure + boundary hardening.

## 4. Target `app/` structure

```
tabulaflow/app/
├── __init__.py  main.py
├── session.py  runtime_paths.py  media.py       # thin glue / shared spine
├── tui.py  widgets.py  screens.py  commands.py   # the app's trunk — the TUI
├── display.py  banner.py  theme.py  tui.tcss     #   terminal rendering + chrome
├── debug.py  sample_data.py
├── pane/                     # the optional, detachable browser subsystem
│   ├── __init__.py           #   public API (OutputPane, PaneCard, PaneTurn,
│   │                         #     CardData, render_record_data, render_map_data, …)
│   ├── server.py             #   OutputPane HTTP server + SSE + rec_ allowlist
│   ├── types.py              #   THE boundary contract (manifest + CardData + ViewKind + rec_)
│   ├── cards.py              #   render_record_data / render_map_data / build_query_data
│   ├── tables.py             #   build_table_data (semantic column descriptors — D)
│   ├── charts.py             #   build_chart_data (semantic spec, no server theme — D)
│   ├── maps.py               #   build_map_data (already semantic — the model for D)
│   └── assets/               #   pane/ (index.html, pane.css owns palette, pane.js,
│       …                     #     pane-render.js owns widths/formatters/theme),
│                             #     tabulator/, vega/, maplibre/
└── assets/                   # non-runtime shared/dev fixtures
    └── debug/  samples/
```

**Deleted:** `page.py` (palette → `pane.css`), `pane.py::_pane_css_vars`,
`app/render/` (folded into `pane/`), the cell-dump helpers + `tests/test_dump.py`.
**Neutral (root):** `app/media.py` (shared binary utils). **Untouched:** all TUI
files, `session.py`/`runtime_paths.py` (shared glue both surfaces stand on).

## 5. The boundary contract (what Phase 2 pins down)

Two typed contracts in `pane/types.py`:

```python
ViewKind = Literal["map", "chart", "data", "query"]
CARD_ID_PREFIX = "rec_"          # minted in cards.py, allow-listed in server.py

# 1. Turn manifest (SSE / turns.jsonl) — already typed today
class PaneCard(TypedDict):   id: str; label: str | None; views: list[ViewKind]
class PaneTurn(TypedDict, total=False):
    id: int; title: Required[str]; cards: Required[list[PaneCard]]
    user: str; assistant: str; source: PaneSource

# 2. Card-data payload ({card_id}.data.json) — NEW: type the ad-hoc dict
class TableData(TypedDict, total=False): columns: list[ColumnDesc]; hasMedia: bool; ...
class DatasetData(TypedDict):            rows: list[dict[str, object]]
class ChartData(TypedDict):              spec: dict; renderer: str; wrapClass: str
class QueryData(TypedDict):              sql: str; lexer: str; language: str; html: str
class MapData(TypedDict, total=False):   provider: str; layers: list[dict]; view: dict
class CardData(TypedDict, total=False):
    table: TableData; dataset: DatasetData; chart: ChartData
    query: QueryData; map: MapData; datasets: dict[str, DatasetData]
```

Under **D**, `ColumnDesc` becomes *semantic* (`{field, title, role}` where role ∈
`text|number|bool|media`) and drops `minWidth`/`widthGrow`/`formatter` — those move
to `pane-render.js`.

## 6. Phased implementation

Each phase is independently committable and leaves the app green. Phases are
ordered so churn compounds cleanly.

### Phase 0 — Finish the removal (small)
- Delete `write_cell_dump` + `serialize_cell` from `render/media.py` (cell-dump,
  test-only) and drop them from `render/__init__.py` exports.
- Delete `tests/test_dump.py`.
- Verify: `make test`.

### Phase 1 — `pane/` package + neutral `media.py` (mechanical move)
- `git mv app/pane.py → app/pane/server.py`; `app/pane_types.py → app/pane/types.py`;
  `app/render/{cards,tables,charts,maps}.py → app/pane/`.
- Move surviving `render/media.py` (`sniff_binary`, `try_decode_base64`) →
  `app/media.py`; delete `app/render/`.
- Move runtime browser assets `app/assets/{pane,tabulator,vega,maplibre}` →
  `app/pane/assets/` (~3.4 MB git move); leave `app/assets/{debug,samples}`.
  Update the `importlib.resources` base in `server.py`
  (`tabulaflow.app.assets…` → `tabulaflow.app.pane.assets…`) and the `/assets/`
  path resolution.
- Rewrite imports: `from tabulaflow.app.render import …` and
  `from tabulaflow.app.pane_types import …` → `from tabulaflow.app.pane import …`;
  `sniff_binary` importers (`pane/tables.py`, `screens.py`) → `app.media`.
  Touch points: `tui.py`, `screens.py`, `scripts/preview_output_pane.py`, tests.
- `pane/__init__.py` re-exports the public API.
- Verify: `make test` + `make mypy` + `node --check` + preview smoke
  (`preview_output_pane.py --port 61211`; the asset-path move is exactly what can
  break serving).

### Phase 2 — Type the boundary (A+B)
- In `pane/types.py`, add `CardData` + sub-shapes and the `CARD_ID_PREFIX` const +
  `ViewKind` as the single source.
- `cards.py` mints ids via `CARD_ID_PREFIX`; `server.py` allow-lists via the same
  const (no more literal `"rec_"` in two files). Annotate the `build_*` return
  types with the `CardData` sub-shapes.
- Verify: `make mypy` (the payload builders now type-check against the contract).

### Phase 3 — Contract test (C)
- Add `tests/test_pane_contract.py`: build a representative record card + map card,
  assert the payload validates against `CardData` (keys present, `views` ⊆
  `ViewKind`, each layer names a `source` present in `datasets`, ids start with
  `CARD_ID_PREFIX`).
- Delete the brittle `assert "<js source string>" in _PANE_HTML` assertions in
  `test_output_pane.py`.
- Verify: `make test`.

### Phase 4 — Semantic boundary (D)
- **Palette → CSS.** Bake the `page.py` palette into `pane.css` as static
  `:root { --bg:…; --card:…; --text:… }`. Delete `pane.py::_pane_css_vars` and
  `app/page.py`. The one brand accent shared with the TUI (`theme.ACCENT`) is
  duplicated in `pane.css` with a comment (one hex; not worth a shared module).
- **Vega theme → client-side.** `charts.py` stops importing colors and emitting a
  themed spec; it emits the semantic spec only. `pane-render.js` `renderChart`
  applies the theme via `cssVar()` (mirror the map renderer). Move the theme
  constants block into the frontend.
- **Table widths/formatters → JS.** `_build_table_data` stops computing
  `minWidth`/`widthGrow`/`rowHeaderWidth` and choosing formatter names; it emits
  semantic `ColumnDesc{field,title,role}`. `pane-render.js` `renderTable` computes
  widths from its rows and maps `role → Tabulator formatter`. Update `CardData`'s
  `ColumnDesc` accordingly.
- Verify: `make test` + `node --check` + **preview smoke with careful eyeballing**
  (this is the visible-behavior phase — confirm tables/charts/maps still render
  identically; the contract test guards the shape, the eyeball guards pixels).

## 7. Risks & notes

- **Asset move (Phase 1)** is the highest-risk step for *silent* breakage — the
  `importlib.resources` base and the server's `/assets/` handler must move in
  lockstep, and `pane-render.js` loads `tabulator`/`vega`/`maplibre` by URL. The
  preview smoke is the guard; don't skip it.
- **Phase 4 is the only behavior-visible phase.** 0–3 are pure refactor/typing.
  If time-boxed, 0–3 capture most of the drift-safety benefit; 4 is the principled
  finish and can land separately.
- **`preview_output_pane.py`** must be updated alongside each phase (it imports the
  moved modules and exercises the real renderer — it's the WYSIWYG check that
  replaced the deleted `gen_debug_html.py`).
- **Import churn** is contained to `app/` + `scripts/` + `tests/`; nothing in
  `chat/`/`toolhub/`/`core/` imports the pane.
