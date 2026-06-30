# Output Pane — Clean-Break Redesign

A from-scratch redesign of the browser output pane's rendering and transport.
The current pane works but pays avoidable costs (reload flicker, per-result
library re-parse, 1 Hz full-list polling). This redesign separates **data from
presentation** and switches the wire to **push**, giving smooth navigation and
bounded long-session cost — while **unifying the live pane and the share-export
path onto one rendering implementation**.

> **Status:** Design approved (full scope: pane + unified export). Not yet
> implemented. Supersedes the iframe-per-dump rendering described in
> `output_pane_plan.md` (the HTTP-server / turn-navigator concepts there still
> hold; only the render unit and transport change).

---

## 1. Problem

The current pane conflates two concerns into a single artifact: a **portable,
self-contained HTML document** (needed for share-export) is *also* the **live
render unit** (loaded in an `<iframe>`). Every weakness follows from that
conflation:

- **Reload flicker.** Switching turns does `innerHTML=''` and rebuilds; switching
  a view sets `frame.src`. Both reload a document and **re-initialize
  Tabulator/Vega from scratch** → blank flash → content pop-in.
- **Per-result library cost.** Each iframe is its own JS realm that re-parses and
  holds a private copy of Tabulator (~460 KB src) / Vega (~0.8 MB src). A
  multi-record turn runs N library copies at once.
- **Height hacks.** Cross-document sizing needs a `ResizeObserver` writing
  `frame.style.height` on every render tick → visible jitter.
- **Poll transport.** The client polls `/__index__` every 1 s and gets the
  **entire** result list back, re-serialized under lock — O(turns)/sec forever,
  up-to-1 s latency.
- **Boilerplate on disk.** Every dump duplicates ~14 KB CSS + ~8 KB JS template +
  page shell.

## 2. Goal & Principles

> The pane is a single-page app with **one** Tabulator runtime and **one** Vega
> runtime loaded once. The server streams **data** (not HTML). Records render
> directly into the DOM. No iframes, ever.

- **Data, not documents.** The server emits row/column/spec/query *data*; the
  browser turns it into widgets with a shared runtime.
- **Push, not poll.** Server-Sent Events deliver only new turns; idle cost is
  zero.
- **One renderer, two packagings.** The same JS render module powers the live
  pane (fetch data) and the share-export (inline data). No second render path.
- **Bounded long sessions.** An LRU mount-cache keeps navigation instant while
  capping memory.
- **Minimal moving parts.** One dynamic endpoint (SSE); everything else is static
  file serving. No build step, no new Python dependencies.

## 3. Architecture Overview

```
ChatResult ── render layer ──▶ <id>.data.json (+ spilled blobs)
                                [~/.tabulaflow/sessions/<session_id>/pane]
                  │
                  └─ PaneTurn manifest ──▶ OutputPane._results ──▶ /events (SSE)
                                                                       │
   browser SPA (loaded once: pane-render.js + Tabulator + Vega) ◀──────┘
        │  on turn: append sidebar item; if on latest, render
        │  on first view: fetch /<id>.data.json, render into a <div>
        └─ LRU mount-cache: switch = visibility toggle; evict → destroy instances
```

- **Transport:** one SSE stream replaces the 1 s poll.
- **Render unit:** a `<div>` rendered by the shared runtime replaces an `<iframe>`
  loading a full document.
- **Persistence:** small `*.data.json` files and `turns.jsonl` live under the
  durable session pane directory, so a resumed session can replay prior output.

## 4. HTTP Wire API

One dynamic endpoint (SSE); everything else is plain static serving from the
session pane directory / package assets.

| Method / path | Type | Purpose |
|---|---|---|
| `GET /` | static | SPA shell (`index.html` + `pane.css` + links to libs & `pane-render.js`). Loaded once. |
| `GET /events` | **SSE (dynamic)** | The only live endpoint. Streams turn manifests; replays backlog on connect. |
| `GET /<recordId>.data.json` | static | One record's `RecordData`. Fetched lazily on first view. |
| `GET /<recordId>/<file>` | static | Spilled media blobs (unchanged spill scheme). |
| `GET /assets/**` | static, `immutable` | Vendored Tabulator/Vega and the shared `pane-render.js`. |

**Removed:** `GET /__index__` (the poll) and the per-result `T_*.html` /
`V_*.html` / `Q_*.html` documents.

### `GET /events` — SSE contract

```
Request:  GET /events     Header: Last-Event-ID: <n>   (EventSource auto-sends on reconnect)
Response: Content-Type: text/event-stream

id: 0
event: turn
data: {"id":0,"title":"...","records":[{"id":"rec_ab12","label":null,"views":["data","query"]}]}

: ping            ← heartbeat (~15s) — detects dead clients, keeps threads tidy

id: 1
event: turn
data: {...}
```

- On connect, replay every turn with `id > Last-Event-ID` (default `-1` → full
  backlog), then block.
- `push()` wakes the handler via a `threading.Condition`; it writes the delta and
  flushes.
