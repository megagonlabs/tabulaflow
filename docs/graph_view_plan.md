# Graph View (Node-Link) — Design & Implementation Plan

> **Update:** Neo4j-native node/relationship/path results are now attached
> automatically to cited `Q<n>` query records as a `Graph | Table | Query` card.
> The `render_graph` tool is reserved for explicit node/edge specs and no longer
> supports the older `subgraph` spec mode described in this historical plan.

## Goal

Add a **graph / node-link visualization** to the output pane, alongside the
existing table, chart, and map views. It renders results whose shape is a graph:
Neo4j/Cypher subgraphs (cypherbench), many-to-many association networks, data
lineage / dbt DAGs, self-referential hierarchies (org charts, category trees),
and the FK/ER schema graph.

A graph is a **standalone artifact**, modeled exactly like the map artifact
(`render_map` → `MAP<n>`): the agent calls `render_graph(...)`, gets back a
`GRAPH<n>` id, and cites that id to show the graph. It is a **view-only card**
(`views == ["graph"]`) — no Data/Query tabs; if the user needs the underlying
rows or SQL, the agent additionally cites the source `Q<n>` records as their own
cards.

Hard constraints (same as the map renderer): **no API key, no external services,
bundle the JS locally.**

This plan is self-contained. It assumes the reader has not seen the prior design
discussion. Read `tabulaflow/toolhub/render_map.py`, `tabulaflow/app/pane/maps.py`,
and `tabulaflow/app/pane/cards.py` first — graph mirrors all three.

## Why an artifact (like map), not an attached view (like chart)

The codebase has two established patterns:

- **Attached view** — `attach_chart(source_id, spec)` puts a Vega spec on one
  `QueryRecord`; it renders as a `Chart | Data | Query` tab strip on that
  source's card. Correct for a chart: it is *one lens on one DataFrame*.
- **Standalone artifact** — `add_map(spec) → "MAP1"` stores a `MapArtifact` in a
  registry parallel to `QueryRecord`; each layer names the `source_id` it reads
  from, so one map can overlay several query results. Cited by its own id.

A graph composes potentially **multiple** results (a nodes table + an edges
table, or several edge types) and is a distinct object not tied to any single
DataFrame — so it follows the **map/artifact** pattern, not chart's attach
pattern. The single-source edge-list graph is just an artifact with one source;
nothing is special-cased.

## Library choice: Cytoscape.js

Bundle **Cytoscape.js** (MIT) + the **dagre** layout extension, locally, exactly
as MapLibre is bundled. Rationale (short version — full comparison lives in the
design discussion, not repeated here):

- It is the one library that cleanly spans all three layout families we need —
  **force** network, **layered DAG** (dagre) for lineage, **tree** — under one
  uniform `layout` API and one data model.
- Declarative stylesheet maps 1:1 onto our semantic color encoding, keeping the
  agent spec semantic and the renderer owning the palette — same split as the
  map.
- Canvas 2D, **not WebGL**: no WebGL-context cap, so lifecycle management is
  simpler than the map's (just `cy.destroy()` on hide).
- Built-in node dragging (`grabbable`, default on) and edge-label auto-rotation
  (`text-rotation: autorotate` follows the edge angle live as nodes move).
- Deterministic layouts (`dagre`, `breadthfirst`, `grid`) → reproducible static
  exports for lineage/trees (see Determinism below).

Bundle: `cytoscape.min.js`, `dagre.min.js`, `cytoscape-dagre.min.js`. Force uses
Cytoscape's built-in `cose` (no extension); `fcose` is an optional later upgrade.

---

## 1. Agent-facing graph spec

A graph spec is a JSON object. It has **three source kinds**, all optional but at
least one edge-bearing source required:

- `nodes: [...]` — node sources (node identity + attributes).
- `edges: [...]` — edge sources (the topology).
- `subgraph: [...]` — Cypher records whose native graph objects are auto-walked
  (Phase 3).

Plus top-level `title` (string, optional) and `layout`
(`"force" | "layered" | "tree"`, optional, default `"force"`).

Each `nodes`/`edges` entry reads from **either** a query result (`source_id`)
**or** inline literal data (`data`) — never both. Field keys
(`id`/`label`/`group`/`source`/`target`/`tooltip`) name **columns** of the
named record in column mode, or **property names** of the inline objects in
inline mode.

