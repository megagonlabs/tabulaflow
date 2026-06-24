# Output Pane — Design & Implementation Plan

Live browser pane that shows the agent's cited results (tables/charts) as they
appear, so the user stops manually opening the browser every turn. The TUI stays
the primary interface; the pane is an **additive, output-only** surface.

> **Status (refreshed):** Phases 1–4 are shipped. The pane now uses a
> **turn-selection navigator** (a left rail of turns; only the selected turn
> renders) — an architecture that emerged after the first draft and **subsumed
> the planned viewport-virtualization** (Phase 4). The remaining roadmap is
> Phases 5–8 below.

---

## 1. Problem & Goal

- The agent produces results that are fundamentally **visual** (charts, wide
  tables, media). The terminal can't render these well, which is why HTML
  rendering (now `app/render/`) exists for browser viewing.
- Previously the user had to **manually open the browser per result** (`file://`),
  which (a) is per-turn friction in a chart-iteration loop and (b) **breaks on a
  remote server** (the file is on the server, the browser is on the laptop).
- **Goal:** results the agent cites appear **automatically** in a single,
  persistent browser pane, served over HTTP so it works **local and remote**.

## 2. Key Design Decisions (settled)

- **TUI-primary + output-only pane.** The terminal remains the one place you
  type (fast, always-reachable in-band over SSH). The browser is a *viewer*, not
  a second chat. We are **not** building browser-primary or a second input
  surface.
- **Turn-selection navigator (not a scrolling stack).** The pane is a left
  **turn rail** (one item per turn, labelled by its question) + a centered
  content area that renders **only the selected turn**. New turns auto-append and
  auto-select. Within a turn, cited results are **horizontal record tabs**, and
  each record's Chart/Data/Query views share **one rounded, borderless panel**.
  This replaced the original append-a-card-per-turn stack and means **only the
  active turn holds live iframes** — memory is constant in turn count, so the
  separate viewport-virtualization step is no longer needed.