- Client disconnect makes `wfile.write` raise → the per-connection thread exits.
  Native `EventSource` handles reconnect/resume with no client code.

`ThreadingHTTPServer` already gives one thread per long-lived connection (1 tab =
1 connection), so SSE needs no new server machinery beyond the condition
variable.

## 5. Data Contracts

**Manifest turn** — what `push()` takes and what crosses `/events` (metadata
only, tiny):

```jsonc
PaneTurn {
  "id": 0,                       // assigned by push()
  "title": "...",
  "user": "...",                 // optional
  "assistant": "...",            // optional
  "source": "manual",            // optional
  "records": [
    { "id": "rec_ab12", "label": "Top schools", "views": ["chart","data","query"] }
  ]
}
```

`views` lists *which* view kinds exist; the payload lives in
`/rec_ab12.data.json`. Record-level `dataset` is shared by table and chart
views so a chart+table record does not duplicate row data:

```jsonc
RecordData {
  "dataset": {                    // present iff data/chart needs rows
    "rows": [ { "c0": ..., "c1": ... } ]
  },
  "table": {                     // present iff a table view exists
    "columns": [ /* Tabulator col defs; formatter as a name: "text"|"media"|"bool" */ ],
    "hasMedia": false, "maxHeight": 640, "rowHeaderWidth": 44,
    "meta": "1,000 rows · 8 columns"
  },
  "chart": {                     // present iff a chart view exists
    "spec": { /* themed Vega-Lite, no data values */ },
    "data": "dataset", "renderer": "svg", "wrapClass": "fill"
  },
  "query": { "sql": "...", "lexer": "sql", "html": "<highlighted fragment>" }
}
```

Every field here is something the current Python **already computes**
(`column_defs`, `rows`, the merged Vega `spec`, `renderer`, `wrap_class`,
sizing). The change is emitting it as JSON instead of string-injecting it into an
HTML template — which also deletes the `</`→`<\/` escaping and
`__DATA__`/`__COLS__` substitution.

Media cells should be represented as structured descriptors in the dataset
instead of pre-rendered HTML. The browser renderer owns DOM creation:

```jsonc
{ "kind": "media", "mime": "image/png", "src": "./rec_ab12/r0_cimg.png", "size": 12031 }
```

Text/numeric/bool cells remain JSON scalars. This keeps the wire contract typed
and avoids embedding HTML in row data.

## 6. Python API

### `OutputPane` (`app/pane.py`)

Signature-compatible with today; internals change.

```python
class OutputPane:
    def __init__(self, pane_dir, *, host=..., port=None, port_range=...): ...
    def start(self) -> None              # binds, serves; sets up self._cond
    def push(self, turn: PaneTurn) -> None   # assigns turn["id"]; append; self._cond.notify_all()
    @property
    def url(self) -> str | None: ...
    def open_browser(self, *, force=False) -> None: ...
    def reopen(self) -> None: ...
    def stop(self) -> None: ...
```

- New internal state: `self._cond = threading.Condition(self._lock)` (SSE wakeup).
- `_results` stays a `list[PaneTurn]` of **manifests** — server RAM is unchanged
  (metadata only; no DataFrames retained). Manifests are also appended to
  `turns.jsonl` and loaded on pane startup.
- TUI call sites (`tui.py:540`, `tui.py:591`) are **unchanged**: still build a
  `PaneTurn` and call `pane.push(...)`.
- Pane data preparation runs off the Textual event loop. The TUI snapshots the
  records needed for pane rendering, hands that work to an executor, then pushes
  the manifest when the `*.data.json` files are ready. Terminal rendering is not
  blocked by large table/media serialization.

### Render layer (`app/render/`) — produces data, not HTML

```python
# pure data builders, shared by pane AND export
build_table_data(df, *, max_rows, inline_cap, max_height) -> dict   # the "table" payload
build_chart_data(df, spec, *, title=None)                 -> dict   # the "chart" payload
build_query_data(sql, *, lexer="sql")                     -> dict   # the "query" payload

# writes <id>.data.json (+ spills blobs); returns the manifest record {id, label, views}
render_record_data(record, pane_dir) -> PaneRecord

# unified export: same data builders → one self-contained file
export_record_html(record_data: dict, out_path: Path) -> None
```

- `build_table_data` is today's `render_table_html` **minus** HTML assembly: it
  keeps column sniffing, formatter assignment, bool/numeric/text classification,
  blob inline-vs-spill, sizing, truncation — returns them as the `table` payload.
- `build_chart_data` is today's `render_chart_html` minus assembly (field-ref
  normalization, line-hover, dark/mint config merge, sizing → `spec` + `renderer`
  + `wrapClass`). It does not inline row values when a shared record dataset is
  available; the renderer attaches `dataset.rows` at mount time.
- `export_record_html` inlines the shared `pane-render.js` + libs + the
  `RecordData` and calls the same `TF.render*` the live pane uses — one rendering
  implementation for both paths.

## 7. Frontend (`app/assets/pane/`)

### Shared render module — `pane-render.js`