> **Naming note for implementers:** edge endpoint columns are `source` and
> `target`. The *source* is always `source_id` — never `source`. (This
> differs from the map's normalized output, where `source` tags the source id.
> Do not copy that convention here.)

### 1.1 Node source

| Field | Required | Description |
|---|---|---|
| `source_id` | column mode | Output-store record the node rows come from (`"Q1"`). |
| `data` | inline mode | Non-empty list of literal node objects. Mutually exclusive with `source_id`. |
| `id` | yes | Column/property holding the node's unique id. Edge endpoints join to this. |
| `label` | no | Short display caption. Defaults to the id. |
| `group` | no | Field name for categorical color, e.g. `"type"` (a plain string; the pane chooses the palette). |
| `tooltip` | no | Column/property, list, or `true` (all safe scalar fields). |

### 1.2 Edge source

| Field | Required | Description |
|---|---|---|
| `source_id` | column mode | Output-store record the edge rows come from. |
| `data` | inline mode | Non-empty list of literal edge objects. Mutually exclusive with `source_id`. |
| `source` | yes | Column/property holding the source node id. |
| `target` | yes | Column/property holding the target node id. |
| `label` | no | Edge caption (rendered along the edge, auto-rotated). |
| `directed` | no | Bool; draw an arrowhead. Default `true`. |
| `tooltip` | no | Column/property, list, or `true`. |

### 1.3 Node derivation and joins

- `edges` `source`/`target` values join to `nodes` `id` values **across all
  sources** (a node source and edge source may be different records).
- If **no `nodes` source** is given, nodes are the distinct endpoints of the
  edge list; each node's id is its label.
- Node ids are **deduped across all node sources and endpoints**. If the same id
  appears in multiple node sources, the first wins (later attributes ignored;
  do not error).
- An edge endpoint id **not present** in any node source is auto-created as an
  id-only node. Count these and emit `meta.unmatchedNodes` (non-blocking; the
  pane may show a small warning later — analogous to the map's skipped-row
  metadata).

### 1.4 Examples

Edge-only, single source (nodes implicit):

```json
{ "edges": [{ "source_id": "Q1", "source": "src", "target": "dst", "label": "rel" }] }
```

Normalized two-source with encodings:

```json
{
  "title": "Collaboration network",
  "layout": "force",
  "nodes": [
    { "source_id": "Q1", "id": "id", "label": "name",
      "group": "type", "tooltip": ["name","type"] }
  ],
  "edges": [
    { "source_id": "Q2", "source": "from_id", "target": "to_id",
      "label": "rel", "directed": true, "tooltip": ["rel"] }
  ]
}
```

Inline (authored diagram — Phase 2):

```json
{
  "title": "ETL pipeline", "layout": "layered",
  "nodes": [{ "data": [
      {"id":"extract","name":"Extract","kind":"source"},
      {"id":"transform","name":"Transform","kind":"step"},
      {"id":"load","name":"Load","kind":"sink"}],
    "id":"id", "label":"name", "group":"kind" }],
  "edges": [{ "data": [
      {"from":"extract","to":"transform","rel":"feeds"},
      {"from":"transform","to":"load","rel":"feeds"}],
    "source":"from", "target":"to", "label":"rel", "directed":true }]
}
```

Cypher auto-extract (Phase 3 — near-spec-free; one record yields both nodes and
edges from its native objects):

```json
{ "subgraph": [{ "source_id": "Q1", "caption": "title" }] }
```

`caption` (default: `name`/`title`/first string prop) is the only optional
override. Node grouping/coloring comes from Neo4j labels.

---

## 2. Architecture & data flow

Every step below has a direct map counterpart — reuse its shape. Respect the
import-linter layers: the tool lives in `toolhub`, the pane builder in
`app/pane`.

