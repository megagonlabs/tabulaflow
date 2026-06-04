# Migration Plan: `mintq` → `tabulaflow` + modular restructure

Status: proposed. Owner: Yanlin. Branch: `restructure` (single long-lived branch; each
phase is its own commit with `make test` green before the next).

---

## 1. Goals

1. **Rename** the package `mintq` → `tabulaflow` (clean break — no back-compat aliases).
2. **Restructure** the flat package into four intuitive, dependency-layered modules so the
   library is easy to navigate and easy to *import from* for three distinct audiences:
   end users (the TUI app), researchers (NL2SQL benchmarking), and the interactive agent lib.
3. **Enforce** the layering with `import-linter` so the boundaries can't silently rot.

## 2. Principles (the rules we keep referring back to)

- **Layout ≠ import surface.** What a library user types is set by each layer's `__init__.py`
  facade, *not* by how many files sit behind it. Optimize the facade; let file count be an
  internal concern.
- **No new abstraction to dodge a dependency.** Prefer moving code to its true layer over
  introducing generics/protocols/indirection. (We are explicitly *not* doing DI, nested
  settings, or per-layer config fragmentation.)
- **Split files only where there's a real seam** (different dependency layer, audience, or
  lifecycle — or a big self-contained infra blob). Cohesive related models stay together.
- **Two big operations never interleave.** Rename is one mechanical pass; restructure is a
  separate sequence. Each lands green and bisectable.
- **Fail fast; fix root causes.** Several moves surface latent layering bugs — fix them, don't
  paper over them.

---

## 3. Target architecture

### 3.1 Layers

```
tabulaflow/
├── core/        Foundation. Depends on nothing else in tabulaflow.
│                  config, registry, utils, db_connector/, formatters/,
│                  types.py (data structures), dataframe.py (Arrow/df infra),
│                  the BaseTool protocol, the atomic RunQueryTool primitive,
│                  connector/schema-level preprocessing.
├── toolhub/     All agent tools. Depends on core only.
│                  registry_* (which wrap the plain tools), message_store,
│                  web_browser, render_chart, add_canonical_name, extract_rows,
│                  entity_extractor, run_subagent, query_history, pdf_extract,
│                  aria_to_markdown.
├── chat/        The interactive tabulaflow agent lib. Depends on toolhub, core.
│                  agent.py (ChatAgent, ProgressSink, ChatResult) + tool wiring.
├── research/    For NL2SQL researchers. Depends on toolhub, core. NEVER chat.
│                  agenthub/, datahub/, metrics/, pipelines/,
│                  types.py (NL2QTask hierarchy, NL2QDataset, NL2QRunResult),
│                  tools/ (research-only: ask_user, run_dbt, execute_bash,
│                  file_editor, search_keywords, finish, get_schema, ...),
│                  dataset-level preprocessing (question_embedder).
└── app/         End-user TUI application. Depends on chat, core. NEVER research.
                   tui, dump (HTML export), widgets, display, theme, commands,
                   runtime_paths, main, assets/.
```

### 3.2 Dependency contract

```
core  <  toolhub  <  { chat | research }  <  app
```

`chat` and `research` are **siblings** — same level, must not import each other (already true
today: the CLI imports zero from `agenthub`/`datahub`). `import-linter` config:

```ini
# .importlinter
[importlinter]
root_package = tabulaflow

[importlinter:contract:layers]
name = Layered architecture
type = layers
layers =
    tabulaflow.app
    tabulaflow.chat | tabulaflow.research
    tabulaflow.toolhub
    tabulaflow.core
```

### 3.3 Why this shape (recorded so we don't relitigate)

- App ↔ research are already decoupled (0 import edges) — the wall exists; we're making it explicit.
- The `registry_*` tools **wrap** the plain tools (`registry_run_query` → `RunQueryTool`, etc.),
  so tools must stay unified in one `toolhub` layer; splitting them across `chat`/`research`
  would create a forbidden `chat → research` edge.
- `toolhub` is its own layer (not folded into `core`) so `core` stays honest foundation —
  `core` shouldn't know about browser automation, dbt, or vega-lite charts.

### 3.4 Naming decisions

