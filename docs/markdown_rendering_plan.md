# Markdown Rendering (Output Pane + TUI) — Design & Implementation Plan

Render the assistant's answer (`ChatResult.text`) as **markdown** on both
frontends — the browser output pane and the terminal TUI — with **per-surface
feature sets** (the TUI disables table rendering). Each surface renders with
its native renderer; they share the markdown *source* and its upstream
semantics, **not rendering code**. The pane change is JS-only; the TUI change
swaps the answer block's plain-text render for a markdown widget.

> **Status:** pane side implemented (`f6759805`); TUI side proposed.

---

## 1. Goal

The chat agent's answer is markdown, but neither surface renders it today:

- **Pane:** `buildTranscript` in `assets/ui/pane.js` sets
  `body.textContent = turn.assistant` on a `white-space: pre-wrap` block —
  literal `**bold**`, `## headings`, pipe-tables.
- **TUI:** `AgentTextBlock` renders the streamed answer as plain Rich `Text`
  (`app/widgets.py`) — deliberately, per its docstring: Textual only extracts
  text *selection* from `Text`/`Content` renders. (The `markdown.*` Rich theme
  styles in `app/display.py` are not used by this path.)

Render both as formatted markdown, in each surface's design language, without
changing what is stored or streamed. Feature sets intentionally differ: the
pane renders GFM tables; the TUI does not (prose tables read poorly at
terminal widths, and tabular data belongs in cited result cards).

## 2. Current state (key facts)

- **The raw markdown already flows end-to-end, semantically normalized once.**
  The chat layer strips the artifact-refs block from the answer
  (`chat/agent.py`, answer parsing around `_parse_refs`) *before* either
  surface sees the text. The TUI receives it streamed (`AnswerDelta` deltas,
  reconciled by the terminal `Finished.result.text`); `tui.py` pushes the same
  final text to the pane via `turn_payload(..., assistant=result.text)`.
  Nothing new needs to be transported.
- **The pane's architecture is "server ships data, browser renders".** Tables
  (Tabulator), charts (Vega), maps (MapLibre), graphs (Cytoscape) all render
  client-side from data payloads; vendored libs live under `assets/vendor/`
  as classic `<script src>` globals (see `docs/pane_frontend_modules_plan.md`).
  One exception: the query view ships pygments-highlighted HTML
  (`build_query_data` in `pane/cards.py`), because no JS highlighter is
  vendored.
- **The TUI answer path streams.** `AgentProgressWidget._on_answer_delta`
  accumulates deltas and re-sets the full text on the sibling
  `AgentTextBlock`; `_on_finished` reconciles with the authoritative text.
- **Both candidate renderers are the same parser lineage.** Rich/Textual parse
  with `markdown-it-py`; the browser lib is `markdown-it` (same spec, same
  named rules: `table`, `strikethrough`, linkify). Dialect alignment across
  surfaces is free — feature toggles have identical names and semantics.

## 3. Architecture — what is shared, what is not

**Shared:**

- **The source string.** `ChatResult.text` is the single markdown artifact.
- **Semantic normalization, upstream in Python.** Any transformation of
  *meaning* (today: artifact-ref stripping) happens once in the chat layer,
  before the text fans out. New transformations of that kind go there too.
- **The dialect spec** (§4) — which features the agent may emit and which
  subset each surface renders. A specification, not code; enforcement is one
  line of parser config per surface.

**Not shared:** rendering code, feature configuration, streaming machinery.

- The render targets are terminal cells and DOM — the only shareable stage is
  parsing, and shipping parsed token streams to the browser would be a worse
  wire format than markdown itself (markdown *is* the compact serialization).
- The feature sets intentionally diverge; a shared "dialect config" object
  would need per-surface overrides on day one — a pass-through abstraction.
- The TUI renders a *stream*, the pane renders a *complete turn*. Coupling a
  streaming renderer to a static one is a forced abstraction.