```
render_graph tool                output_store                pane render (browser-side)
─────────────────                ─────────────                ──────────────────────────
render_graph(*, graph_spec) ──►  add_graph(spec) → "GRAPH1"
  parse + validate spec          GraphArtifact(graph_id,
  resolve columns vs source        graph_spec)  in _graphs
  DataFrames; store normalized
  spec (original col names)

agent cites "GRAPH1" in answer
  _artifacts_from_refs           get_graph("GRAPH1")
  ref.startswith("GRAPH")
  _chat_result_graph_from_artifact
    gather source DataFrames
    → ChatResultGraph(graph_id,
        label, graph_spec, sources)

app/tui.py snapshot dispatch     render_graph_data(snap, dir)  window.TF.renderGraph(node, data)
  kind == "graph" → SimpleNamespace  build per-source datasets    cytoscape({ elements, style,
    (graph_id,label,graph_spec,      build_graph_data(spec,          layout })
     sources)                        sources) → materialized       drag, autorotate labels,
                                     elements + meta                tooltips, lazy-init/destroy
                                     → card json, views=["graph"]
```

### 2.1 Tool (`tabulaflow/toolhub/render_graph.py`) — mirror `render_map.py`

- Pydantic models with `extra="forbid"`: `GraphNodeSourceSpec`, `GraphEdgeSourceSpec`,
  `_GraphSpec` (`title`, `layout`, `nodes`, `edges`, `subgraph`). Node `group`,
  edge `source`/`target`/`label`, and `tooltip` are plain `str | None`
  (or `str | list[str] | Literal[True]` for tooltip) field names — **not**
  encoding objects. v1 keeps `group: "type"` as a simple column/property name;
  the pane owns the palette. `directed` is `bool = True` per edge source.
  `layout` is `Literal["force","layered","tree"]`.
- `parse_graph_spec(spec) -> _GraphSpec` (raise `GraphSpecError` with a friendly
  message — copy `_validation_message`).
- `referenced_source_ids(parsed) -> list[str]` over all `nodes`/`edges`/`subgraph`
  entries that carry a `source_id`.
- `normalize_graph_spec(parsed, sources: Mapping[str, pd.DataFrame]) -> dict`:
  validate each entry's referenced columns exist in `sources[source_id]`
  (case-insensitive via `resolve_column`), verify ≥1 edge row overall, tag each
  entry with its `source_id`. Store original column names (the pane rewrites to
  compact field names later, exactly like maps).
- `RenderGraphTool.__call__(self, *, graph_spec: str) -> str`: parse JSON →
  parse spec → collect `referenced_source_ids` → fetch each from
  `self._history.get(rid)` (error on unknown/empty) → `normalize_graph_spec` →
  enforce **graph-specific element caps** (not a row cap) → `add_graph` → return
  `f"{label} {graph_id} created from {...} — {n} nodes, {m} edges"`.
- Element caps — driven by **readability + interaction smoothness**, not the raw
  canvas draw ceiling: `GRAPH_MAX_NODES = 500`, `GRAPH_MAX_EDGES = 1_500`.
  Cytoscape's canvas renderer sails past Neo4j Browser's ~100-node wall (that
  wall is SVG-DOM churn during D3 force ticks, which canvas + settle-then-stop
  avoids), but our label-heavy styling (per-node labels, autorotate edge labels,
  bezier edges) gets sluggish approaching ~1k, and the **layout computation**
  janks before rendering does. More to the point, a force graph past a few
  hundred nodes is an unreadable hairball — so the *comfortable* range is lower,
  ~100–300. Check against total node rows and total edge rows across sources (a
  safe pre-assembly upper bound); reject with a hint to aggregate / take top-N
  (e.g. by degree) in SQL.
  - These numbers are **provisional** — set the final caps from a spike
    (100/500/1000-node fixtures in the debug pane), not a guess.
  - `force` is the tightest constraint; `layered`/`tree` (dagre — structured,
    deterministic, one-shot) stay readable at higher counts. v1 uses one cap for
    simplicity; if we later split, keep the `force` cap lowest.
- `as_pydantic_ai_tool()`. Write the docstring in the same style as
  `render_map` (grammar + minimal examples); **describe functionality only, no
  lecturing** (per AGENTS.md).

### 2.2 Output store (`tabulaflow/toolhub/output_store.py`)

Add, mirroring `MapArtifact`/`add_map`/`get_map`/`_maps`/`_next_map_id`:

```python
@dataclass
class GraphArtifact:
    graph_id: str
    graph_spec: dict[str, Any]

# in OutputStore.__init__: self._graphs = {}; self._next_graph_id = 1
def add_graph(self, graph_spec) -> str: ...   # "GRAPH1", ...
def get_graph(self, graph_id) -> GraphArtifact: ...
```

