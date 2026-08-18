# Agent-Driven Data Sources — Design & Implementation Plan

## Goal

Today, in the TUI app a user can only connect to a data source **manually** via the
`/connect` slash command (typing a URL or file path). We want the **chat agent** to
connect to and build data sources **on the user's behalf**, without the user supplying
paths/URLs. Two motivating flows:

1. **Connect a prebuilt source** — the agent runs the equivalent of `/connect` for a
   HuggingFace dataset, an existing CSV/JSON file, or a database URL.
2. **Build a dataset from scattered data** — e.g. experiment results scattered across
   `output/`. The agent gathers them (running code via a shell tool), produces a
   consolidated artifact, and connects it as a queryable source — which the user can
   then **keep adding to**.

In all cases the user must still **see the auto-connected sources in the data explorer**.

---

## Key architectural facts (current state)

- **One shared object is the source of truth: `session.registry` (`DBRegistry`).**
  The chat agent (`ChatAgent.registry`) and the data explorer
  (`SchemaBrowserScreen`) both hold a reference to the *same* instance. Anything
  registered there is queryable by the agent and visible in the explorer.
- **The explorer is pull-based** — it reads `registry.list_aliases()` each time it is
  opened (`Ctrl+O`). No subscription/refresh machinery exists. So a new source shows up
  on the next open with no extra plumbing.
- **`/connect` flow** (`tabulaflow/app/commands.py`): resolve source → build connector
  (`load_files` / `SQLConnector.from_url_async`) → `registry.register(alias, connector)`
  → `_register_user_db` (dedup bookkeeping via `session._sources`, remove the bundled
  `sample_data`, `chat_agent.note_event(...)`).
- **The workspace** is a per-session **writable DuckDB** connector
  (`create_workspace_connector`, `read_only=False`) registered under alias `workspace`.
  It is the agent's *internal scratch* (result spill, message offload, canonical names) —
  **not** a user-facing deliverable.
- **`run_query` (`RegistryRunQueryTool`)** executes SQL against a registered connector by
  alias. The agent has no shell/code-execution tool and no way to connect/create sources.
- **Layering** (enforced by import-linter):
  `core < datasources < toolhub < modulehub < {chat | research} < app`.
  `toolhub` may import `datasources`/`core`. `toolhub` may **not** import `app`. So
  app-owned registration policy must reach agent tools via **injected callbacks**, not
  imports.
- **Session paths** (`RuntimePaths.for_session`): `~/.tabulaflow/sessions/<id>/` holds
  `data/` (materialized connector DBs), `trajectories/`, `logs/`, `workspace.duckdb`.
  The TUI process `cwd` is the **project dir** where the user launched the app (where
  `output/` lives, and what `/connect ./x.csv` resolves against).

---

## Design decisions (with rationale)

### D1. Three distinct operations — don't conflate them

- **Gather** — custom aggregation of scattered files → one artifact. A **shell/bash tool**.
- **Connect** — expose data that *already exists* as a **read-only** reference.
- **Create dataset + ingest** — build a **writable, growable** named dataset.
- **Export** — push a processed result *out* to a user-named file.

These have different inputs, mutability, and intent; each gets its own mechanism.

### D2. Shell tool: guardrail, not sandbox

The agent is **cooperative** (an LLM helping on the user's own machine, with the user's
own permissions) — not adversarial. The realistic risk is an *accidental* destructive
command, not an attacker evading us. Therefore:

- **No OS sandbox.** `sandbox-exec` (macOS Seatbelt) was considered and **rejected**: it
  is macOS-only (not cross-platform), Apple-deprecated, and needs fragile write-allowlist
  tuning. We want something simple and cross-platform.
- **Small, high-signal denylist** of catastrophic patterns (`rm -rf` on broad paths,
  `dd`/`mkfs`, fork bombs, `curl|sh`, `git reset --hard`/`checkout` across the tree,
  redirects onto system paths, …). **Refuse-on-match**, returning the reason to the
  agent. Keep it short; chasing completeness is a losing game and breeds false
  confidence. This is explicitly a guardrail against accidents, **not** a security
  boundary.
- **Network is allowed** (needed for HF downloads etc.). There is simply nothing to
  restrict.

### D3. Shell tool cwd = project dir; scratch addressed absolutely

The path trap: the agent operates in **two execution contexts with different cwds** —
bash (subprocess) and `run_query` (app process). A relative path means different things
in each. Resolution:

- **`cwd` = project dir** for the shell tool. This (a) matches the agent's strong prior
  (coding agents run in the project dir), and (b) makes relative reads of source data
  consistent across bash *and* `run_query` (both share cwd=project):
  `read_csv_auto('output/**/*.csv')` works in either.
- **No `$TABULAFLOW_PROJECT_DIR` env var** — redundant once cwd=project. If the agent ever
  needs the absolute project path, the shell already provides `$PWD`.
- **`$SCRATCH` env var (absolute)** — the *only* required var, because the scratch dir
  lives **outside** cwd (in the session dir) and can only be referenced absolutely.

### D4. No-pollution is enforced structurally, not by cwd

The user requirement: agent work must not leave side effects in the project dir. This is
honored **by construction**, not by a "safe" cwd default:

- The **connected deliverable** (a dataset) always lives in the session's `data/` — the
  agent never names its path.
- **Common paths write no project files**: Route A (direct ingest) and export
  (`run_query` + `COPY … TO`) write nothing via the shell. Only the rare custom-transform
  (Route B) writes a file,
  and it targets `$SCRATCH` (absolute).
- Residual (accepted): a *naive* relative write in a Route-B transform could land in the
  project. Mitigated by handing the agent `$SCRATCH` + instruction; the hard requirement
  (the deliverable) is structurally safe regardless. If a *guarantee* of zero incidental
  temp files were required, the only lever is cwd=scratch — rejected here for the
  read-consistency/agent-prior reasons in D3.

### D5. Scratch lives in the session dir

`~/.tabulaflow/sessions/<id>/scratch/` (sibling of `data/`).

- **Not** `.tabulaflow/` in the project dir — that pollutes the working tree and forces
  edits to the user's `.gitignore`. Rejected.
- **Not** `/tmp` — splits a session's artifacts across two roots. (The codebase sends
  *dumps* to `/tmp` because they're transient browser-viewed HTML with a different
  lifecycle; staging parquet is session-internal and benefits from co-location.)
- Referenced by **absolute path** when it crosses into `run_query`. Wiped on session end;
  per-file cleanup is unnecessary (session-scoped, bounded).

### D6. Datasets = named writable DuckDB; not the workspace; no cross-session persistence

Agent-synthesized data is **writable and growable** (synthesis is iterative — "connect,
then add more later"). A read-only `load_files` snapshot cannot grow. So:

- A dataset is a **named writable DuckDB** at `data/<alias>.duckdb` (`read_only=False`),
  registered as its own source — distinct from the internal `workspace`. Generalizes
  `create_workspace_connector`.
- **"Add more later" = append** (`INSERT`/`COPY`/`CREATE TABLE`) into the same dataset
  via `run_query` — no reconnect, no replace.
- **No cross-session persistence** (decided). Datasets live in the per-session dir and die
  with the session. This sidesteps the only real DuckDB-locking risk (two concurrent app
  instances opening the same persistent file read-write). Within a session there is a
  single writer (the app process), so no contention.

### D7. DuckDB single-writer is avoided by funneling all writes through the in-process connector

DuckDB allows one read-write holder **across processes**. The constraint is dodged by one
rule:

> **The shell subprocess never opens a `.duckdb` file.** It only reads/writes flat files
> (parquet) in scratch. **All** DB mutation goes through the in-process connector
> (`run_query` / `transfer_source_table`).

This is exactly how the existing workspace already works. Within one process, DuckDB's
MVCC handles concurrent connections fine.

### D8. `run_query` is the single ingestion verb, gated by connector mutability

- Relax `RegistryRunQueryTool` from SELECT-only to allow DML/DDL, **gated by
  `connector.read_only`**. User-connected sources are `read_only=True` (protected at the
  connector level); datasets/workspace are writable. The connector's own flag is the gate
  — no string-level guard, no separate ingest tool.
- **Route A (no shell, no scratch):** DuckDB reads the source files directly —
  `CREATE TABLE t AS SELECT * FROM read_csv_auto('output/**/*.csv', union_by_name=true)`
  (relative paths, cwd=project).
- **Route B (custom transform):** shell writes a parquet to `$SCRATCH`, then
  `run_query` ingests it by **absolute path** — `read_parquet('<abs $SCRATCH path>')`.
  Clean because it's the *same* absolute path the agent used to write the file.

### D9. File formats: parquet in, user's choice out

- **Gather intermediate → Parquet.** Typed, lossless, DuckDB-native, compact, supports
  nested. CSV's type-inference round-trip is a *correctness* hazard for the connected
  source (IDs, nulls, dates mis-typed). DuckDB itself can do gather+emit in one
  `COPY (… read_csv_auto(glob) …) TO 'x.parquet' (FORMAT parquet)`.
- **Export out → the user's chosen format** (csv/tsv/parquet/json/xlsx; markdown/LaTeX are
  cheap and realistic for a research audience). Inferred by file extension. The audience
  flips from DuckDB to a human, so the default flips too.