- This matches the codebase-wide pattern: one data payload, N surface-native
  renderers (a DataFrame renders via Tabulator in the pane and differently in
  the TUI; markdown joins that pattern — text is data, rendering is
  surface-owned).

**Rejected: server-side HTML rendering for the pane** ("Python parses markdown
for the TUI anyway — one Python stack"). markdown→terminal-cells and
markdown→HTML share nothing except the parse call. Client-side pane rendering
keeps the manifest pure data, applies renderer/CSS fixes retroactively to
persisted sessions, and needs zero contract change. The query view's
pre-rendered `html` is the lone precedent, motivated by the lack of a JS
highlighter — markdown has a first-class JS renderer. If highlighted fenced
code ever matters in the pane, `markdown-it` has a `highlight` hook.

## 4. Dialect matrix

The agent emits the superset; each surface renders its subset. Degradation is
always *visible text*, never silently dropped content.

| Feature | Pane (browser) | TUI (terminal) |
|---|---|---|
| Headings, emphasis, lists, blockquote, inline code | rendered | rendered |
| Fenced code blocks | rendered, unhighlighted (hook later) | rendered, syntax-highlighted (Textual fence uses `Syntax` — free) |
| GFM tables | rendered (thin-ruled prose table, not Tabulator) | **disabled** — pipe source shows as literal text |
| Strikethrough | rendered | rendered |
| Raw HTML | escaped → visible as text (`html: false`) | visible as text (`html=False`) |
| Images | **disabled** (`.disable('image')`) — no remote fetches from the token-scoped page | not applicable (terminal) |
| Linkify bare URLs | on | off |
| Typographer | off | off |

Parser configs (the entire per-surface enforcement):

- **Pane:** `markdownit({ html: false, linkify: true })` — JS default preset;
  tables/strikethrough already on.
- **TUI:** `MarkdownIt("commonmark", {"html": False}).enable("strikethrough")`
  — no `table` rule.

Because the TUI shows pipe tables literally, answer-style guidance in the chat
system prompt should keep discouraging inline prose tables — tabular data
belongs in cited records (Data cards). Small prompt nudge if not already
covered.

## 5. Pane implementation

1. **Vendor the library.** `assets/vendor/markdown-it/markdown-it.min.js`
   (current 14.x dist) plus its MIT `LICENSE`, following the maplibre
   provenance pattern. Load in `index.html` as a classic script before the
   module entry; render code reads `window.markdownit`. Vendor assets are
   already served immutable-cached by `_serve_asset` — no server change.
   `markdown-it` over `marked`: `html: false` escapes raw HTML **by
   construction** (no DOMPurify needed), and GFM tables/strikethrough are in
   the default preset; `marked` passes raw HTML through and would need a
   second sanitizer lib.
2. **`assets/ui/render/markdown.js`** — export `renderMarkdown(node, text)`:
   one module-scope `markdownit({ html: false, linkify: true }).disable('image')`,
   set `node.innerHTML = md.render(text)`, then rewrite `a[href]` with
   `target="_blank" rel="noopener noreferrer"` (the pane is a token-scoped
   local page — never leak it as a referrer; images are disabled so the page
   makes no remote fetches). Falls back to `textContent` if the vendor lib
   didn't load. No `ViewHandle` — the transcript is outside the card view
   lifecycle (`renderKind`/`viewCache`).
3. **`pane.js`** — in `buildMessage`, assistant role only: add class `md` and
   call `renderMarkdown(body, text)`. User messages stay `textContent` (user
   input is not markdown; asymmetry matches chat-app convention). Turn titles
   and the sidebar stay plain text.
4. **`pane.css`** — a `.message-body.md` typography block in the design
   language: mint (`#3eb489`) headings and links; `pre`/`code` on the panel
   surface (`#1a212c`, thin `#21262d` border); minimal thin-ruled tables;
   blockquote with a mint left border; tight margins so rendered text keeps
   the current plain-text rhythm. Drop `white-space: pre-wrap` for `.md`.
   Wide content (`pre`, tables) scrolls inside its own box; the message column
   never overflows.
5. **Cache-busting.** Add `render/markdown.js` to the module-hash list in
   `_load_pane_html` (`pane/server.py`).
6. **`contract.d.ts`** — declare `markdownit?: any` on `Window`. No payload
   types change.

## 6. TUI implementation

1. **Replace the answer block's render with Textual's `Markdown` widget**
   (textual 8.2.2), constructed with
   `parser_factory=lambda: MarkdownIt("commonmark", {"html": False}).enable("strikethrough")`
   — `parser_factory` is a first-class knob and *is* the "disable tables"
   implementation. Keep the mount-as-sibling structure
   (`AgentProgressWidget._set_text` mounts the block after itself); the block
   becomes (or wraps) the `Markdown` widget instead of a `Static(Text)`.
2. **Streaming.** Use the widget's streaming API (`Markdown.get_stream()` /
   `MarkdownStream`): feed each `AnswerDelta` via `stream.write(delta)` — it
   re-renders only the tail block, purpose-built for LLM streaming. On
   `Finished`, stop the stream and reconcile with the authoritative
   `result.text` via a full `update()` when it differs from the streamed
   accumulation (mirrors today's `_on_finished` reconcile).
3. **Theming.** Style the widget's component classes (headings, fences, links,
   blockquote) to the TUI design language in `tui.tcss` / `app/theme.py`
   (mint accent, dark code surface). Retire the unused `markdown.*` styles in
   `display.py` or repoint them if the Rich theme participates.