Export `GraphArtifact` where `MapArtifact` is exported (`toolhub/__init__.py`).

### 2.3 Chat result type (`tabulaflow/chat/result.py`) — mirror `ChatResultMap`

```python
class ChatResultGraph(BaseModel):
    kind: Literal["graph"] = "graph"        # match the discriminator ChatResultMap uses
    graph_id: str
    label: str | None
    graph_spec: dict[str, Any]
    sources: dict[str, pd.DataFrame]
    # copy the field_serializer / field_validator that (de)serialize `sources`
```

Add `ChatResultGraph` to the `ChatResult.artifacts` union and its exports.

### 2.4 Citation resolution (`tabulaflow/chat/agent.py`)

In `_artifacts_from_refs`, add a branch before/after the `MAP` branch:

```python
elif ref_id.startswith("GRAPH"):
    graph_artifact = output_store.get_graph(ref_id)   # try/except KeyError,ValueError: continue
    artifacts.append(await _chat_result_graph_from_artifact(graph_artifact, label, output_store))
```

Add `_chat_result_graph_from_artifact` — copy `_chat_result_map_from_artifact`
verbatim: walk `graph_spec` `nodes`/`edges`/`subgraph` entries for `source_id`s,
fetch each source DataFrame, return `ChatResultGraph(...)`.

**Update the citation ref regex** (`_ARTIFACT_REF_RE` in `chat/agent.py`): the
id alternation is currently `(?:Q|MAP)\d+` — change it to `(?:Q|MAP|GRAPH)\d+` so
`GRAPH<n>` refs are extracted from the answer. The prefixes don't collide
(`"GRAPH".startswith("MAP")` is false and vice-versa), so `_artifacts_from_refs`
branching by prefix is safe.

Register the tool: add `render_graph: RenderGraphTool` to `_Toolset`, construct
it in `_build_tools` (`RenderGraphTool(output_store=self._output_store)`), and add
`self._tools.render_graph.as_pydantic_ai_tool()` to the `tools=[...]` list. Add a
one-line usage note to the system prompt next to the `render_map` note (~line
218): "Call `render_graph` for graph/network results (node-link). It returns a
`GRAPH<n>` id; cite it to show the graph."

### 2.5 Terminal placeholder (`tabulaflow/app/display.py`) — mirror map

Graphs don't render in the terminal. In `build_card_views`, add a
`ChatResultGraph` branch that appends a single `ViewItem(kind=VIEW_KIND_GRAPH,
renderable=_build_graph_card(artifact.graph_spec))` placeholder; add
`VIEW_KIND_GRAPH` and a `_build_graph_card` placeholder builder (copy
`_build_map_card`). In the DataFrame-release loop, set `artifact.sources = {}`
for `ChatResultGraph` too.

### 2.6 TUI snapshot + pane dispatch (`tabulaflow/app/tui.py`)

In the artifact-snapshot loop, add `artifact.kind == "graph"` →
`("graph", SimpleNamespace(graph_id=..., label=..., graph_spec=...,
sources=dict(artifact.sources)))`. In `render_cards`, dispatch:
`render_graph_data(snap, pane_dir) if kind == "graph" else ...`. Import
`render_graph_data` alongside `render_map_data`.

### 2.7 Pane payload builder (`tabulaflow/app/pane/graphs.py` + `cards.py`)

Add `render_graph_data(graph_record, pane_dir) -> PaneCard | None` to
`app/pane/cards.py`, copying `render_map_data`:

- Add a `GraphArtifactLike` Protocol (`graph_id`, `label`, `graph_spec`,
  `sources`).
- For each source df, build a compact dataset via `_build_table_data`
  (`max_height=None`), collecting `rows`, `columns`, `field_by_column` into
  `sources_payload[source_id]` — identical to `render_map_data`.
- Call `build_graph_data(graph_spec, sources_payload)`; write
  `{card_id}.data.json`; return `card_payload(card_id=card_id,
  label=graph_record.label, views=["graph"])`.

Add `tabulaflow/app/pane/graphs.py` with
`build_graph_data(graph_spec, sources) -> GraphCardData | None`. **Key
divergence from `build_map_data`:** because edges join to nodes across sources,
graphs **fully materialize** concrete Cytoscape elements in Python rather than
shipping field references + datasets for the JS to resolve. This keeps the JS
renderer trivial and puts the cross-source join where it belongs (Python, with
the row values in hand).