- **Option 2 serving model** (self-contained files + iframe-per-card, served over
  HTTP, polled index). Chosen over a single-shared-runtime model (Option 3) for:
  **one renderer for pane + sharing** (WYSIWYG, no drift), **durability** (files
  on disk → reconnect re-fetch), and **fault/visual isolation** (one bad result
  can't break the pane). Option 3 stays a *de-risked escalation* only if many
  heavy Vega charts are visible at once — now even less likely given one-live-turn.
- **Content trigger: `cited ⟺ pane`.** Auto-push every result the turn's answer
  cites. Uncited intermediate/scratch results do **not** auto-push. Manual
  exploration ("view this cell/table") pushes on demand.
- **Window trigger: lazy-open, then update silently.** Open on the *first* pushed
  result; subsequent auto-pushes update **without stealing focus**. Manual
  "view this" **does** raise the pane (explicit intent).
- **Remote:** bind `127.0.0.1` only; serve **bundled** assets (never a CDN);
  **degrade gracefully** to TUI-only when port-forwarding is unavailable; serve
  exports as a **download over the tunnel** (artifact lives on the server).

## 3. Non-Goals

- Browser-primary mode / a second interactive chat surface.
- Multi-tenant / auth / hosted share service (single-user localhost tool,
  Jupyter-class — not a web app).
- Edit-and-rerun of previous turns (no notebook cell model).
- Option 3 (single shared runtime) unless concurrently-visible heavy charts
  force it.

---

## 4. Current State (what's shipped)

| Phase | Status | Notes |
|-------|--------|-------|
| **1 — MVP server** | ✅ done | stdlib `http.server` on a daemon thread, loopback + auto free port, serves the dumps dir, polls `/__index__`, lazy-open + URL fallback. |
| **2 — Trigger & interaction** | ✅ mostly | `cited ⟺ pane` auto-push; explorer "view in browser" → `pane.push`; focus asymmetry (auto-push silent, manual view calls `reopen()`); `ctrl+b` re-open. *Polish backlog below.* |
| **3 — Record cards + `render/` split** | ◑ partial | `dump.py → app/render/` split done; Chart\|Data\|Query views done. **Asset-mode split not done** — every card re-inlines Tabulator/Vega. |
| **4 — Scalability** | ✅ via navigator | The turn navigator bounds live iframes to the active turn (constant memory). Table has a row cap + fixed-height cap. Output truncation for huge results and polling→SSE not done. |

**Shipped UI refinements (this work):** turn navigator with auto-advance;
horizontal record tabs + sliding Chart/Data/Query segmented control; one unified
rounded **borderless** panel for all three views; the panel surface lifted to
`#1a212c` so it separates from the page without a border; short results **hug**
the panel (auto-height measures `<body>`; the table uses a fixed-pixel cap so it
hugs short / caps + scrolls long); the data table fills the panel edge-to-edge;
the query view is **SQL syntax-highlighted** (Pygments, mint-accented,
self-contained).

**Reality vs. the original target structure:** the SERVE layer is a single
`app/pane.py` module (the planned `pane/` package with `server.py`/`channel.py`/
`lifecycle.py` was **not** split out — unnecessary at current size). Keep it a
module until it actually grows or a browser-primary mode appears.

## 5. File Structure (current + planned additions)

```
tabulaflow/app/
├── render/                # RENDER — used by pane + (future) export
│   ├── __init__.py        #   re-export public API
│   ├── media.py           #   sniff / serialize / blob rendering
│   ├── tables.py          #   render_table_html + Tabulator JS  (asset mode: Phase 5)
│   ├── charts.py          #   render_chart_html + Vega          (asset mode: Phase 5)
│   ├── cards.py           #   render_record_card → card descriptor; SQL highlight
│   └── export.py          #   ← NEW in Phase 7 (self-contained / inline bundler)
├── pane.py                # SERVE — OutputPane (server thread, push API, pane page).
│                          #   Decoupled from the TUI; the TUI wires into it.
├── page.py                # page shell + web palette (PAGE_BG / CARD_BG / …)
├── runtime_paths.py       # dumps_dir (flat $TMPDIR/tabulaflow today → per-session in P8)
├── session.py  tui.py  screens.py  display.py   # TUI wiring + reuse
└── assets/                # bundled Tabulator/Vega (→ served at /assets in Phase 5)
```

**Dependency rule:** `pane.py` depends on `render/` + a push API, **never** on the
Textual TUI. The TUI wires *into* the pane.

---

## 6. Remaining Roadmap

Each phase is independently inspectable; none requires rework of the shipped
phases. **Recommended order:** 5 → 7 (the asset-mode parameterization that
Phase 5 introduces is what Phase 7's export reuses); 6 and 8 are independent and
can slot in by need.

### Phase 5 — Asset-mode split (efficiency)

**Goal:** stop re-inlining Tabulator/Vega in every card; serve them once. This
finishes the scalability story the navigator started (disk + remote bandwidth at
50+ turns).

**Scope:**
- Parameterize `render/` with an **asset mode**: `linked` (reference
  `/assets/tabulator.min.js` etc., browser-cached once) vs `inline` (today's
  self-contained, for offline/export). Keep `render/` transport-agnostic via an
  asset-base parameter.
- `pane.py` serves `/assets/*` from bundled package resources.
- `render_record_card` uses `linked` for the pane.

**Inspect:** network panel shows Tabulator/Vega fetched **once** across many
cards; a card saved/opened standalone (inline mode) still works offline; existing
render tests + `scripts/gen_debug_html.py` unchanged.

### Phase 6 — Curation (workspace model)

**Goal:** prune the superseded refinement intermediates our append-only model
accumulates. **Pane = curated workspace; TUI = immutable log.**

**Scope:**
- In the **turn rail**: delete a turn (remove the rail item + its `V_/T_/Q_` dump
  files) and **pin** (keep across a "clear others"). Default delete is the firm
  action; an optional hide/collapse is the soft, recoverable one.
- Pruning never touches the TUI conversation history.

**Inspect:** delete a turn in the pane → its rail item + files are gone; the TUI
still shows that turn; a pinned turn survives "clear others." (Simpler than the
old stack's per-card delete — it's just "remove from the rail.")

### Phase 7 — Sharing / export

**Goal:** make an artifact easy to share with others.

**Scope:**
- **`render/export.py`** (inline asset mode from Phase 5): one portable,
  interactive-but-frozen HTML — per artifact / per turn / whole-session report.
- **Picture-only vs with-data** choice (PNG/SVG/spec vs HTML/CSV) so sensitive
  rows don't leak.
- **`/download/<id>` over the tunnel:** serves the export so it reaches the laptop
  (the file lives on the server). Hosted-link (user's own bucket → signed URL)
  stays opt-in; **no hosted share service**.

**Inspect:** export a chart → opens offline (no server); on remote, the export
downloads to the laptop; a chart-only export carries no rows.

### Phase 8 — Remote hardening

**Goal:** safe and robust on shared/remote servers.

**Scope:**
- **Dumps dir:** flat `$TMPDIR/tabulaflow/` → **`$TMPDIR/tabulaflow/<session_id>/`**
  + **0700 dir / 0600 files** (data exposure on shared `/tmp`). `$XDG_RUNTIME_DIR`
  noted as the per-user tmpfs alternative.
- **gzip** responses; **persist the session port** for predictable re-forwarding
  after a tunnel drop.
- *(Optional)* polling → **SSE** with keepalive + Last-Event-ID reconnect.
- Re-confirm: loopback bind, sandboxed iframes, bundled assets, full TUI-only
  degradation when forwarding is unavailable.

**Inspect:** on a multi-user box, dump files aren't world-readable; a dropped
tunnel + reconnect restores the pane from server-side files.

### Polish backlog (small, do anytime)

- **Phase 2 leftovers:** persistent TUI status line (`results → localhost:PORT`);
  a toggle to disable auto-push / auto-open; a subtle per-push `→ pane` indicator;
  graceful-degrade messaging on auto-open failure.
- **Navigator UX:** don't auto-jump to a new turn when the user has scrolled back
  to an older turn (follow-the-latest only when already on the latest).
- **Output caps:** truncate very large tables/charts (bandwidth control on remote;
  the table row cap already exists).

---

## 7. Deferred Decisions / Open Questions

- **Option 3 escalation:** adopt the single-shared-runtime model only if
  concurrently-visible heavy Vega charts strain the browser — now unlikely given
  one-live-turn. Keep `render/` (export) regardless.
- **Polling → SSE timing:** still polling; upgrade in Phase 8 if latency/efficiency
  warrants.
- **Agent-signaled supersession:** later, let the agent mark "this revises the
  prior chart" → auto-collapse — the automatic analog of curation (Phase 6 is the
  manual version).
- **`pane/` package split:** only if `pane.py` grows materially or a
  browser-primary mode emerges; not now (avoid over-abstraction).