### D10. DuckDB does not expand env vars in SQL

`read_parquet('$SCRATCH/x.parquet')` is treated **literally** and fails. `getenv()` /
`getvariable()` exist but are gated/fragile inside table-function paths. Resolution:
keep `$SCRATCH` **shell-only** (the shell expands it when *writing*); in `run_query` the
agent uses the **literal absolute path** (a per-session constant stated in the system
prompt). Optional future nicety: a one-line `$SCRATCH`-token expansion inside our own
`run_query` tool — defaulted off (avoid magic; "don't over-abstract").

### D11. `create_dataset` vs `connect` — one decision axis

Disambiguating question for the agent: **"Will this source be written to after I create
it?"** (maps onto `read_only`):

- **No — static reference to existing data** → `connect` (HF/CSV/JSON/DB-URL, read-only,
  one step, mirrors the source). The **default** for anything that already exists.
- **Yes — build/grow/transform/synthesize** → `create_dataset` + `run_query`.

Encode the axis in **complementary, cross-referencing tool descriptions**. Frame around
"static reference vs. thing-I-build-and-grow", *not* data format (where overlap creeps
in). The tie-breaker for the genuine overlap (an existing file you just want to query):
prefer `connect`.

### D12. `create` and `connect` are the same op for a dataset

Opening a DuckDB connector **read-write at a non-existent path** creates the empty file
*and* is the live connection. No separate "create file then connect" step. Reuse the
workspace connector pattern; **not** `load_files` (nothing to load). Read-only open of a
missing file errors — datasets are RW precisely so the file is born and stays writable.

### D13. Export = `run_query` + DuckDB `COPY` — no dedicated tool

Export is the inverse of import, and import is already `run_query` with DuckDB's native
file reading (`read_csv_auto`/`read_parquet`). DuckDB has the symmetric write —
`COPY (SELECT …) TO '<path>' (FORMAT parquet|csv|json)` — which works through `run_query`
with the same in-process path semantics (cwd=project / `$SCRATCH`). Verified: `COPY … TO`
succeeds against a writable dataset/workspace. So a dedicated `export_record` tool is
**redundant** for the primary case (saving the data you *built*, which lives in a writable
DuckDB) and is dropped — one fewer tool, perfect import/export symmetry, smaller surface.

Gaps and how they're handled (none justify a tool):
- **Exotic formats** (xlsx, markdown, LaTeX) — not DuckDB-native → the bash escape hatch
  (COPY to parquet, then transform), consistent with the long-tail philosophy.
- **Read-only sources** — `COPY … TO` is blocked by the connector's read-only guard
  (it classifies COPY as a write). Route via the workspace, or — a possible future,
  principled relax — allow `COPY … TO` on read-only connectors (it reads the DB, doesn't
  modify it; only `COPY … FROM` is a real write). Not done now.