`build_graph_data` steps:
1. For each `nodes` entry: read `sources[source_id].rows` (or the inline `data`);
   rewrite column names → compact field names via that source's
   `field_by_column`; emit node records `{id, label, group?, tooltip?}`.
2. Assemble the merged node set; dedup by `id` (first wins).
3. **Precompute presentation** (the pane owns the palette, so do it here, in
   Python, not in the stylesheet):
   - `color`: map each distinct `group` value → a stable categorical palette
     entry (a fixed hex list in `app/pane/graphs.py`); write it to each node's
     `data.color`. **Do not** rely on Cytoscape `mapData` for categories —
     `mapData` is numeric. Nodes without a `group` get the default mint.
4. For each `edges` entry: read rows; resolve `source`/`target`; for endpoints
   not already a node, create an id-only node and increment `unmatchedNodes`.
   Emit edge records `{id (synth), source, target, label?, directed, tooltip?}`
   — carry `directed` **per edge** in `data.directed` (mixed directed/undirected
   graphs must work; there is no top-level `directed`).
5. Return Cytoscape-ready:
   ```json
   {
     "graph": {
       "layout": "force",
       "elements": {
         "nodes": [{"data": {"id":"n1","label":"…","group":"team-a","color":"#3eb489"}}],
         "edges": [{"data": {"id":"e1","source":"n1","target":"n2","label":"…","directed":true}}]
       },
       "meta": {"unmatchedNodes": 0}
     }
   }
   ```
   Return `None` if there are no valid edges (mirrors `build_map_data` returning
   `None` on no valid layer).

### 2.8 Pane types (`tabulaflow/app/pane/types.py`)

- `ViewKind = Literal["map", "chart", "data", "query", "graph"]`; add `"graph"`
  to `VIEW_KINDS`.
- Add `GraphData` / `GraphCardData` TypedDicts (`graph: {...}` per §2.7) and add
  `graph` to the `CardData` union.

### 2.9 Browser renderer (`tabulaflow/app/pane/assets/pane/`)

**`pane.js`**
- Dispatch (~line 273): `if (kind === 'graph') return TF.renderGraph(node, data);`
- View ordering (~line 228): `if (entry.kind === 'graph') return 3;` (peer of map).
- Wherever a kind→label map produces tab captions, add `graph → "Graph"`.
- `turnMeta()` — include graph cards in the sidebar turn summaries (mirror how
  `map` cards are counted/labeled).
- `cacheEntryWeight()` — treat `graph` views as heavy cached views like `map`
  (a live Cytoscape instance holds a canvas + layout state), so eviction
  accounts for them correctly.

**`pane-render.js`**
- Add `function renderGraph(container, cardData)`:
  - `container.className = 'tf-view tf-graph-view';`
  - Read `cardData.graph.elements`, `.layout`, `.directed`.
  - **Lazy-init on visibility** and **`cy.destroy()` on hide** — return the same
    `{ afterVisible, afterHidden, destroy }` lifecycle object the other
    renderers return (copy `renderMap`'s lifecycle shape).
  - `cytoscape({ container, elements, style, layout })`.
  - Layout map: `force → { name: 'cose' }` (or `fcose` if bundled),
    `layered → { name: 'dagre', rankDir: 'TB' }`, `tree → { name: 'breadthfirst' }`.
  - Stylesheet (dark/mint theme, see Design Language in AGENTS.md). Presentation
    is **precomputed into element data** by `build_graph_data`, so the stylesheet
    just reads it — no `mapData`:
    - `node`: `background-color: data(color)` (mint `#3eb489` default is baked in
      when `color` is absent); fixed `width`/`height`; `label: data(label)`;
      `text-valign/halign` centered/right.
    - `edge`: `curve-style: bezier`; `label: data(label)`;
      `text-rotation: autorotate`; `text-margin-y: -8`; muted stroke (`#6a737d`).
      Arrowheads are **per edge**: a selector `edge[?directed]` (or
      `edge[directed]`) sets `target-arrow-shape: triangle`, so a graph can mix
      directed and undirected edges.
  - **Performance** (main-thread canvas): set `hideEdgesOnViewport: true` and
    `textureOnViewport: true` so pan/zoom stays fluid on dense graphs; add
    `min-zoomed-font-size` so labels drop out when zoomed away; and **stop the
    layout on convergence** — don't run an open-ended force sim (bound `cose`
    iterations / handle the `layoutstop` event). For the largest graphs,
    `curve-style: haystack` is much cheaper than bezier, trading off edge labels.
  - Node dragging is on by default (`grabbable`). Add hover/click tooltips via a
    lightweight popper/HTML overlay (reuse the map popup CSS classes
    `tf-map-detail-*` or add `tf-graph-detail-*`); tooltip content from
    `data.tooltip`. HTML-escape all label/tooltip text.