| Old | New | Reason |
|-----|-----|--------|
| `cli/agent.py` | `chat/agent.py` | avoid collision with research `agenthub` and its `MintqAgent` |
| (the agent layer) | `chat/` | conversational layer; matches `ChatAgent`/`ChatResult`; sibling-style to `toolhub` |
| `cli/` (app part) | `app/` | it's more than a TUI (HTML `dump.py`, entrypoint); honest superset |
| `cli/app.py` | `app/main.py` | entrypoint `tabulaflow.app.main:main` (avoid `app.app` stutter) |
| `schema.py` | `core/types.py` | file holds schemas **+** queries/results/usage/trajectory; `schema` was a misnomer. **Not** `models.py` — collides with LLM "models". |
| (df helpers) | `core/dataframe.py` | ~285 lines of Arrow/df serialization infra; extracted because big + unrelated to domain |
| research task types | `research/types.py` | `NL2QTask*`, `NL2QDataset`, `NL2QRunResult`, serializers |

---

## 4. Phases

Each phase: branch is already cut; do the work; `make test` green; `make lint`/`mypy` clean;
commit with the message shown. `import-linter` is installed in Phase 0 but only **enforced**
from the phase noted (run report-only before that).

### Phase 0 — Baseline & safety net
- Cut branch `restructure`. Record baseline: `make test` green, capture the aggregated metrics
  of one smoke run so behavior can be compared post-migration.
- Add `import-linter` to the `dev` dependency group; add `make lint-arch` (`uv run lint-imports`).
- Write `.importlinter` with the §3.2 contract (it will fail now — that's expected; keep it
  report-only / non-blocking until Phase 6).
- Snapshot the import inventory (`grep -rhoE "from mintq\.[a-z_]+"`), to diff against later.
- **Commit:** `chore: baseline + import-linter scaffolding`

### Phase 1 — Rename `mintq` → `tabulaflow` (clean break)
Pure identity change on the *current* (flat) structure — easiest to verify because behavior is
unchanged.
- Mechanical: `git mv mintq tabulaflow`; substitute the `mintq` token across `*.py`, `*.toml`,
  `*.md`, `Makefile` (distinctive token, few false positives — still review the diff).
- Deliberate, **non-mechanical** spots (clean break, no aliases):
  - env prefix `MINTQ_` → `TABULAFLOW_` (`config.py` `env_prefix`).
  - cache dir `~/.mintq` → `~/.tabulaflow`; session dir likewise (invalidates existing cache —
    accepted).
  - CLI command + entrypoint: `[project.scripts] tabulaflow = "tabulaflow.cli.app:main"`
    (path fixed in Phase 7).
  - dist name `mintq` → `tabulaflow` in `pyproject.toml`.
  - agent self-identity: `chat`/`cli` system prompt string "You are the mintq agent…".
  - branding: `dump.py` banner/logo, README, AGENTS.md, CLAUDE.md, Makefile targets, tmux
    session name `mintq`. Note: "tabulaflow" drops the *mint* pun, so the mint accent
    `#3eb489` is now just a color — keep or revisit deliberately.
  - `_MintqSettings` → `Settings`.
- Verify: `uv sync`; `make test` green; `tabulaflow --help` launches; one debug agent run.
- **Commit:** `Rename mintq → tabulaflow (clean break)`

### Phase 2 — Config decoupling
Small, isolated, still in the flat structure.
- Remove `dataset` and `split` from `Settings` — they are experiment parameters, not config,
  and they're the only fields that would make `core`'s config know about research.
- Move their defaults into the research CLI (`run_agent.py` argparse: `--dataset` default
  `"bird-sql"`, `--split` default `"dev"`), and drop the `mintq_config.dataset/split` fallbacks.
- Leave everything else flat & global (no nesting, no DI — deliberate).
- (Optional, low priority) fold `PHOENIX_*`/`LANGFUSE_*`/`LOGFIRE_TOKEN` reads into `Settings`
  so all config flows through one place.
- Verify: `make test`; run `run_agent.py --dataset bird-sql --debug`.
- **Commit:** `config: drop dataset/split (experiment params, not config)`

### Phase 3 — Establish `core/` + split the type modules
- Create `tabulaflow/core/`. `git mv` foundation in: `config.py`, `registry.py`, `utils.py`,
  `db_connector/`, `formatters/`.