- **Overwrite** — `COPY` silently overwrites. Accepted: export is user-requested *with* a
  path, so clobbering the named file is the intent, and import has no guard either. (This
  reverses the earlier "typed tool with an overwrite guard" plan — the guard was the only
  thing a dedicated tool added, and it isn't worth a tool.)

The agent learns to export via `COPY … TO` through **prompt guidance** (Phase 6), the same
way it learns to import via `read_csv_auto`.

### D14. Visibility

Agent-initiated connect/create surface a **legible chat line** from the tool response
("✓ Connected `experiment_results` (1,234 rows)"). Export rides the visible `run_query`
tool call (the `COPY … TO` statement) plus the agent's natural-language confirmation.
The explorer reflects new sources on next open. A **live refresh of an already-open
explorer is deferred** (nice-to-have).

### D15. Wiring respects layering

App-owned registration policy reaches the agent via **injected callbacks**, threaded
through `ChatAgent` as **optional** dependencies (like `workspace`). Server/non-app
contexts leave them unset and the corresponding tools are not built. New agent tools live
in `toolhub` and depend only on callbacks/dirs handed in at construction — never importing
`app`.

---

## Tool surface (final)

| Tool | Layer | Mutates | Purpose |
|---|---|---|---|
| `execute_bash` (`ExecuteBashTool`, moved into toolhub) | toolhub | files in `$SCRATCH` (and project only on explicit request) | gather / custom transforms; cwd=project, network on, denylist guard |
| `connect_data_source` | toolhub (registry + data_dir) | registry (read-only source) | expose an existing file, db URL, or HF dataset as-is (defers credentialed URLs to the user) |
| `create_dataset` | toolhub (registry + data_dir) | registry (writable dataset) | new empty writable named DuckDB |
| `run_query` (extended) | toolhub | writable connectors only | query **and** ingest/append (gated by `read_only`) |
| *(export)* | — | a user-named file | not a tool — `run_query` + DuckDB `COPY … TO` (D13) |

---

## Implementation plan (phased, independently inspectable)

Each phase is self-contained, compiles/passes lint+mypy+tests, and has explicit
acceptance criteria. Inspect after each.

### Phase 0 — Foundations (no behavior change)

- Add `scratch_dir = session_dir / "scratch"` to `RuntimePaths`; create it at session
  start; wipe on clean exit (mirror dumps-cleanup pattern).
- Generalize `create_workspace_connector` → `create_duckdb_connector(db_path, alias, *, read_only)`;
  re-express the workspace in terms of it.
- Define the injection point on `ChatAgent`: optional host-action callbacks
  (e.g. a small `HostDataActions` protocol with `connect(...)` / `create_dataset(...)`),
  plus optional `project_dir` / `scratch_dir`. No new tools yet.

**Acceptance:** app starts unchanged; scratch dir exists; workspace still works; lint/mypy/tests green.

### Phase 1 — `run_query` write-enablement

- Relax `RegistryRunQueryTool` to permit non-SELECT statements, gated by
  `connector.read_only` (writable → allowed; read-only → clean error).

**Acceptance:** new tests — `CREATE TABLE`/`INSERT` succeeds against the writable workspace;
the same against a read-only connector fails with a clear message. SELECT behavior unchanged.

### Phase 2 — `create_dataset` (writable named dataset)

- App callback `create_dataset(name) -> alias`: sanitize/de-collide alias →
  `create_duckdb_connector(data_dir/<alias>.duckdb, alias, read_only=False)` →
  `_register_user_db(...)`.
- `CreateDatasetTool` (toolhub) — thin wrapper over the callback; emits a visible chat line.
- Wire the callback from the app into `ChatAgent`.

**Acceptance:** agent creates an empty dataset → appears in the explorer → `run_query`
`CREATE TABLE … AS SELECT * FROM read_csv_auto('<relative source glob>')` (Route A) populates
it. End-to-end with **no shell** for homogeneous source files.

### Phase 3 — Shell tool

**Reuse, don't rebuild.** A capable, well-tested `ExecuteBashTool` already existed in
`research/tools/` (persistent PTY session, completion detection, interrupt/background
support, output truncation, and a `command_filter` hook). It lived in `research`, a
sibling of `chat`, so the chat agent couldn't import it.

- **Move** `ExecuteBashTool` `research/tools/ → toolhub/` (below both `chat` and
  `research`); `research/tools/__init__` re-exports it so `dbt_agent` is unchanged.
- **`command_filter`** changed from `Callable[[str], bool]` → `Callable[[str], str | None]`
  (return a block reason, surfaced to the agent; `None` allows).
- **`toolhub/shell_guard.py`** — `dangerous_command_reason(cmd)`: small high-signal
  denylist (rm -rf of root/home/cwd, fork bomb, mkfs/dd, device/system writes, curl|sh,
  destructive git, shutdown, sudo). Guardrail, not a sandbox. Covered by `tests/test_shell_guard.py`.
- **Wire into `ChatAgent`** (built only when `project_dir`/`scratch_dir` are set):
  `working_dir=project_dir`, `init_commands=["export SCRATCH=<abs scratch>"]` (persists in
  the session shell), `command_filter=dangerous_command_reason`. Full env, network on.
- **Lifecycle:** `ChatAgent.aclose()` closes the persistent shell; called from the app's
  shutdown path.

**Acceptance:** denylist blocks a catastrophic command with a reason; an ordinary command
runs; cwd is the project dir; `$SCRATCH` is set and writable; writes default to scratch
(project stays clean). Route B end-to-end: shell writes `$SCRATCH/x.parquet`, `run_query`
ingests it by absolute path into a dataset.

### Phase 4 — `connect_data_source` (read-only)

**Self-contained, twin to `create_dataset` — no app callback.** `datasources < toolhub`,
so the tool calls `load_files`/`load_hf_dataset` directly; the only pull toward the app was
*session policy* (`note_event`, `_sources` dedup, sample-removal), and — as with
`create_dataset` — none of it is essential for the agent path:
- `note_event` is redundant (the agent initiates the connect and gets the alias back);
- source dedup is best-effort via alias collision (skip the `_sources` map);
- sample-removal is dropped from the agent path (consistent with `create_dataset`; the
  prompt already steers to real data). A uniform app-level cleanup can be revisited later.

- `ConnectDataSourceTool(registry, data_dir)` (toolhub): resolve `source` → `load_files`
  (local data file) or `load_hf_dataset` (HF URL) with `read_only=True` → `registry.register`.
- **Scope: any local file + database URL + HuggingFace.** Data files → `load_files`;
  local db files (SQLite/DuckDB) and **database URLs** (Postgres/MySQL/BigQuery/Snowflake/
  Neo4j) → `connect_url`; HF → `load_hf_dataset`. A URL that needs a password not in
  it is **deferred to the user** through an "ask the user to /connect" hint after
  an actual connection error. The response reports the source's **actual**
  dialect (e.g. `sqlite SQL` / `duckdb SQL` / `cypher`) so the agent writes correct syntax.
- **URL→connector logic lives in `data/url.py`** — `connect_url`, supported by
  `normalize_connection_url` and `is_database_file_path`. It is a smart constructor above the type-specific
  `from_url_async`, shared by `/cmd_connect` and the agent tool.
  `normalize_connection_url` is idempotent.
- Alias: the agent supplies it, used **verbatim-or-error** (like `create_dataset`) — no
  derivation, sanitization, or collision-suffixing; an invalid or taken alias is rejected.
- Response names the dialect (`sqlite SQL` / `duckdb SQL`, N tables), host-agnostic.
  Descriptions are **self-contained — no sibling tool names** (so the tools stay modular
  for standalone library use); disambiguation from `create_dataset` comes from each tool's
  own description (read-only/existing vs writable/new), not cross-references.
- `/cmd_connect` is **untouched** — no shared factoring needed (both already share
  `load_files`/`load_hf_dataset` in `datasources`).

**Acceptance:** agent connects a local CSV (and a HuggingFace dataset) read-only; writes are
refused; re-connecting suffixes the alias; db-file / missing-file / bad-alias return clear
errors; `/connect` slash behavior unchanged.

### Phase 5 — Export (no tool)

**Dropped as a tool** (D13): export is `run_query` + DuckDB `COPY (…) TO '<path>' (FORMAT …)`,
the mirror of import. No code; the agent learns it via prompt guidance in Phase 6.

### Phase 6 — Prompts, polish, QA

- System-prompt additions: the per-session absolute scratch path; the `connect` vs
  `create_dataset` rule (D11); shell usage ("write intermediates to `$SCRATCH`, absolute";
  prefer parquet; one-shot `COPY … TO … (FORMAT parquet)` when sources are tabular);
  **export guidance** — save results with `COPY (SELECT …) TO '<path>' (FORMAT parquet|csv|json)`
  via `run_query` (from a writable dataset/workspace); exotic formats (xlsx/markdown/LaTeX)
  via the shell.
- Confirm chat-stream visibility lines render; confirm session-end scratch wipe.

**Acceptance:** full manual QA of the motivating scenario — *scattered `output/` results →
agent gathers → dataset appears in explorer → user asks to add more → appended →
user asks to export → file written via `COPY … TO`*. lint/mypy/tests green.

---

## Out of scope / deferred / rejected

- **Cross-session dataset persistence** — out of scope (D6). Would require a stable
  non-session location, a dataset registry/reattach, and a single-writer policy across
  concurrent app instances.
- **OS-level sandbox** (`sandbox-exec`/bubblewrap) — rejected (D2): not cross-platform,
  deprecated, fragile.
- **Tool-confirmation UI** for shell/connect — not built; auto-run + denylist + visible
  chat lines instead. (A y/n confirmation path is a possible future safer mode.)
- **Live refresh of an already-open explorer** — deferred (D14).
- **`$SCRATCH`-token expansion inside `run_query`** — optional future nicety; default to
  literal absolute paths (D10).
- **Agent connecting credential-requiring DB URLs** — the agent path is scoped to
  HF/files/credential-less sources (D11/Phase 4); password-prompt connects stay a user
  action.
