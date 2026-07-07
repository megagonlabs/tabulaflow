# Multi-Record Maps — Design & Implementation Plan

Let a single map overlay layers sourced from **more than one query result**. Today
a map is attached to exactly one `QueryRecord` and every layer reads columns from
that record's single DataFrame. The goal is one map whose layers each name their
own source record — e.g. polygon boundaries from `Q1` and point markers from `Q2`.

> **Status:** proposed. Listed as `- [ ] Multiple records for map` in `README.md`.

---

## 1. Problem & Goal

- A map is currently 1:1 with a query record: `render_map(record_id, map_spec)`
  attaches `map_spec` to `record.map_spec`, and `normalize_map_spec(df, spec)`
  resolves every layer against that one `df`
  (`tabulaflow/toolhub/render_map.py`, `query_history.py:attach_map`).
- The layers people most want to overlay **cannot come from one query**:
  - GeoJSON boundaries from one table + point markers from another — different
    row cardinalities and columns, so no clean `UNION`/join produces them
    together.
  - Two semantically distinct point sets (e.g. warehouses vs. customers) shown as
    separately-styled layers.
- A single query can only fake this with padding/nulls. The one-record limit is a
  structural gap for maps, not a cosmetic one.
- **Goal:** each map layer names its own `record_id`; the map is assembled from
  N query results and rendered as one standalone card.

## 2. Key Decisions (settled)

- **Per-layer `record_id`, required — no top-level default.** Each column-mode
  `points` and `geojson` layer names its own `record_id`; inline `points` layers
  omit it. The tool signature drops `record_id` (`render_map(map_spec)`). A map is
  a standalone artifact assembled from its layers, so a top-level `record_id` is a
  vestige of the deleted attach-to-a-record model. Backward compatibility is not a
  goal.
- **The map is a standalone artifact with its own id.** Drop `QueryRecord.map_spec`;
  store maps as a sibling collection in `QueryHistory` (`_maps`) keyed by a
  **`MAP`-prefixed id** (`MAP1`, `MAP2`, …). `MAP` — not `M` — because `M` is
  already the offloaded-message prefix.
