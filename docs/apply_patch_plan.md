# apply_patch tool — implementation plan

Add an `apply_patch` file-editing tool (OpenAI V4A patch format, the native editing
format of GPT-5.x models) to toolhub, and wire it into `ChatAgent` for the app.
Implemented in phases; **stop at the end of each phase for user inspection before
starting the next.** Do not touch any `tabulaflow.research` path in this change.

## Background and decisions (already settled — do not relitigate)

GPT-5.x models are RL-trained to edit files via an `apply_patch` tool that takes a
multi-file patch in the "V4A" envelope format (`*** Begin Patch` / `*** Update File:`
/ `@@` hunks / `*** End Patch`). Codex exposes it as an OpenAI Responses API
`type: "custom"` (freeform grammar) tool; however **pydantic_ai (1.107.1, what we
use) has no end-to-end custom-tool support** for this use case. Normal pydantic_ai
tools are JSON-schema function tools, and `OpenAIResponsesModel` currently does not
execute/replay `custom_tool_call` or `apply_patch_call` response items. Decisions:

1. **Declare `apply_patch` as a normal JSON function tool** with a single required
   `patch: str` parameter. This is exactly what OpenHands ships in production for
   GPT-5.1 (`cloned/software-agent-sdk/openhands-tools/openhands/tools/apply_patch/definition.py`).
   The tool name must be exactly `apply_patch` and the schema minimal, so the
   model's training on the tool kicks in. No pydantic_ai changes, no wrapper-model
   surgery.
2. **Port the OpenHands/OpenAI-cookbook engine as the base algorithm**
   (`cloned/software-agent-sdk/openhands-tools/openhands/tools/apply_patch/core.py`,
   ~480 lines, pure Python with injected file I/O), keeping two
   fidelity-critical OpenHands/cookbook behaviors:
   - **Splice semantics**: context lines are copied from the *original file*, only
     `+`/`-` runs are inserted/deleted. (Codex replaces the whole matched block
     with patch-authored lines, which can rewrite context after a fuzzy match.)
   - **Anchored pure-inserts**: a section with only `+` lines inserts at the `@@`
     anchor position. (Codex appends no-old-line chunks at end-of-file; we choose
     the OpenHands/cookbook behavior for compatibility with that JSON tool.)
3. **Harden the base with four codex-inspired changes** after the faithful port
   (details in Phase 1B).
4. **Do not modify or replace `file_editor`** — `apply_patch` is a separate,
   additive tool. Agents that get `apply_patch` keep `file_editor` for `view`.
5. Wire the tool only into the app-facing `ChatAgent`, when `project_dir` is
   available. Do not wire it into `dbt_agent`, research configs, or
   `tabulaflow.research.tools`.

Reference implementations to consult while porting:
- OpenHands engine: `cloned/software-agent-sdk/openhands-tools/openhands/tools/apply_patch/core.py`
- OpenHands tool/executor: `.../apply_patch/definition.py`
- Codex matcher (Unicode tier): `cloned/codex/codex-rs/apply-patch/src/seek_sequence.rs`
- Codex parser/apply (for behavior comparison only): `cloned/codex/codex-rs/apply-patch/src/{streaming_parser.rs,lib.rs}`

## Phase 1A — OpenHands/cookbook V4A engine (pure logic, no tool yet)

**Deliverable**: `tabulaflow/toolhub/apply_patch.py` containing the parse/locate/apply
engine as pure functions + dataclass-or-pydantic models (mirror the OpenHands
structure: `Parser`, `Chunk`, `PatchAction`, `Patch`, `Commit`, `DiffError`,
`process_patch(text, open_fn, write_fn, remove_fn)` with injected I/O callables).
Port from the OpenHands `core.py` first, preserving its behavior before hardening.

Preserve these OpenHands/cookbook semantics:
- Splice semantics: context lines are copied from the original file, while `+`/`-`
  runs are inserted/deleted.
- Anchored pure-inserts: a section with only `+` lines inserts at its located `@@`
  anchor position, not end-of-file.
- Injected file I/O: no direct filesystem access inside the engine.
- Fuzz counter and return shape from `process_patch`.
- Whole-commit shape: parse and compute the commit before applying writes.

Additional requirements:
- Avoid global `text.strip()` parsing. Preserve raw line positions enough that
  diagnostics and leading/trailing patch whitespace behave predictably; accepting a
  final newline around `*** End Patch` is fine.
