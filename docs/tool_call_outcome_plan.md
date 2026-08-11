# Structured per-call tool outcomes — implementation plan

Finish the migration of tool-outcome display facts (the `→ 42 rows` / `→ error`
suffixes on tool steps) to a single typed fact that rides each tool call's own
return, end to end: toolhub states facts, chat transports them, the app words
them. This replaces the intermediate implementation currently in the tree (see
Baseline below).

## Background and decisions (already settled — do not relitigate)

The original bug: `ToolFinished.outcome` was derived from last-write-wins shared
state (`output_store.last()`, `last_columns_returned`), so concurrent calls of
the same tool in one turn could cross-attribute row/column counts or failed
states. The fix direction — verified against the installed pydantic-ai — is that
facts ride the call's own return: a tool returns
`pydantic_ai.ToolReturn(return_value=..., metadata=...)`; the runtime copies
`metadata` verbatim onto the `ToolReturnPart` (see `_agent_graph.py`), which is
what `FunctionToolResultEvent.result` carries in chat's stream handler.
`metadata` is never sent to the model. `ToolReturn` is a top-level
`pydantic_ai` export.

Decisions from design discussion:

1. **`ToolCallOutcome` is a typed frozen dataclass** in `toolhub/base.py` — not
   an untyped dict. The wire contract must remain a schema frontends can
   validate against; stringly keys fail silently (a `"row"` typo renders as
   nothing) and force defensive `isinstance` parsing in every consumer.
2. **Fields are generic: `count` / `unit` / `error`** — not `rows` / `columns`.
   Tool nouns in the shared type were the real extensibility limiter. With
   `count`+`unit`, `run_query` attaches `(3, "rows")`, `get_table_schema`
   attaches `(12, "columns")`, and any future or user-defined tool attaching
   `(5, "files")` renders with **zero changes** to toolhub, chat, events, or
   app. This mirrors `ToolProgressUpdate`'s `completed`/`unit` idiom, giving
   toolhub one coherent shape for progress and outcome.
3. **`__call__` returns `ToolReturn` and is the single core** of the two
   outcome-reporting registry tools. Grep-verified: no production code calls
   their `__call__` — only tests (chat and `run_subagent_for_each_row` use
   `as_pydantic_ai_tool()`). So the `_execute` / `_execute_llm` / `__call__`
   projection split is speculative API and gets deleted. Schema wrappers become
   one-line delegations to `__call__`.
4. **Only tools with facts return `ToolReturn`.** All other toolhub tools keep
   returning `str` (pydantic-ai wraps plain values automatically). Layer rule:
   *returns `ToolReturn` ⇔ reports host-facing facts*. Do not impose the
   envelope on tools with nothing to put in it.
5. **The `ToolOutcome` union in `chat/events.py` is deleted.**
   `ToolFinished.outcome` carries `ToolCallOutcome | None` directly; the app
   layer words it (it already owns the wording). Chat keeps exactly one
   normalization: the toolhub-wide `"(error:"` string-return convention becomes
   `ToolCallOutcome(error=True)` at the chat boundary, so no frontend ever
   learns toolhub string conventions (same rationale as `_TextStreamRouter`).
   `Failed.message` is dead code (never populated) and disappears with the
   union.
6. **Do not symmetrically collapse `ToolProgress`/`ToolProgressUpdate`** — there
   the adapter is one constructor call with no union behind it; nothing to
   delete. Collapse only where there is real weight.
7. Unknown `db_alias` reports `error=True` (renders as failed). This was a
   deliberate behavior change already made in the baseline; keep it.
8. Metadata not recognized as `ToolCallOutcome` degrades gracefully to no
   outcome (channel stays open at the pydantic-ai level; only the rendered
   vocabulary is typed). Rich non-count payloads from hypothetical future tools
   are a *new* typed field/event when a concrete need exists — do not pre-build
   an open passthrough.

## Baseline (what is in the tree now)