- **Option 1 data model: the map card bundles one dataset per source record.**
  The card's payload carries `datasets: {Q1: {...}, Q2: {...}}` and each layer
  names its `source` record; the browser reads `datasets[layer.source].rows`. A
  single-source map is the degenerate one-dataset case. Chosen over embedding
  materialized features per layer (Option 2): Option 1 is the natural "one table →
  several tables" extension of today's single-dataset renderer, so the JS
  feature-builders change minimally. (Trade-off accepted: Option 1 carries whole
  rows, so it uses more browser RAM than Option 2's drawn-columns-only payload.)
- **Map cards are map-only.** Unlike a chart, a map has no single DataFrame or SQL
  — it is composed from N records, so `Data` and `Query` have no single referent.
  Map cards therefore show only the `map` view, regardless of source count. The
  underlying tables remain available: the agent cites the source `Q*` records
  separately when the user wants them. (A map's raw coordinate table is plumbing,
  not the answer — another reason it needs no `Data` tab, where a chart's rows are
  often meaningful in their own right.)
- **One citation-ordered `artifacts` list; maps are first-class in the TUI too.**
  `ChatResult` holds a single discriminated union
  `artifacts: list[ChatResultRecord | ChatResultMap]` (tagged by `kind`), in
  citation order — replacing the separate `records`/`maps` split so both the pane
  and the TUI render cards in the order the agent cited them. In the terminal a map
  renders as a `VIEW_KIND_MAP` **placeholder card** ("Open the browser pane to view
  this map"), mirroring how a non-renderable chart degrades to a browser card
  (`display._build_chart_card`). So a cited map is visible where the user is typing,
  not only in the browser. `primary_artifact_index` replaces `primary_record_index`.
  The `record → artifact` rename stays scoped to the model layer (`ChatResult`,
  `_artifacts_from_refs`); the pane/TUI `record` symbols (`PaneRecord`,
  `RecordGroup`, `build_result_views`, `turn.records`) still convert in the deferred
  pass.
- **Cited by id, through the existing marker.** The agent cites a map exactly like
  a query result — `[[record:MAP1:label]]` — and `render_map` returns the id so it
  has something to cite. The ref resolver dispatches on the id prefix: `Q*` →
  query-result card, `MAP*` → map card. One citation grammar, one streaming
  router; the prefix is the type, so no per-artifact marker keyword.
- **`record` → `artifact` rename is deferred to a separate pass.** The layer
  *should* standardize on `artifact` (already the storage term via `MapArtifact`),
  but that rename spans Python + the pane JS/CSS + the `turn.records` wire key
  (~40 JS refs, the `.multi-record` classes) and is orthogonal to this feature. To
  keep diffs reviewable it lands **after** the feature as its own mechanical pass
  (see §7). The feature therefore keeps the `[[record:…]]` marker, broadened to
  accept `MAP*` ids.
- **Charts stay single-record.** Overlaying two substantial query results in one
  chart is a rare real-world pattern; `vegalite_spec` remains a per-record field.
  Per-record viz stays on the record; cross-record viz (maps) is a standalone
  artifact.

## 3. Non-Goals

- Multi-record charts (`vegalite_spec` stays single-record).
- Renaming `QueryRecord`/storage vocabulary.
- New layer types, encodings, or basemaps.
- Cross-record linking/selection inside the map (layers are independent).
- Backward compatibility with the old `render_map(record_id, spec)` call shape.

## 4. Map Spec Changes

Add `record_id` to both layer types
(`_PointsLayer` at `render_map.py:90`, `_GeoJsonLayer` at `render_map.py:117`):

```python
record_id: str | None = None   # source query result
```

Semantics:

- **Column-mode `points`** and **`geojson`** layers **require** `record_id` and
  read their columns from that record's DataFrame.
- **Inline `points`** (`points: [...]`) carry their own data → `record_id` must be
  omitted (validation error if present).
- No default: a column/geojson layer without `record_id` is a validation error.

Overlay example (the motivating case):

```json
{
  "title": "Facilities by service area",
  "layers": [
    {"type": "geojson", "record_id": "Q1", "geojson": "service_area_geojson", "label": "service_area"},
    {"type": "points",  "record_id": "Q2", "lat": "facility_lat", "lng": "facility_lng", "label": "facility_name", "tooltip": ["facility_name", "status"]}
  ]
}
```

**The normalized layer carries its resolved `source` record id.** Today
`normalize_map_spec` emits layers with no source tag because there is only one
DataFrame. Downstream needs to know which record's dataset each layer reads, so the
normalized layer dict gains `source` (the resolved record id; absent for inline
layers).

## 5. Agent-Facing Interface Changes

**Signature** — `record_id` removed (`render_map.py:369`):

```python
async def __call__(self, *, map_spec: str) -> str:
```

**Tool body** (`render_map.py:422–457`):

1. Collect referenced ids from column/geojson layers. Error if any such layer
   omits `record_id`.
2. `await history.get()` each referenced id (hydrates spilled DataFrames), and run
   the existing empty / `MAP_RENDER_MAX_ROWS` checks **per record**.
3. Store via `history.add_map(spec) -> map_id` (mints a `MAP*` id).
4. Return `"Map MAP1 created from Q1, Q2 — 312 + 1,204 rows"`.

**Docstring / description.** Add `record_id` to the common-layer-fields block and
the overlay example; describe it plainly:

> `record_id`: query-history record id the layer reads from (e.g. `"Q3"`).
> Required for column and geojson layers; omit for inline `points`.

Update the two `render_map` mentions in `chat/agent.py` (~line 216) to describe
per-layer sourcing and citing the returned `MAP*` id.

## 6. Citation Model

The citation block is unchanged in shape — a run of `[[record:<ID>:<label>]]`
markers, then `---`, then prose (`agent.py:786–886`). The map is cited by its id:

```
[[record:Q1:regions]]
[[record:MAP1:facilities by area]]
---
<answer>
```

- `_QUERY_REF_RE` broadens from `Q\d+` to `(?:Q|MAP)\d+`.
- `_records_from_refs` dispatches on prefix: `Q*` builds a query-result card via
  `query_history.get`; `MAP*` builds a map card via the `_maps` lookup.
- Ordering is preserved: cards render in citation order.

## 7. `record` → `artifact` Rename (deferred — separate pass, after the feature)

| Now | → |
|---|---|
| `[[record:…]]` marker + prompt text | `[[artifact:…]]` |
| `ChatResultRecord` | `ChatResultArtifact` |
| `ChatResult.records` / `primary_record*` | `ChatResult.artifacts` / `primary_artifact*` |
| `PaneRecord` | `PaneArtifact` |
| `record_payload` / `manual_record_turn` | `artifact_payload` / `manual_artifact_turn` |
| `_records_from_refs` | `_artifacts_from_refs` |
| `render_record_data` | `render_artifact_data` |
| `ResultRecordLike` | `ArtifactLike` |

Also the delimiter machinery: `_QUERY_REF_RE`, `_TextStreamRouter._MARKER`,
`_is_citation_block`, `_parse_refs`.

**Not renamed:** the `record_id` *field/value* stays `record_id` — it is the id
minted by `QueryHistory` (storage) and legitimately crosses layers; renaming it
would reach into `query_history` and every tool consumer (the out-of-scope
storage rename). Files: `chat/result.py`, `app/pane_types.py`, `app/render/*`,
`chat/agent.py`, `app/{tui,screens,debug}.py`, and the tests. Done as Phase 2, a
pure refactor verified green before the feature lands. JS payload var names
(`recordData`) are internal and left as-is; only JSON keys that change (`datasets`)
matter across the boundary.

## 8. Storage Changes (`QueryHistory`)

```python
@dataclass
class MapArtifact:
    map_id: str
    map_spec: dict[str, Any]   # layers carry a resolved `source` record id

class QueryHistory:
    _records: dict[str, QueryRecord]   # unchanged
    _maps: dict[str, MapArtifact]      # new
    _next_map_id: int                  # mints MAP1, MAP2, …

    def add_map(self, map_spec: dict[str, Any]) -> str: ...   # returns map_id
    def get_map(self, map_id: str) -> MapArtifact: ...
```

- Remove `map_spec` from `QueryRecord` and remove `attach_map`.
- `add_map` mints `MAP{n}`; the id space is separate from `Q{n}`.
- `attach_chart` / `vegalite_spec` untouched.
- `app/debug.py` gains a parallel path to seed `_maps` for map fixtures.

## 9. Pane Card / Render-Path Changes

A map card is a `PaneArtifact` with `views: ["map"]` whose `.data.json` bundles
per-source datasets:

```json
{
  "map": {"layers": [
    {"type": "geojson", "source": "Q1", "geojson": "f0", "label": "f1"},
    {"type": "points",  "source": "Q2", "lat": "f0", "lng": "f1", "label": "f2"}
  ], "view": {...}},
  "datasets": {
    "Q1": {"rows": [...], "columns": [...]},
    "Q2": {"rows": [...], "columns": [...]}
  }
}
```

- **`app/render/maps.py`**: `build_map_data` takes the spec plus a
  `{record_id: (df, field_by_column)}` map; it resolves each layer against its
  source's `field_by_column`, tags the normalized layer with `source`, and emits
  the `datasets` bundle. Each source's dataset is built with the existing table
  dataset builder so field names (`f0`, `f1`) stay consistent per source.
- **`app/render/cards.py`**: a new `render_map_artifact_data(map_artifact, resolve_df, pane_dir)`
  builds a map-only card (no table/chart/query views), resolving each source df via
  the history. `render_artifact_data` (renamed) keeps handling query-result cards.
- **`chat/result.py`**: a new `ChatResultMap` model (map_id, spec, per-source
  dataframes), added to the `ChatResult.artifacts` discriminated union so query and
  map cards interleave in citation order in both the pane and the TUI.
- **`app/display.py`**: `build_result_views` iterates `artifacts` and dispatches —
  records → Chart/Data/Query groups, maps → a single `VIEW_KIND_MAP` placeholder
  card via `_build_map_card`.
- **`app/assets/pane/pane-render.js`** (`renderMap`, ~994): read
  `recordData.datasets[layer.source].rows` per layer instead of a single
  `recordData.dataset.rows`; feed each layer's rows to the existing
  `buildPointFeatures` / `buildGeoJsonFeatures`. `fieldLabels` resolves per source.

All existing per-layer logic (row limit, coordinate validation, tooltip/label/
color/size resolution) is unchanged — it runs per source DataFrame.

## 10. Implementation Order

1. **Design doc** (this file). ✅
2. **Spec + normalize** — per-layer `record_id`; `normalize_map_spec(spec, sources)`
   with per-source resolution and `source`-tagged layers. Tests in
   `test_render_map.py`.
3. **Storage** — `MapArtifact`, `_maps`, `add_map`/`get_map`; drop
   `QueryRecord.map_spec`/`attach_map`. Tests in `test_query_history.py`.
4. **Tool** — new signature, per-record validation, `add_map`; docstring + example.
5. **Result + citation** — `ChatResultMap`, `MAP` prefix in `_QUERY_REF_RE`,
   prefix dispatch in `_records_from_refs`, prompt update.
6. **Render path** — `build_map_data` datasets bundle, `render_map_card_data`
   map-only card, `pane-render.js` per-source datasets.
7. **Docs + fixtures** — update `map_spec.md`; regenerate debug HTML per the
   dump-demo workflow.

Deferred (separate pass, §7): `record → artifact` rename across Python + pane
JS/CSS + wire.