- Register in `window.TF` (~line 1430): `renderGraph: renderGraph`.

**`index.html`** — add before `pane-render.js`:
```html
<script src="/assets/cytoscape/cytoscape.min.js"></script>
<script src="/assets/cytoscape/dagre.min.js"></script>
<script src="/assets/cytoscape/cytoscape-dagre.min.js"></script>
```
Bump `__PANE_RENDER_VERSION__` (cache-bust) as other pane-render.js changes do.

**Assets** — add `tabulaflow/app/pane/assets/cytoscape/` with the three files
above (vendored, like `assets/maplibre/`). Add any CSS the pane serves; add
`.tf-graph-view` rules to the pane stylesheet.

**Packaging** — vendored assets are only shipped if listed in `pyproject.toml`
`package-data` (currently enumerates `maplibre/`, `tabulator/`, `vega/`, …). Add
the `cytoscape/` glob there, or the assets will be missing from installed builds.

---

## 3. Determinism / export path

The interactive pane may use a force layout, but the static export/dump path
(`scripts/gen_debug_html.py`, `dump.py`) must be reproducible.

- `layered` (dagre) and `tree` (breadthfirst) are **deterministic** given a fixed
  element order → reproducible for free. Emit nodes/edges in a **stable sorted
  order** from `build_graph_data`.
- `force` (`cose`): set `randomize: false` so it seeds from initial positions;
  with stable input order this is deterministic enough for dumps. If exact
  reproducibility is needed, precompute positions in `build_graph_data` and emit
  them as a `preset` layout for the export path.

After any `dump.py` / `page.py` rendering change, follow the repo workflow: run
`uv run scripts/gen_debug_html.py` and open the emitted `file://` URLs. Add a
graph fixture (both a force network and a dagre lineage DAG) to the debug HTML
gallery.

---

## 4. Phased implementation (inspect between phases)

**Phase 1 — Foundation (column mode, the whole vertical slice).**
`nodes`/`edges` column sources (single + multi-record), force/layered/tree,
color encoding, full plumbing (tool → output store → citation → chat result →
tui snapshot → `render_graph_data` → `build_graph_data` → `renderGraph`), assets,
CSS, view-only card, terminal placeholder. Ship the whole path for column mode
before anything else. Add unit tests mirroring the render_map / build_map_data
tests. *State after phase:* agent can `render_graph` from query results and cite
`GRAPH<n>`; draggable nodes, autorotating edge labels, tooltips, three layouts.

**Phase 2 — Inline mode.** Accept `data: [...]` on `nodes`/`edges` entries
(mutually exclusive with `source_id`); field keys resolve against inline object
properties. A resolver branch only — no artifact/renderer changes. Enables
authored diagrams and inline annotation overlays on record-backed graphs.

**Phase 3 — Cypher auto-extract (`subgraph`).** A `subgraph: [{source_id,
caption?, group?}]` source whose resolution **walks native
`neo4j.graph.Node/Relationship/Path` objects** into `{nodes, edges}`.
- Prerequisite to verify first: those objects live in result cells
  (`Neo4jConnector.run_query_async` uses `to_df(expand=False)`) but are very
  likely stringified by pane serialization (`json.dumps(default=str)`). The
  extractor must run **before** that — put it in the Neo4j connector or a
  Cypher-specific normalizer (`core`/`datasources`/`toolhub` layer), emitting the
  generic `{nodes, edges}`; **the renderer never learns about Neo4j.**
- Only fires when the Cypher `RETURN`s node/rel/path objects; scalar projections
  still use Phase 1 column mode.

---

## 5. Validation rules (tool, fail fast)