An intermediate version of this design is already implemented and verified
(927 tests passing). Identify it by these symbols, not by git state:

- `toolhub/base.py`: `ToolCallOutcome(rows, columns, error)` — **old field
  names**, to be changed.
- `toolhub/registry_run_query.py`: `_execute -> tuple[str, ToolCallOutcome | None]`,
  `_execute_llm -> ToolReturn`, four LLM wrappers returning `ToolReturn`,
  `__call__ -> str`. The `[record_id=...]` marker prefix on returns is a
  model-facing contract — **keep it**.
- `toolhub/registry_get_table_schema.py`: same `_execute`/`_execute_llm`
  pattern. The inner `toolhub/get_table_schema.py` already has
  `execute(...) -> tuple[str, int | None]` — **leave the inner tool unchanged**.
- `chat/agent.py`: `_build_outcome(result_part)` maps metadata to the union;
  `_emit_stream_event(event, emit, text_router)`.
- `chat/events.py`: `RowsReturned` / `ColumnsReturned` / `Failed` / `Completed`
  / `_Outcome` / `ToolOutcome` union, plus a tool→outcome comment table.
- `app/widgets.py`: `summarize_outcome` isinstance-chain over the union.
- Tests: `tests/test_tool_call_outcome.py` (asserts old field names),
  `tests/test_registry_tools_rebind.py` (two direct `await tool(...)` calls
  asserting on `str`), `tests/test_tool_labels.py` (`summarize_outcome` cases).

## Changes

### 1. `toolhub/base.py`

```python
@dataclass(frozen=True)
class ToolCallOutcome:
    """Facts about one completed tool call, for the host's display.

    Attached as ``pydantic_ai.ToolReturn.metadata`` by a tool's LLM-facing
    entrypoints, so it rides the call's own return — never sent to the model.

    Attributes:
        count: Units of work the call returned (e.g. result rows).
        unit: Noun for the count (e.g. ``"rows"``, ``"columns"``).
        error: Whether the call failed.
    """

    count: int | None = None
    unit: str | None = None
    error: bool = False
```

### 2. `toolhub/registry_run_query.py`

- Move `_execute`'s logic into `__call__`, returning `ToolReturn`. Keep the
  `refresh and self.enable_refresh` gate in `__call__`. Delete `_execute` and
  `_execute_llm`.
- Metadata: success with df → `ToolCallOutcome(count=len(df), unit="rows")`;
  exec error → `ToolCallOutcome(error=True)`; unknown alias →
  `ToolCallOutcome(error=True)`; otherwise `None`.
- The four schema wrappers become `return await self(db_alias, query, ...)`
  (annotated `-> ToolReturn`). Their signatures and docstrings are the
  LLM-facing schema — do not change parameters or docstrings.

### 3. `toolhub/registry_get_table_schema.py`

- Same shape: `__call__ -> ToolReturn` is the core (calls the inner tool's
  `execute()`), wrappers delegate, `_execute`/`_execute_llm` deleted.
- Metadata: inner count `n` → `ToolCallOutcome(count=n, unit="columns")`;
  unknown alias or non-SQL `TypeError` → `ToolCallOutcome(error=True)`; inner
  `n is None` (table not found, bad regex, over max_columns) → `None`.

### 4. `chat/events.py` and `chat/__init__.py`

- Delete `_Outcome`, `RowsReturned`, `ColumnsReturned`, `Failed`, `Completed`,
  the `ToolOutcome` alias, and the tool→outcome comment block.
- `from tabulaflow.toolhub import ToolCallOutcome` (layering-legal: toolhub <
  chat) and change `ToolFinished.outcome: ToolCallOutcome | None = None`.
  **Plain completion is `outcome=None`** — `null` in the serialized event, no
  suffix in the app. There is no `Completed` value anywhere anymore.
  pydantic serializes/validates frozen stdlib dataclass fields natively, so the
  `TypeAdapter(ChatEvent)` round-trip promised by the module docstring still
  holds — update that docstring's outcome wording.
