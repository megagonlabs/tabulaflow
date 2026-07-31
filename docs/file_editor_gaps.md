# `file_editor` — gaps that push an agent to the shell

Status: observations from using the tool, not a plan. No decisions taken.

`FileEditorTool` (`tabulaflow/toolhub/file_editor.py`) exposes `view`, `write_file`
and `str_replace` — one edit per call, exact whitespace-sensitive matching, and it
fails loudly when `old_str` matches zero times or (without `replace_all`) more than
once. That failure behavior is the tool's main safety property and it works: a stale
anchor errors instead of landing a mangled edit.

The gaps below are all cases where that safety is *bypassed*, because the cheapest way
to make the edit is `execute_bash` with a Python or `sed` one-liner — where a
mismatched anchor is a silent no-op and the write is not shown as a diff.

## 1. No multi-edit call, and `apply_patch` is provider-gated

A mechanical change that touches N sites in one file costs N sequential
`str_replace` calls. Example from threading an `exclude_schema_names` parameter
through `sql_conn.py`: six insertions (function signature, docstring, pass-through
call, config dataclass field, `_SchemaBuildConfig` construction, refresh path) —
each nearly identical, each needing its own call and its own snippet response.

`ApplyPatchTool` covers exactly this, but `_model_supports_apply_patch`
(`tabulaflow/chat/agent.py:102`) restricts it to `openai-responses:gpt-5*`, and
`docs/apply_patch_plan.md` fixes that scope deliberately (V4A is what those models
are trained on). So on any other provider the agent has only one-edit-per-call
`file_editor`, and a scripted fallback starts to look rational — at the cost of the
loud-failure guarantee.

Possible direction: accept a list of `{old_str, new_str}` edits in one `str_replace`
call, applied atomically — all anchors must match uniquely, or nothing is written.
That keeps the exact-match contract while removing the N-call tax, and needs no
provider-specific format.

## 2. No way to add lines to the end of a file

Appending (e.g. one new test to an existing test module) has no command. The options
are `write_file`, which rewrites the whole file from the model's memory of it, or
shell `cat >>`. Both are worse than the edit deserves: the first risks silently
dropping content the model misremembered, the second leaves no diff and no
validation.

Possible direction: an `insert` command taking a line number (0 = start, omitted =
end), or an `append` mode. Cheap, and it removes the most common reason to reach for
`write_file` on a file that already exists.

## 3. Nothing survives a mid-sequence failure

A change that needs several calls has no transaction. If call 4 of 6 fails — a stale
anchor because a formatter ran, or a typo — the file is left half-edited, and
recovering means reconstructing which edits landed. Atomic multi-edit (gap 1) fixes
this case too.

## 4. `replace_all` reports only the first site

`_str_replace` returns a snippet around the first replacement plus a count
(`file_editor.py:313`). With `replace_all=true` and four matches, the other three are
invisible; the agent has to `view` again or take the count on trust. Returning the
line numbers of every replacement (the error path already computes them for the
"found N times" message) would close that without adding output bulk.

## Related friction, not defects

- **Formatter races.** `make format` rewrites files, so any anchor the agent captured
  before it is stale afterwards. The tool errors correctly; the cost is a re-read.
  Worth remembering when a task mixes editing with `make format`.
- **Large-file reads.** A 2900-line module like `sql_conn.py` can't be held in context,
  so edits proceed from `grep` + narrow `view` ranges. That is the right shape, but it
  means anchors are chosen from a small window and are more likely to be non-unique —
  which the tool then rejects, correctly, costing another round trip.
