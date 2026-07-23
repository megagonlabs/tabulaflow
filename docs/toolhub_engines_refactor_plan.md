# toolhub `engines/` refactor — plan

Separate the non-tool machinery in `tabulaflow/toolhub/` from the tools themselves.
Today the package is 30 flat modules mixing three kinds of code; this plan quarantines
the deterministic engine/helper files into a `toolhub/engines/` subpackage while
keeping the top-level `tabulaflow.toolhub` package exports unchanged.

## Diagnosis (current state)

`toolhub/` contains three distinct kinds of non-tool code, only one of which is the
problem:

1. **Tools (20 files, fine as-is)** — one `*Tool` per file: `run_query`,
   `execute_bash`, `file_editor`, `apply_patch`, `web_browser`, the six `registry_*`,
   the three `render_*`, `get_table_schema`, `get_column_json_schema`,
   `add_canonical_name`, `connect_data_source`, `extract_rows_from_documents`,
   `run_subagent_for_each_row`.
2. **Deterministic engines/helpers (7 files, ~2,100 lines) — the clutter**:
   `aria_to_markdown.py` (1,312 lines, used only by `web_browser`),
   `markdown_splitter.py` (439), `pdf_extract.py`, `fs_roots.py`, `shell_guard.py`,
   `column_types.py`, `utils.py`.
3. **Shared session state (2 files, correctly top-level)** — `query_history.py` and
   `message_store.py`. Not utils: runtime state objects that tools write into and
   `app`/`chat` read from. Part of toolhub's public API.

Plus `base.py` (protocols) and `entity_extractor.py` — an LLM-powered helper, not a
`BaseTool`, but public and consumed by a tool. It cannot move to `modulehub` without
inverting the layering (`toolhub < modulehub`), so it stays top-level.

## Decisions (settled — do not relitigate)

1. **Tools stay flat at the top level.** They are the package's identity;
   `toolhub.run_query` reads better than `toolhub.tools.run_query`, and nesting them
   would churn every deep import for a stuttery name.
2. **Subpackage name is `engines/`.** It matches the vocabulary the repo already uses
   ("Add pure apply_patch engine" commits) and describes what unifies these files:
   deterministic machinery that does a tool's heavy lifting. Unlike `utils/` or
   `support/`, it resists grab-bag creep — "is this an engine?" has an answer.
   Not underscore-private: these modules are legitimately imported across layers
   (`chat/agent.py` uses `shell_guard`, `research/tools` uses SQL helpers).
3. **Engines do not move down to `core`** despite being deterministic. They exist
   solely to serve specific tools; code lives in its consumer's layer. Moving them
   would bloat `core` with browser/patch machinery nothing else uses.
4. **`query_history.py`, `message_store.py`, `entity_extractor.py`, `base.py` stay
   top-level** (see diagnosis).
5. **Top-level package API is unchanged** — `toolhub/__init__.py` re-exports stay
   identical. Deep imports into implementation modules intentionally move, e.g.
   `tabulaflow.toolhub.markdown_splitter` becomes
   `tabulaflow.toolhub.engines.markdown_splitter`.

## Target structure

```
toolhub/
├── __init__.py              # top-level public API unchanged
├── base.py                  # BaseTool, LLMProfileTool, + sum_tool_metrics (moved in)
├── query_history.py         # shared state
├── message_store.py         # shared state
├── entity_extractor.py      # LLM helper
├── <20 tool files>          # flat, unchanged
└── engines/
    ├── __init__.py
    ├── aria_to_markdown.py
    ├── markdown_splitter.py
    ├── patch_engine.py      # extracted from apply_patch.py (see Phase 2)
    ├── pdf_extract.py
    ├── fs_roots.py
    ├── shell_guard.py
    ├── column_types.py
    └── sql.py               # renamed from utils.py (see Phase 2)
```

## Phases

Stop at the end of each phase for user inspection before starting the next.

### Phase 1 — mechanical move

- Create `toolhub/engines/` and `git mv` the six existing engine files into it
  (`aria_to_markdown`, `markdown_splitter`, `pdf_extract`, `fs_roots`, `shell_guard`,
  `column_types`).
- Update all import sites. Known deep importers outside toolhub itself:
  - `tabulaflow/chat/agent.py` — `shell_guard.dangerous_command_reason`
  - tests: `test_aria_to_markdown.py`, `test_markdown_splitter.py`,
    `test_shell_guard.py`, `test_extract_rows_from_documents.py`
- Verify: `make lint`, `make mypy`, `make lint-arch`, `make test`.

### Phase 2 — dissolve the grab-bags

- **Split `utils.py`.** `sum_tool_metrics` operates on `BaseToolMetrics` and moves to
  `base.py` next to that type. The remaining coherent set of SQL-identifier helpers
  (`equals_ci`, `qualified_table`, `sa_table`, `format_sqlalchemy_error_msg`) becomes
  `engines/sql.py`. A `utils.py` inside `engines/` would recreate the smell this
  refactor removes. Known external importers:
  `tabulaflow/research/tools/get_column_description.py` and `search_keywords.py`
  use `equals_ci`.
- **Extract the patch engine from `apply_patch.py`.** The file's docstring says "Pure
  engine for OpenAI V4A apply_patch patches" but it mixes the ~450-line pure engine
  (`Parser`, `Patch`, `Chunk`, `PatchAction`, `Commit`, `DiffError`, apply logic)
  with `ApplyPatchTool`. Engine → `engines/patch_engine.py`; the tool stays in
  `apply_patch.py` — the same pattern `file_editor`/`fs_roots` already follows.
  Update `tests/test_apply_patch.py` imports accordingly.
- Verify: same commands as Phase 1.