4. **Selection gate (verify before committing to this route).** Plain `Text`
   was chosen deliberately so the answer is select-to-copyable. Verify
   selection over the `Markdown` widget subtree on textual 8.2.2. If selection
   is unacceptable, stop and surface the markdown-vs-selection tradeoff —
   don't trade it away silently.

*Rejected alternative:* Rich's `Markdown` renderable inside the existing
`Static`. Its parser is hardcoded in `__init__` (`.enable("table")` — disabling
tables requires a subclass that re-parses), it has no streaming API (full
re-parse and re-render per delta), and it definitely breaks selection.

## 7. Test fallout / verification

- **Pane:** no payload change → `test_pane_contract.py` untouched. Check
  `test_output_pane.py` for assertions pinned to `index.html` script tags or
  the module-hash list; extend rather than re-pin JS source strings.
  `node --check` on `render/markdown.js` and `pane.js`. Preview smoke
  (`uv run scripts/preview_output_pane.py --port 61211`) with a fixture answer
  exercising headings, bold, GFM table, fenced code, links, and a raw
  `<script>alert(1)</script>` line — the latter must render as escaped text
  (the `html: false` guarantee).
- **TUI:** no existing tests pin `AgentTextBlock`'s render. Manual pass: run
  the app, stream an answer with headings/lists/fence/table — the table must
  appear as literal pipe text, the fence highlighted; verify select-to-copy
  (§6.4) and streaming smoothness on partially-arrived constructs.
- `make test` green.

## 8. Future extension (out of scope here)

If markdown ever becomes a citable **artifact** (agent-written reports), the
pane side slots straight in: add `"markdown"` as a `ViewKind`, carry raw
markdown in the card's `.data.json`, dispatch to the same renderer from
`renderKind`. Nothing about the transcript-first version changes.

## 9. Non-goals

- No shared markdown code path or config object between surfaces — alignment
  is spec-level (§4) only.
- No server-side markdown rendering; no new fields in `PaneTurn` or card
  payloads.
- No syntax highlighting in pane fenced code (hook exists if needed later).
- No TUI table rendering (by design), and no degraded table substitute
  (e.g. "see output pane" placeholders).
- No markdown rendering of user messages, turn titles, or card labels, on
  either surface.
- No streaming in the pane — turns arrive complete.