- Where cheap, include the patch line number in `DiffError` messages ("line 12:
  Unknown Line: ...") — the model repairs its patch from these messages.
- Error cases must all raise `DiffError` (never assert) so the tool layer can
  return them as tool errors: bad envelope, unknown line, missing/duplicate file,
  context not found, overlapping chunks.

**Tests** (`tests/test_apply_patch.py`), engine-level, driven through
`process_patch` with dict-backed fake I/O:
- Add / Update / Delete / Move-to, single- and multi-file patches.
- Update with `@@` context headers, bare `@@`, and no header for the first chunk.
- Pure-insert section anchored by `@@` lands after the anchor (not at EOF).
- OpenHands fuzzy tiers: trailing-whitespace mismatch and indentation mismatch
  apply, report fuzz > 0, and preserve the file's original context lines
  byte-for-byte.
- OpenHands EOF fallback behavior is documented by a test before Phase 1B changes
  it.
- Errors: bad envelope, unknown marker line, update of missing file, duplicate
  path in one patch, context not found.
- Empty body line without leading space treated as empty context line.

**Checkpoint**: user reviews the faithful port and tests. Run
`uv run pytest tests/test_apply_patch.py`, `make lint`, `make mypy` (scope any
formatting to changed files only).

## Phase 1B — Codex-inspired engine hardening

**Deliverable**: harden the Phase 1A engine without changing the public tool API.
Apply these deltas:

1. **Unicode-normalization fuzzy tier.** `find_context_core` currently has three
   tiers: exact → rstrip → strip. Add a fourth, most-permissive tier that compares
   lines after normalizing typographic characters to ASCII (dashes/hyphens → `-`,
   curly single/double quotes → `'`/`"`, exotic spaces → ` `; copy the mapping
   from codex `seek_sequence.rs:76-94`). Count it as high fuzz (e.g. `fuzz += 1000`).
   Safe under splice semantics — original context lines are never rewritten.
2. **Strict `*** End of File`.** Drop the OpenHands fallback that matches an EOF
   section anywhere in the file with `fuzz += 10000`. If the section doesn't match
   end-anchored, raise `DiffError` (codex behavior).
3. **`*** Add File` must not overwrite.** The engine can't see the filesystem, so
   surface this at the boundary: `process_patch` receives an `exists_fn` (or the
   Add path check happens in the tool executor in Phase 2 — implementer's choice,
   but the error must be a `DiffError` before any write happens).
4. **Trailing-newline normalization.** Written file contents always end with
   exactly one trailing newline (codex `lib.rs:687-689` behavior). Update matching
   must tolerate a final empty patch line representing the file's trailing newline.

Additional requirements:
- Keep whole-commit atomicity. Parse the whole patch, compute every target file's
  new content, and validate every engine-visible semantic constraint before the
  first write. The tool layer adds path/PDF/binary validation in Phase 2 before it
  invokes writes. A later `write_fn` failure can still leave partial OS-level
  effects, but semantic patch errors must not.
- Error cases must all raise `DiffError` (never assert) so the tool layer can
  return them as tool errors, including add-over-existing and misplaced EOF section.

**Tests** (extend `tests/test_apply_patch.py`):
- Unicode quotes/dashes mismatch applies, reports fuzz > 0, and preserves original
  context lines byte-for-byte.
- `*** End of File` matching at end works; the same section not at file end raises.
- Add-over-existing raises before any write.
- Trailing-newline invariant on written content.
- Atomicity: a two-file patch whose second file fails leaves the first untouched.

**Checkpoint**: user reviews hardening semantics + tests. Run
`uv run pytest tests/test_apply_patch.py`, `make lint`, `make mypy` (scope any
formatting to changed files only).

## Phase 2 — `ApplyPatchTool` (toolhub tool class)

**Deliverable**: `ApplyPatchTool` in the same module, following the toolhub
conventions in `tabulaflow/toolhub/file_editor.py` (class with `name: ClassVar =
"apply_patch"`, async `__call__`, `as_pydantic_ai_tool()` returning
`Tool(self.__call__, name=self.name)`, a small pydantic metrics model).

- **Signature**: `async def __call__(self, patch: str) -> str` — one required
  parameter, nothing else. The docstring (= tool description) states what the tool
  does and the envelope format concisely; per repo guidelines, no lecturing.
- **Path scoping**: constructor takes `working_dir` and resolves/validates every
  patch path against it exactly like `FileEditorTool._resolve` (relative paths
  resolve against `working_dir`; escapes raise). Match `FileEditorTool`'s
  constructor policy: default to `working_dir`-scoped access, but allow
  `allowed_roots=None` for unrestricted host-file access. Reuse by extracting the
  root resolution helpers (`FileEditorRoot`, `_ResolvedFileEditorRoot`, `_resolve`,
  `_root_for`) from `file_editor.py` into `tabulaflow/toolhub/engines/file_access.py`,
  and update `FileEditorTool` to use the extracted module in the same change. Keep the
  public re-export in `toolhub/__init__.py` working. Do not touch
  `tabulaflow/research/tools/__init__.py`.
- **Parent directories**: `*** Add File` and `*** Move to` writes create missing
  parent directories, matching OpenHands/Codex behavior.
- **Result string**: on success, a per-file summary, one line per change
  (`A path`, `M path`, `M old -> new` for moves, `D path`), plus a
  `(fuzzy-matched, fuzz=N)` note when fuzz > 0. On `DiffError`, return
  `(error: ...)` following the `file_editor` `_error` convention, and count it in
  metrics. Never let `DiffError` escape as an exception.
- Reject edits to PDFs the same way `file_editor` does (reuse its `_is_pdf` check
  is not needed — a simple extension check is fine here; patches are text-only).
- Export `ApplyPatchTool` from `tabulaflow/toolhub/__init__.py` only.

**Tests** (extend `tests/test_apply_patch.py`): tool-level round trips on a tmp
dir; path escape rejected (`../outside.txt`, absolute path outside root); atomicity
(a two-file patch whose second file fails leaves the first untouched); result
formatting; metrics counts; missing parent directories are created for adds/moves;
existing `tests/test_file_editor.py` still passes after the `file_access.py`
extraction.

**Checkpoint**: user reviews tool API, the `file_access` extraction diff, and result
formatting. `make test` should pass.

## Phase 3 — wire into `ChatAgent`

**Deliverable**: app-facing `ChatAgent` wiring only (`tabulaflow/chat/agent.py` and
`tabulaflow/chat/system_prompt.md` or the session-tail prompt composer):

- Add `apply_patch: ApplyPatchTool | None` to the internal `_Toolset`.
- Build `ApplyPatchTool` when `project_dir` is present, next to `FileEditorTool`.
  In ChatAgent, pass `allowed_roots=None` so `apply_patch` has the same host-file
  access policy as `file_editor`. The lower-level tool default remains conservative
  (`working_dir`-scoped) for direct construction elsewhere.
- Add it to the `host_tools` list in `_make_agent()`, next to `file_editor`.
- Keep `file_editor` — the agent still uses it for `view`, PDF text extraction, and
  small direct edits.
- Prompt guidance should reflect availability. Prefer a session-tail line emitted
  only when `project_dir` exists, e.g. "File editing tools: use `file_editor` to
  view files; use `apply_patch` for multi-file text edits." A short static
  "when available" line in `system_prompt.md` is also acceptable, but avoid a
  misleading unconditional instruction when host tools are omitted.

**Tests**:
- `ChatAgent(project_dir=...)` builds both `file_editor` and `apply_patch`.
- `ChatAgent(project_dir=None)` omits both host file-editing tools.
- The pydantic-ai tool list includes `apply_patch` when host tools are available.
- `apply_patch` in ChatAgent can edit the same outside-project path that
  `file_editor` can edit under the existing unrestricted ChatAgent policy.
- Prompt/session tail mentions `apply_patch` only when the tool is available.

**Checkpoint**: user reviews wiring + prompt diff.

## Phase 4 — validation run (user-driven)

Run the app with a GPT-5 model and ask it to make a small multi-file text edit in a
throwaway project directory. Inspect the app trajectory for: the model actually
calling `apply_patch`, `DiffError` rate, JSON-escaping failures (invalid tool args),
fuzz warnings, result formatting, and whether the prompt still uses `file_editor`
for viewing. This phase produces observations, not code; any fixes loop back into
the relevant phase.

## Out of scope

- OpenAI `type: "custom"` freeform declaration with a Lark grammar — blocked on
  pydantic_ai upstream (issue #2513; PRs #2572/#3612 both closed unmerged).
  The JSON tool is forward-compatible: if upstream lands support, only the
  declaration changes, the engine and tool stay.
- Any `tabulaflow.research` changes, including `dbt_agent`, experiment configs,
  research pipelines, or `tabulaflow/research/tools/__init__.py`.
- Codex-style shell heredoc interception of `apply_patch` — irrelevant to our
  agents.

## Conventions for the implementing agent

- `uv` for everything; `make test`, `make lint`, `make mypy` before each
  checkpoint. Scope `ruff format` to files you changed — never the whole tree.
- Google-style docstrings; no comments on self-explanatory code.
- Do not commit — the user inspects each phase first.
