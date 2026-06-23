# Output Pane — Design & Implementation Plan

Live browser pane that shows the agent's cited results (tables/charts) as they
appear, so the user stops manually opening the browser every turn. The TUI stays
the primary interface; the pane is an **additive, output-only** surface.

---

## 1. Problem & Goal

- The agent produces results that are fundamentally **visual** (charts, wide
  tables, media). The terminal can't render these well, which is why `dump.py`
  already exists to render them to HTML for browser viewing.
- Today the user must **manually open the browser per result** (`file://`),
  which (a) is per-turn friction in a chart-iteration loop and (b) **breaks on a
  remote server** (the file is on the server, the browser is on the laptop).
- **Goal:** results the agent cites appear **automatically** in a single,
  persistent browser pane, served over HTTP so it works **local and remote**.

## 2. Key Design Decisions (settled)

- **TUI-primary + output-only pane.** The terminal remains the one place you
  type (fast, always-reachable in-band over SSH). The browser is a *viewer*, not
  a second chat. We are **not** building browser-primary or a second input
  surface — that would be duplication and would lose the terminal's
  free reachability on locked-down servers.
- **Option 2 serving model** (file + linked shared assets + iframe-per-card,
  served over HTTP). Chosen over a single-shared-runtime model (Option 3)
  because it gives: **one renderer for pane + sharing** (WYSIWYG, no drift),
  **durability** (files on disk → reconnect re-fetch), and **fault/visual
  isolation** (one bad agent-rendered result can't break the pane). Option 3 is a
  *de-risked escalation* only if many heavy Vega charts are visible at once.
- **Content trigger: `cited ⟺ pane`.** Auto-push every result the turn's answer
  cites (all cited tables + charts, uniformly — a rendered+cited chart is just a
  cited result). Uncited intermediate/scratch results do **not** auto-push.
  Manual exploration ("view this cell/table") pushes on demand.
- **Window trigger: lazy-open, then update silently.** Open the pane on the
  *first* pushed result (env-aware), then update it **without stealing focus**
  on subsequent pushes (no terminal↔browser focus ping-pong). Manual "view this"
  *does* focus the pane (explicit intent).
- **Scalability:** automatic **virtualization + output truncation** for resource
  bounds; **curation** (delete/collapse/pin) for navigability. Needed because,
  unlike Jupyter's edit-and-rerun, our sessions are **append-only** and grow
  monotonically.
- **Dump location:** `$TMPDIR/tabulaflow/<session_id>/` — keep the OS temp root
  (regenerable, OS-reaped, off the home dir), but add a **per-session subdir**
  (scopes each pane's server; deterministic cleanup) and **0700 perms** (shared
  remote servers).
- **`render/` package:** split `dump.py` → `app/render/` as a behavior-preserving
  move **once the new render code (cards, asset modes, export) exists** — not
  speculatively, not fused into a feature diff.
- **Remote:** bind `127.0.0.1` only; serve **bundled** assets (never a CDN);
  **degrade gracefully** to TUI-only when port-forwarding is unavailable; serve
  exports as a **download over the tunnel** (artifact lives on the server).

## 3. Non-Goals

- Browser-primary mode / a second interactive chat surface.
- Multi-tenant / auth / hosted share service (this is a single-user localhost
  tool, Jupyter-class — not a web app).
- Edit-and-rerun of previous turns (no notebook cell model).
- Option 3 (single shared runtime) unless concurrently-visible heavy charts
  force it.

## 4. Target File Structure

All in the `app/` layer (consumes `ChatResult`/`ChatEvent` from `chat`; no new
cross-layer edges).

```
tabulaflow/app/
├── render/                # dump.py split (Phase 3) — RENDER, used by pane + export
│   ├── __init__.py        #   re-export public API (stable imports)
│   ├── media.py           #   sniff/serialize/write_cell_dump/blob
│   ├── tables.py          #   render_table_html + table JS
│   ├── charts.py          #   render_chart_html + Vega
│   ├── cards.py           #   record-card composer (Chart|Data|Query tabs)
│   └── export.py          #   self-contained / inline-mode bundler
├── pane/                  # SERVE — decoupled from the Textual TUI
│   ├── __init__.py        #   start_pane(session) -> PaneHandle{push(), url, stop()}
│   ├── server.py          #   ASGI: static (dumps+assets), /pane, /index, /download
│   ├── channel.py         #   push notifications (poll index → SSE later)
│   └── lifecycle.py       #   free port, bind 127.0.0.1, env-aware open
├── assets/pane/           # pane.js (stack, virtualization, curation), pane.css
├── page.py                # (stays) page shell
├── display.py             # (reuse) build_result_views — shared by TUI + pane
├── screens.py             # open_*_in_browser → repoint to pane.push (Phase 2)
├── widgets.py             # AgentResultWidget → push cited results (Phase 1/2)
├── session.py             # SessionState owns the PaneHandle
└── runtime_paths.py       # dumps_dir → $TMPDIR/tabulaflow/<session_id>/ + 0700
```

**Dependency rule (internal):** `pane/` depends on `render/` (and a push API),
**never** on the Textual TUI. The TUI wires *into* the pane. This keeps a future
browser-primary mode reusable without a rewrite.

---

## 5. Phased Plan

Each phase is independently inspectable. Phases 1–2 are the usable MVP; 3+ are
enhancements layered on top with no rework of earlier phases.

### Phase 1 — MVP: auto-updating output pane

**Goal:** a cited result appears automatically in one persistent browser pane,
local and remote. Kills the per-turn "open in browser" friction.

**Scope (the 4 minimal things):**
1. Embedded HTTP server in the TUI process: bind `127.0.0.1`, auto-pick a free
   port, serve the session dumps dir + bundled assets.
2. Auto-write each **cited** result using the **existing** `dump.py` (chart if
   present, else table) → write to the dumps dir. *No new rendering code.*
3. One pane page that **stacks** result files (iframes) and auto-updates by
   **polling** an index endpoint and appending new cards (naive append).
4. Lazy-open on the first result: `webbrowser.open("http://localhost:PORT")`;
   always also print the URL as fallback.

**Reuse:** `dump.py` unchanged (re-inlines assets — inefficient but fine for few
results); `build_result_views`/`ChatResult` for the cited set.

**Out of scope:** tabs, virtualization, curation, sharing, asset-mode split,
`render/` refactor, SSE, perms hardening.

**Get right now (so it's a subset, not throwaway):** serve over HTTP + bind
loopback; reuse `dump.py` as-is.

**Inspect:** run the app, ask for a chart → it appears in the browser without a
manual open; ask again → second chart appended. Over SSH with a forwarded port,
the same works. Closing/not-opening the tab never blocks the TUI.

### Phase 2 — Trigger & interaction polish

**Goal:** the pane feels right — present but not intrusive.

**Scope:**
- **Content trigger:** confirm `cited ⟺ pane` (auto); **repoint** the explorer's
  `open_*_in_browser` actions to `pane.push` (manual view → pane).
- **Focus asymmetry:** auto-pushed results update the pane **silently** (no focus
  steal); manual "view this" **opens/focuses** the pane.
- **Window trigger:** re-open/focus keybinding; persistent TUI status
  (`results pane → localhost:PORT`); subtle per-push indicator (`→ pane`);
  a toggle to disable auto-push/auto-open.
- **Graceful degrade:** on bare SSH / auto-open failure, surface the URL + the
  re-open keybinding; never error.

**Inspect:** no focus ping-pong while iterating; manual view from the data
explorer opens the pane; status line shows the URL; toggle works; opening the
pane *late* shows the full backlog (durable).

### Phase 3 — Record cards + `render/` refactor

**Goal:** each cited result shows as a proper card with Chart | Data | Query
tabs, matching the TUI's view model; serve assets once.

**Scope:**
- **`render/` split** (behavior-preserving pure move): `dump.py` → `render/`
  (`media`, `tables`, `charts`), `__init__` re-exports. Separate commit, verified
  by existing render tests + `scripts/gen_debug_html.py`.
- **`render/cards.py`:** compose a `RecordGroup` (from `build_result_views`) into
  a self-contained card with a **Chart | Data | Query tab strip**, default to the
  most visual view. *Stack records, tab views.*
- **Asset-mode split:** `assets="linked"` for the pane (served `/assets`, cached
  once) vs `inline` (offline/share). Parameterize the asset base so `render/`
  stays transport-agnostic.

**Inspect:** a result shows the tab strip; switching tabs works; network shows
the library fetched once; `render/` tests green; debug HTML unchanged.

### Phase 4 — Scalability: virtualization + truncation

**Goal:** a 50+ turn session stays smooth and bounded (append-only growth).

**Scope:**
- **Viewport virtualization** (IntersectionObserver): only cards in/near the
  viewport hold live iframes; off-screen → placeholders. Bounds live runtimes to
  visible (memory constant in turn count).
- **Output truncation/caps** for large tables/charts (also a bandwidth control
  remotely).
- *(Optional)* swap polling → **SSE** with Last-Event-ID reconnect + keepalive.

**Inspect:** a long session (force 50+ cited results) stays responsive; browser
memory flat; scrolling doesn't degrade.

### Phase 5 — Curation (workspace model)

**Goal:** prune the superseded refinement intermediates our append-only model
uniquely accumulates.

**Scope:**
- **Pane = curated workspace; TUI = immutable log.** Delete/collapse/pin in the
  pane prunes the card + its dump file; the TUI history is untouched.
- Default to **collapse** (recoverable); **delete** is the firm action;
  **pin** keeps the desired result.

**Inspect:** delete/collapse a turn's card in the pane; the card + file go; the
TUI conversation still shows that turn; pinned results survive a "clear others".

### Phase 6 — Sharing / export

**Goal:** make an artifact easy to share with others.

**Scope:**
- **Self-contained export** (`render/export.py`, inline asset mode): one portable
  HTML — interactive-but-frozen — per artifact / per turn / whole-session report.
- **Picture-only vs with-data** choice (PNG/SVG/spec vs HTML/CSV) so sensitive
  rows don't leak.
- **Download over the tunnel:** `/download/<id>` serves the export so it reaches
  the laptop (the file lives on the server). Hosted-link (user's own bucket →
  signed URL) stays opt-in; **no hosted share service**.

**Inspect:** export a chart → open the file offline (no server); on remote, the
export downloads to the laptop; chart-only export carries no rows.

### Phase 7 — Remote hardening

**Goal:** safe and robust on shared/remote servers (some folded earlier).

**Scope:**
- **Dump dir:** `$TMPDIR/tabulaflow/<session_id>/` + **0700 dir / 0600 files**
  (data exposure on shared `/tmp`). `$XDG_RUNTIME_DIR` noted as the per-user
  alternative (tmpfs — only for modest dumps).
- **gzip** responses; **SSE keepalive**; **persist the session port** for
  predictable re-forwarding after a tunnel drop.
- Re-confirm: loopback bind, sandboxed iframes, bundled assets, full
  degradation to TUI-only when forwarding is unavailable.

**Inspect:** on a multi-user box, dump files aren't world-readable; a dropped
tunnel + reconnect restores the pane from server-side files.

---

## 6. Deferred Decisions / Open Questions

- **Option 3 escalation:** adopt the single-shared-runtime model only if
  concurrently-visible heavy Vega charts strain the browser even with
  virtualization. Keep `render/` (export) regardless.
- **Polling → SSE timing:** start with polling (Phase 1); upgrade in Phase 4 if
  latency/efficiency warrants.
- **Agent-signaled supersession:** later, let the agent mark "this revises the
  prior chart" → auto-collapse — the automatic analog of Jupyter's edit-and-rerun
  (curation in Phase 5 is the manual version).
- **`render/` split timing:** Phase 3 (when cards/export land). Only the
  media/serialization peel-off is safe to do earlier if desired.