Exports a tiny, container-oriented API (generalized from today's inline
templates so it renders into *any* element instead of self-invoking against
`#table` / `#vis`):

```js
TF.renderTable(container, tableData)   // builds a Tabulator into `container`
TF.renderChart(container, chartData)   // vegaEmbed into `container`
TF.renderQuery(container, queryData)   // inserts highlighted fragment + copy button
```

Used verbatim by both the live SPA and `export_record_html`. The table CSS
(`_CUSTOM_CSS`) and chart CSS move into `pane.css`, scoped under a container
class (single app, no iframe isolation needed).

### SPA — `pane.js`

- Open `new EventSource('/events')`; on each `turn` event append a sidebar item;
  if the user is on the latest turn, render it.
- **Render a turn:** for each record, lazily `fetch('/<id>.data.json')` on first
  view and render into a `<div>` via `TF.render*`. Cache the fetched data.
- **Switch turn / record / view:** pure **visibility toggle** of pre-rendered
  containers — no reload, no re-parse.
- **LRU mount-cache:** keep the last N turns (default ~8) mounted; on eviction,
  `destroy()` their Tabulator/Vega instances and drop the DOM (re-render from
  cached data on revisit). N is a one-line tunable.

No `autosize`, no iframe `ResizeObserver` — normal CSS flow handles height
(tables cap + scroll internally; charts size to container).

## 8. Resource Impact

Representative long session: 50 turns, each a ~1k×8 table (~120 KB row JSON) +
a query.

| Axis | Current | New |
|---|---|---|
| **Disk / turn** | data + ~23 KB boilerplate per dump (×N dumps) | data only; ~0 boilerplate |
| **Browser RAM** | iframe realm per result = private library copy (several MB each) | one shared runtime; LRU window of lightweight instances |
| **Server RAM** | manifest metadata (small) | identical (+ one condition var) |
| **Browser CPU** | reparse + re-init on every switch; reflow churn | toggle (≈0); only LRU-evicted turns re-render, from cached data |
| **Server CPU (idle)** | re-serialize whole list every 1 s | zero — work only on `push()` |
| **Network (idle)** | full-list poll every 1 s | zero bytes; content fetched once, cached |
| **Flicker / latency** | blank flash + pop-in; up to 1 s | none; instant |

Disk savings range from ~15–20% (large, data-dominated tables) to ~10–20×
(small, boilerplate-dominated tables). Server RAM is already fine and stays flat;
the substantial wins are browser CPU/RAM, idle server CPU, idle network, and
flicker — with long-session memory now explicitly LRU-bounded.

## 9. Migration / Touch Points

| File | Change |
|---|---|
| `app/pane.py` | Add `/events` SSE handler + `threading.Condition`; drop `/__index__`; static-serve `*.data.json` & blobs (already serves `pane_dir`). |
| `app/pane_types.py` | `PaneTurn` gains `id`; `PaneRecord` becomes `{id, label, views}` (views = kind list). |
| `app/render/tables.py` | Extract `build_table_data` (data) from `render_table_html` (assembly). |
| `app/render/charts.py` | Extract `build_chart_data`; keep theming/normalization. |
| `app/render/cards.py` | `render_record_data` writes `<id>.data.json`; add `export_record_html`. |
| `app/assets/pane/` | New `pane-render.js`; rewrite `pane.js` (EventSource + LRU mount-cache); fold render CSS into `pane.css`. |
| `tui.py` | Unchanged call sites; `_push_turn_to_pane` builds data via the new builders. |
| `scripts/preview_output_pane.py`, `gen_debug_html.py` | Repoint to data builders / `export_record_html`. |

TUI-side widgets (`widgets.py`) are **out of scope** for this redesign (separate
surface, separate follow-up if desired).

## 10. Risks & Mitigations

- **CSS isolation loss (no iframe).** Mitigate by scoping all render CSS under a
  container class; Vega/Tabulator already namespace their own DOM. Single app, so
  no untrusted-content concern.
- **One SSE thread per open tab.** Bounded in practice (a few tabs); heartbeat
  reaps dead connections.
- **Large data files fetched on view.** Table virtual DOM already bounds render;
  data fetch is one-time and cached. Media stays spilled, served on demand.
- **Two consumers of the data contract (pane + export).** That's the intended
  unification — a contract change updates both paths through the same builders.

## 11. Implementation Order

1. **Data builders + `RecordData` contract** — `build_table_data` /
   `build_chart_data` / `build_query_data`; `render_record_data` writes
   `*.data.json`. (Foundation for both pane and export.)
2. **Shared `pane-render.js`** — generalize current inline templates to
   container-oriented `TF.render*`; unit-render against a data file.
3. **SSE backend** — `/events` + condition var in `OutputPane`; drop
   `/__index__`.
4. **SPA rewrite** — `EventSource` + lazy fetch + LRU mount-cache.
5. **Unified export** — `export_record_html` on the shared module; repoint
   `render_*_html` callers / scripts.
6. **Cleanup** — remove the old template injection and dead HTML-doc paths.
</content>
</invoke>