Reject with a clear message when:
- JSON is invalid or not an object.
- No edge-bearing source (`edges`/`subgraph`) is present, or all edge sources are
  empty.
- A `nodes`/`edges` entry sets both `source_id` and `data`, or neither.
- A referenced `source_id` is unknown or its result is empty.
- A referenced column does not exist in its source (list available columns).
- Total node rows exceed `GRAPH_MAX_NODES` or total edge rows exceed
  `GRAPH_MAX_EDGES` (suggest filter/aggregate).
- `layout` is not one of `force`/`layered`/`tree`.

Non-fatal (skip + count): dangling edge endpoints → `meta.unmatchedNodes`.

---

## 6. Testing & dev workflow

- Unit-test the tool and `build_graph_data` mirroring the existing render_map /
  `build_map_data` tests (`tests/`): spec validation, column resolution, node
  dedup, dangling-endpoint counting, multi-source merge, each layout.
- Preview fixtures live: `uv run scripts/preview_output_pane.py --port 61211`
  (add a graph fixture). For layout/theming iteration, serve the live debug pane
  and inspect DOM geometry via the browser tool.
- Because this is a **canvas** renderer, a browser smoke test is worth it: after
  `renderGraph` runs, assert the Cytoscape canvas is present and non-blank and
  that node/edge counts and bounding geometry match the payload (e.g.
  `cy.nodes().length`, `cy.edges().length`, non-empty `cy.elements().boundingBox()`).
  Don't rely *only* on screenshots, but don't skip visual verification either —
  pair the geometry/count assertions with tests and lint.
- `make format && make lint && make mypy && make test` before finishing; scope
  ruff/git to changed files only.
- Do not commit until each phase's changes have been inspected.

---

## 7. Non-goals (v1)

Deferred (revisit only on real need): clustering / graph collapse, expand-on-
click exploration, edge bundling, WebGL/large-scale rendering (Sigma/NVL tier),
Sankey / flow-magnitude diagrams (that is a chart grammar, not node-link),
freehand authoring with no data behind it beyond the inline path, table↔graph
linked selection, and graph exports beyond the existing pane/export path.

## 8. File change checklist

- `docs/graph_view_plan.md` (this file)
- `tabulaflow/toolhub/render_graph.py` (new)
- `tabulaflow/toolhub/output_store.py` (`GraphArtifact`, `add_graph`, `get_graph`)
- `tabulaflow/toolhub/__init__.py` (exports)
- `tabulaflow/chat/result.py` (`ChatResultGraph`, union)
- `tabulaflow/chat/__init__.py` (export `ChatResultGraph`)
- `tabulaflow/chat/agent.py` (citation branch, `_chat_result_graph_from_artifact`,
  `_Toolset` field, `_build_tools`, `tools=[...]`, system-prompt note, ref regex)
- `tabulaflow/app/display.py` (`VIEW_KIND_GRAPH`, `_build_graph_card`, branch)
- `tabulaflow/app/tui.py` (snapshot branch, dispatch, import)
- `tabulaflow/app/pane/cards.py` (`GraphArtifactLike`, `render_graph_data`)
- `tabulaflow/app/pane/graphs.py` (new — `build_graph_data`)
- `tabulaflow/app/pane/types.py` (`ViewKind`, `VIEW_KINDS`, `GraphData`/`GraphCardData`, `CardData`)
- `tabulaflow/app/pane/__init__.py` (export `render_graph_data`)
- `tabulaflow/app/pane/assets/cytoscape/*` (new vendored JS)
- `tabulaflow/app/pane/assets/pane/index.html` (script tags, version bump)
- `tabulaflow/app/pane/assets/pane/pane.js` (dispatch, ordering, label,
  `turnMeta`, `cacheEntryWeight`)
- `tabulaflow/app/pane/assets/pane/pane-render.js` (`renderGraph`, `window.TF`)
- pane CSS (`.tf-graph-view`, `.tf-graph-detail-*`)
- `pyproject.toml` (`package-data`: add `cytoscape/` assets glob)
- `tests/` (new tool + `build_graph_data` tests; update `tests/test_result_views.py`,
  `tests/test_pane_contract.py`, `tests/test_tool_labels.py` for the new view kind,
  artifact, and tool)
- graph fixture in the debug HTML gallery