- Split `schema.py`:
  - `core/types.py` — all core data structures (SQL + graph schema, `GoldQuery`/`PredQuery`,
    `ExecResult`/`ErrorInfo`, `Usage` + cost, messages + `Trajectory`).
  - `core/dataframe.py` — the Arrow/df (de)serialization helpers.
  - `research/types.py` (create `research/` here as destination) — `NL2QTask` hierarchy + all
    `*Output` + ambiguity points + `ARCSAmbiguityType` + dbt task types + `NL2QDataset`/
    `NL2QRunResult`/`CSVSummaryRow` + the `_task_to_*` serializers.
- Move the `BaseTool` protocol (`toolhub/base.py`) **down** into `core` (preprocessors/core need
  it; otherwise it's an upward edge).
- **Type-leak fixes** (latent layering bugs this split surfaces):
  - `utils.py`: move `sort_gold_queries` / `sort_ambiguity_points` (take `AmbigNL2QTask`) out of
    core → `research`.
  - the `User*Question/Answer` + `BaseUserSimulator` types → fold into `agenthub/user_simulator.py`
    (research).
- **Facades:** curated `core/__init__.py` re-exports the public types so users write
  `from tabulaflow.core import SQLSchema, ExecResult, Usage`. Same pattern for `research/__init__.py`.
- Rewrite imports tree-wide to the new `core.*` / `research.types` paths.
- Verify: `make test`; `lint-imports` shows `core` with no upward edges.
- **Commit:** `restructure: establish core/ layer; split schema.py → core/types + dataframe`

### Phase 4 — Untangle the schema-tooling cycle
The one genuine knot. Today:
`preprocessors.{db_summarizer,er_diagram,components.fk_predictor}` → `toolhub.run_query.RunQueryTool`,
while `toolhub.{get_table_schema,registry_get_schema,registry_get_db_document}` →
`preprocessors.{components.schema_compressor,db_summarizer}`; plus `formatters.er_diagram` →
`preprocessors.er_diagram`.

Resolution (move code to its true layer; no new abstraction):
1. **`RunQueryTool` is the atomic query-execution primitive** (query → `ExecResult`; depends only
   on a connector + `core` utils). Move it (and its minimal deps) **down into `core`**. Now
   preprocessors can use it without reaching up.
2. **`ERDiagram` is a data type; its *synthesizer* is logic.** Put the `ERDiagram` type in
   `core` (alongside `types.py` or a small `core/er_diagram.py`); keep the synthesizer (which
   runs queries) wherever it's used. Then `formatters.er_diagram` and `preprocessors.er_diagram`
   both depend *down* on the core type instead of on each other.
3. With (1)+(2), **connector/schema-level preprocessing** (`schema_compressor`, `db_summarizer`,
   `fk_predictor`, `column_profiler`, `text_summarizer`, schema-`er_diagram` synthesis) depends
   only on `core` → it lives in `core` (or the bottom of `toolhub`; pick per `import-linter`).
4. Re-validate: the `db_connector.loaders.huggingface → TextSummarizer` and
   `formatters.er_diagram → ERDiagram` edges must now be downward or same-layer. The huggingface
   import is already function-local; keep it lazy if a stubborn cycle remains.
- Verify: `make test`; no cycles reported by `lint-imports`.
- **Commit:** `restructure: break preprocessors↔toolhub cycle (RunQueryTool→core, ERDiagram type→core)`

### Phase 5 — `toolhub/` layer + tool re-homing + preprocessor split
- Create `tabulaflow/toolhub/`. Move the shared + chat tools there: `run_query` wrappers,
  `get_table_schema`, `get_column_json_schema`, all `registry_*`, `message_store`, `web_browser`,
  `render_chart`, `add_canonical_name`, `extract_rows_from_documents`, `entity_extractor`,
  `run_subagent_for_each_row`, `query_history`, `pdf_extract`, `aria_to_markdown`.
- Move **research-only** tools → `research/tools/`: `ask_user` (uses `BaseUserSimulator`),
  `run_dbt`, `execute_bash`, `file_editor`, `search_keywords`, `finish`, `get_schema`,
  `get_column_description`. (These aren't wrapped by `registry_*`, so they don't belong in the
  shared layer.)
- **Preprocessor split by level:** dataset-level (`question_embedder` + `BaseDatasetPreprocessor`)
  → `research`; connector/schema-level stays in `core`/`toolhub` (per Phase 4). Decouple the
  caching base from `NL2QDataset`: remove the `isinstance(input_data, NL2QDataset)` branch in
  `_get_cache_id`; have each subclass supply its cache id (connectors → `connector.global_id`;
  the dataset preprocessor brings its `name_split` id to research). This *removes* a type
  dependency — no generic/TypeVar added.
- Verify: `make test`; `lint-imports` shows `core < toolhub`.
- **Commit:** `restructure: toolhub/ layer; research-only tools + dataset preprocessing → research`

### Phase 6 — `research/` layer
- `git mv` `agenthub/`, `datahub/`, `metrics/`, `pipelines/` into `tabulaflow/research/`.
- Fix the `agenthub → pipelines` back-edge while here (both land in research, so the contract
  passes regardless, but invert the dependency for cleanliness).
- Curate `research/__init__.py` facade (`from tabulaflow.research import SQLAgent, NL2QTask, …`).
- Update the top-level `tabulaflow/__init__.py` facade: the lazy registry getters now resolve to
  `tabulaflow.research.*`; keep `tabulaflow.configure()`.
- Verify: `make test`; `lint-imports` shows `research` never imports `chat`.
- **Commit:** `restructure: research/ layer (agenthub, datahub, metrics, pipelines)`

### Phase 7 — `chat/` + `app/` split, entrypoint, branding paths
- Create `tabulaflow/chat/`: move `cli/agent.py` → `chat/agent.py`; co-locate its tool-wiring.
  Its `ProgressSink`/`ChatResult` are the seam the app depends on.
- Create `tabulaflow/app/`: move the rest of `cli/` (`tui`, `commands`, `display`, `widgets`,
  `dump`, `theme`, `runtime_paths`, `assets/`); `app.py` → `app/main.py`.
- Update entrypoint: `[project.scripts] tabulaflow = "tabulaflow.app.main:main"`; update
  `[tool.setuptools.package-data]` asset globs to `app/assets/*`.
- Remove the now-empty `cli/`.
- Verify: `make test`; `tabulaflow` launches the TUI; an HTML dump renders.
- **Commit:** `restructure: split cli/ into chat/ (agent lib) + app/ (TUI)`

### Phase 8 — Enforce, document, clean up
- Flip `import-linter` to **blocking** in CI / `make lint`; the §3.2 contract must pass.
- `mcp/`: it imports `mintq.metadata_synthesizer`, which doesn't exist — decide **delete** the
  dead example or fix it. Update remaining `mintq.*` references in `mcp/`.
- Update AGENTS.md / CLAUDE.md / README to the new layout, commands, and `tabulaflow` name.
- Update `Makefile` paths (`tabulaflow/research/pipelines/run_agent.py`, etc.).
- Verify: full `make test`, `make mypy`, `make lint`, `make lint-arch` all green; behavior
  metrics match the Phase 0 baseline.
- **Commit:** `restructure: enforce layer contract; docs + mcp cleanup`

---

## 5. Verification checklist (run at every phase)

- `make test` green (caching disabled, as the target already does).
- `make mypy` and `make lint` clean.
- `lint-imports` — report-only through Phase 5, blocking from Phase 6.
- Smoke: `uv run tabulaflow/research/pipelines/run_agent.py --agent sql_agent --dataset bird-sql --debug`
  produces the same aggregated metrics as the Phase 0 baseline.
- From Phase 7: `tabulaflow` CLI launches; an HTML table dump renders in the browser.

## 6. Deferred (explicitly out of scope)

- **Experiment-config files** replacing the ~50 flag-string Makefile targets (e.g.
  `experiments/arcs_qwen_thinking.toml` loaded by the pipeline). This is the natural endpoint of
  the "config vs. run-params" split (Phase 2) and would make runs reproducible/diffable — but
  it's a *feature*, not part of the rename/restructure. Do it after this lands.
- Any change to the global-singleton config mechanism beyond removing `dataset`/`split`
  (no nesting, no DI — decided against as over-abstraction for this project's scale).

## 7. Risks & rollback

- **Risk: a phase wedges on a stubborn cycle (Phase 4/5).** Mitigation: phases are independent
  commits; `lint-imports` localizes the offending edge; function-local (lazy) imports are an
  accepted last resort for a genuine two-way data dependency.
- **Risk: clean break breaks someone's `.envrc` / cached schemas.** Accepted by decision
  (clean break). Cache regenerates on next run; `.envrc` must switch `MINTQ_*` → `TABULAFLOW_*`.
- **Rollback:** each phase is one revertable commit; the branch is not merged until Phase 8 is
  green end-to-end.