- Import-weight note: this import does make bare `chat.events` consumers pull
  `toolhub/__init__`. Spelling it `from tabulaflow.toolhub.base import ...`
  would NOT avoid that — importing any submodule executes the parent package's
  `__init__` — so use the public re-export per repo convention. In practice
  every real chat consumer already imports `ChatAgent`, which imports toolhub
  at module level; if bare-events import weight ever matters, the fix is
  trimming `toolhub/__init__`'s eagerness, not the import spelling.
- `chat/__init__.py` re-exports `RowsReturned`, `ColumnsReturned`, `Failed`,
  `Completed`, `ToolOutcome` — remove them from the import and `__all__`, and
  re-export `ToolCallOutcome` instead (it is now part of the chat event
  contract frontends consume).

### 5. `chat/agent.py`

- Delete `_build_outcome`. In `_emit_stream_event`'s
  `FunctionToolResultEvent` branch, inline:

```python
outcome = result_part.metadata if result_part is not None else None
if not isinstance(outcome, ToolCallOutcome):
    outcome = None
if outcome is None:
    content = result_part.content if result_part is not None else None
    if isinstance(content, str) and content.startswith("(error:"):
        outcome = ToolCallOutcome(error=True)
emit(ToolFinished(tool_call_id=event.tool_call_id, name=tool_name, outcome=outcome))
```

  (`ToolCallOutcome` imported lazily inside the function, matching the file's
  convention for toolhub imports.)
- Remove now-unused imports (`RowsReturned`, `ColumnsReturned`, `Failed`,
  `Completed`, `ToolOutcome`).

### 6. `app/widgets.py`

- `summarize_outcome(outcome: ToolCallOutcome | None) -> str`, importing
  `ToolCallOutcome` from `tabulaflow.chat.events` (frontends depend only on the
  chat contract): `error` → `"error"`; `count is not None` →
  `f"{count} {unit}"` (bare `str(count)` if `unit` is `None`); else `""`.
- Update the `chat.events` import list at the top of the file.

### 7. Tests

- `tests/test_tool_call_outcome.py`: switch assertions to `count`/`unit`
  fields; `__call__` now returns `ToolReturn`, so rework
  `test_programmatic_call_returns_text` to assert `ToolReturn` +
  `.return_value` prefix.
- Replace the `TestBuildOutcome` class with a chat-normalization test that
  MUST be kept (the `"(error:"` → `ToolCallOutcome(error=True)` fallback is a
  boundary rule): drive `_emit_stream_event` with a constructed
  `FunctionToolResultEvent` (collecting `emit` into a list, fresh
  `_TextStreamRouter`) and assert the emitted `ToolFinished.outcome` for three
  cases — metadata passthrough, `"(error:"` content fallback, and plain
  completion (`outcome is None`).
- `tests/test_registry_tools_rebind.py`: the two direct calls now return
  `ToolReturn`; assert against `.return_value`.
- `tests/test_tool_labels.py`: `summarize_outcome` cases use
  `ToolCallOutcome(count=42, unit="rows")` etc., and `None` → `""`.
- Stale-reference sweep with targeted patterns (a bare `Failed`/`Completed`
  grep drowns in unrelated strings and vendored assets):

```bash
rg -n "\b(RowsReturned|ColumnsReturned|ToolOutcome)\b" tabulaflow tests --glob '!tabulaflow/app/**/assets/**'
rg -n "from tabulaflow\.chat(\.events)? import .*\b(Failed|Completed)\b" tabulaflow tests
```

## Verification

- `uv run ruff format <changed files>` and `uv run ruff check --fix <changed
  files>` — **scoped to the changed files only, never repo-wide**.
- `make mypy`, `make test`, `make lint-arch` — all must pass.
- Do not touch any `tabulaflow/research` path. Do not commit unless the user
  explicitly asks.
