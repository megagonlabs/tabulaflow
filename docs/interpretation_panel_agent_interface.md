# Interpretation Panel — Agent-Facing Interface

Status: `run_query_for_each_combination` is implemented (`tabulaflow/toolhub/run_query_for_each_combination.py`,
not yet wired into the chat toolset); `show_artifacts` is designed, not implemented.

Supersedes the "Proposed tool surface", "Query alignment idea" and "Why not fully implicit query
expansion?" sections of `interpretation_panel_design.md`. The product direction, UI prototype notes
and visual language in that doc still apply.

**Deferred, not in v1:**

- Charts, maps and graphs over interpretations (`render_chart` / `render_map` / `render_graph` on a
  combination set). v1 panels hold table cards only.
- Browser output pane support. v1 is TUI-only; the pane renders the first combination or nothing.

## Summary

Two tools, and no change to `run_query`:

| tool | job |
|---|---|
| `run_query_for_each_combination` | run one query template over the combinations of some dimensions |
| `show_artifacts` | declare the turn's cards, and the dimensions the user may switch between |

`show_artifacts` replaces the `<artifacts>` citation block entirely — see
[Replacing the citation block](#replacing-the-citation-block).

## Model

- A **dimension** is one ambiguity in the question (`ranking`, `period`), with an ordered list of
  **choices** (`net_revenue`, `order_count`). Choices are listed best-reading-first; the panel opens
  on the first choice of every dimension. There is no separate default.
- A **combination** is one choice per dimension — a point the user can select.
- A **card** is one labelled result view. The card set is fixed: the same labels, in the same order,
  at every combination. Only card contents change as the user switches.
- A card is assembled from one or more **parts**. A part is a result (from either query tool) plus
  the coordinates it sits at.
- A part's **coordinates** are the dimensions its query varied over, plus any assigned by `at`.
  A dimension a card never mentions is one it does not vary over.

Resolution at a selected combination:

```python
key = ";".join(f"{d}={point[d]}" for d in sorted(part.dims))
part.variants[key]
```

A plain `run_query` result has no coordinates, so its key is empty and it shows the same rows
everywhere. That is the same code path, not a special case.

## Tool 1: `run_query_for_each_combination`

```python
class QueryDimension(BaseModel):
    id: str                 # matches the dimension id used in show_artifacts
    choices: list[str]      # choice ids; the template must branch on them

async def run_query_for_each_combination(
    db_alias: str,
    dimensions: list[QueryDimension],
    query_template: str,
) -> str                    # "QS3 — 8 combinations, 6 executed"
```

Renders `query_template` once per combination of `dimensions`, runs them under a concurrency bound,
and registers the whole set under one `QS<n>` id. Each dimension id is bound to the chosen choice id
in the Jinja context, so the SQL owns the SQL logic:

```sql
SELECT customer_name AS customer,
  {% if ranking == "net_revenue" %} SUM(net_revenue_usd) AS net_revenue_usd
  {% elif ranking == "order_count" %} COUNT(*) AS orders
  {% endif %}
FROM orders
WHERE status = 'completed'
  AND {% if period == "compl_qtr" %} order_date >= DATE '2026-04-01' AND order_date < DATE '2026-07-01'
      {% elif period == "last_90_days" %} order_date > CURRENT_DATE - INTERVAL 90 DAY
      {% endif %}
GROUP BY customer_name ORDER BY 2 DESC LIMIT 5
```

One template per call. Templates that vary over different dimension sets cannot share a call, and
that is what lets each card run over only the dimensions it depends on.

Deliberately absent:

- **No positioning argument.** Where a result sits in a space is declared in `show_artifacts`, so a
  batch run before a dimension existed can still be placed once it does.
- **No label.** Cards are labelled where cards are declared.
- **No `parameters`.** Jinja already substitutes values; `:param` binding on top would be a second
  mechanism for one job.
- **No `refresh`.** DDL across interpretation variants is not a coherent operation.

### Validation, before anything executes

1. The template's Jinja variables equal the declared dimension ids, both directions, under
   `StrictUndefined`.
2. Dimension ids unique; choice ids unique within a dimension. Non-empty ids and a non-empty
   choice list are expressed as schema constraints (`min_length`), so a violation is a retryable
   schema error rather than a tool error string.
3. A cap on total combinations (50) — rejected, not truncated.
4. After rendering, before running: for each dimension, if changing it never changes the rendered
   SQL, error naming that dimension.

Check 4 earns its place over check 1 alone: a template can reference `{{ ranking }}` in a comment or
a no-op position, pass the variable check, and produce a card the user can toggle with no effect.
Comparing renders catches that, and yields the dedup map for free — identical renders execute once
and register under several keys.

`run_subagent_for_each_row` already implements this pattern and is the reference:
`_JINJA_ENV` with `StrictUndefined` (line 65), `find_undeclared_variables` (line 471), and the
convention of naming the language in the argument description rather than the argument name
(`task_instruction`, line 313).

### Return value

One combination in full so the agent can sanity-check the query, then one row count per remaining
combination so it can see they ran — an empty variant means a card that renders empty for that
reading, which is either real or a bug in that branch. The tool goes in the message-store allowlist
so wide results spill instead of flooding context.

The exact layout is pinned by `test_output_format` in `tests/test_run_query_for_each_combination.py`;
that assertion is the spec, not a copy of it here.

On failure nothing is registered, and the return names the first failing combination with its error.
Partial registration would push the hole downstream; a batch is complete or absent.

## Tool 2: `show_artifacts`

```python
class At(BaseModel):
    dimension: str
    choices: list[str]

class Part(BaseModel):
    id: str                                   # Q<n> or QS<n>
    at: list[At] = []                         # extra coordinates this result sits at

class Artifact(BaseModel):
    label: str                                # fixed across all combinations
    id: str | None = None                     # exactly one of id / parts
    parts: list[Part] | None = None
    not_applicable_reason: str | None = None

class Choice(BaseModel):
    id: str
    label: str

class Dimension(BaseModel):
    id: str
    label: str                                # short phrase, not a question
    choices: list[Choice]                     # best reading first; >= 2 required

async def show_artifacts(
    artifacts: list[Artifact],                # first card is shown first
    dimensions: list[Dimension] = [],         # empty = no chooser
) -> str
```

### Part semantics

Which cells of a card a part covers, per dimension:

| the part's relation to a dimension | cells it covers |
|---|---|
| its query varied over it | exactly the choices that query ran |
| named in its `at` | the listed choices |
| neither | all of them (wildcard) |

The card's dimensions are the union of its parts' coordinates.

### Rules

1. A part's `at` must not name a dimension its query already varied over.
2. Every choice a part touches — from its query's run or from `at` — must be declared for that
   dimension in `dimensions`.
3. Parts of one card must be pairwise disjoint; no cell claimed twice.
4. The union of a card's parts must cover its full cell space. If it does not,
   `not_applicable_reason` is required and the remainder becomes a declared empty region rendered as
   a placeholder. If it does, the reason must be absent.
5. All parts of one card must be the same artifact kind, so the card's view tabs keep their shape as
   the selection moves.
6. Every dimension must affect at least one card's content or its applicability.
7. `dimensions` is either empty or holds dimensions with two or more choices each. A chooser with
   nothing to choose is an error pointing back at the plain form.

Rule 2 deliberately does not require an individual query to cover all of a dimension's choices —
siblings fill in, and rule 4 is what checks completeness. That is what makes incremental extension
possible without re-running the original batch.

### Examples

Space: `ranking` (net_revenue, order_count) × `returns` (excl, incl) × `period` (compl_qtr, qtd) —
8 combinations.

```python
# Ordinary answer, no interpretations.
show_artifacts(artifacts=[{"id": "Q3", "label": "player count"}])

# Varies over everything; two batches because `returns` changes the SQL shape.
{"label": "Top customers",
 "parts": [{"id": "QS1", "at": [{"dimension": "returns", "choices": ["excl"]}]},
           {"id": "QS2", "at": [{"dimension": "returns", "choices": ["incl"]}]}]}

# Does not vary over `returns` — nothing to write, it wildcards.
{"label": "Region summary", "parts": [{"id": "QS3"}]}

# Plain query result: one payload at all 8 combinations.
{"id": "Q5", "label": "Data coverage"}

# Inapplicable on part of its space.
{"label": "Quarter-over-quarter change",
 "parts": [{"id": "QS4", "at": [{"dimension": "period", "choices": ["compl_qtr"]}]}],
 "not_applicable_reason": "a quarter-over-quarter comparison needs a completed quarter"}

# A 3-choice dimension where two choices share one SQL shape.
{"label": "Revenue trend",
 "parts": [{"id": "QS7", "at": [{"dimension": "period", "choices": ["compl_qtr", "l90d"]}]},
           {"id": "QS8", "at": [{"dimension": "period", "choices": ["qtd"]}]}]}

# A choice added to an existing dimension in a later turn — no `at` needed.
{"label": "Region summary",
 "parts": [{"id": "QS3"},      # ran over ranking (net_revenue, order_count) × period
           {"id": "QS9"}]}     # ran over ranking (gross_revenue) × period
```

### The not-applicable placeholder

The panel renders which choices a card does not apply to from its coordinates and the panel's own
display labels; the agent supplies only the reason. This keeps the actionable half — the choice to
change, in the words the user is reading — out of agent prose, where it could drift from the
coordinates and tell the user something false.

```
Not applicable for Time period: Current quarter to date
A quarter-over-quarter comparison needs a completed quarter to compare against.
```

`not_applicable_reason` is documented as completing "Not applicable because …", one line, and
explicitly not restating which choices it applies to.

### Coverage errors

All arrive before any prose is written, and each names the offending id:

```
error: "Top customers" covers 4 of 8 combinations — missing returns=incl.
       Run them, or set not_applicable_reason.
error: QS2 was run over 'period' choices ['compl_qtr'] but 'period' declares ['compl_qtr', 'qtd'].
error: dimension 'currency' affects no card's content or applicability.
error: a panel needs at least one dimension with two or more choices — pass artifacts only.
```

### Echoing the alignment back

The return should list what was aligned, with the first line of each part's SQL:

```
2 cards, 3 dimensions, 8 combinations
  Top customers
    returns=excl ← QS1  SELECT customer_name, SUM(net_revenue_usd) … FROM orders …
    returns=incl ← QS2  SELECT customer_name, SUM(net_revenue_usd) … FROM orders LEFT JOIN returns …
  Region summary — varies over ranking, period
```

Mispositioning a part is the one error no check can catch: every cell is filled, nothing is missing,
and the user sees real but wrong data. Echoing makes it visible at the moment it is made, which
matters most when the part being positioned ran several turns earlier.

## Replacing the citation block

`show_artifacts` is the only way to declare a turn's cards; the `<artifacts>` block is removed.

The block is a text protocol whose rules are enforced by prompt discipline — start every answer with
it even when empty, ids valid only inside it, label mandatory and never the id — and it fails late,
while parsing the final message, after the answer is written. A tool call gets schema validation and
a retryable error before any prose exists. What leaves the system prompt is the syntax half of the
citing section; what stays is the judgment half, which no schema expresses: cite only what is most
relevant, most important first, minimize overlap, never repeat query text in prose.

Cost accepted: one extra tool call on every turn that produces an answer. The block also serves as
the answer/narration boundary today, so the call is required even when there is nothing to show —
see [Implementation](#implementation).

## Naming

- `run_query_for_each_combination` — mirrors `run_subagent_for_each_row`, the repo's existing
  template-over-a-binding-set fan-out. "Interpretation" would overclaim: a call usually covers a
  subset of the dimensions, so its renders are partial readings.
- `query_template` — keeps template-ness in the name, which is the one thing distinguishing it from
  `run_query`'s literal `query`; the language goes in the description, as `task_instruction` does.
- `show_artifacts` — a plain verb for the act. It returns no id, so `create_*` would imply an object
  that does not exist, and "panel" in this UI means the chooser, not the card area.
- No `PANEL<n>` id, and no `default_selection`: position encodes priority in both lists — first card
  shown first, first choice applied.

## Terminology

Standard vocabulary for what this is, if it helps future readers: the dimension space is an OLAP
**cube**; a result over a subset of its dimensions is a **cuboid** (all dimensions = base cuboid,
none = apex cuboid); resolving a point against a lower-arity result is **broadcasting** by named
dimension, as in xarray, or a natural join on the shared dimension keys. A result's dimension set is
its **grain** in dimensional-modeling terms.

## Rejected alternatives

- **Flags on `run_query`** (`interpretation_space` / `artifact_role` / `selections`). It taxes the
  most-called tool's schema and description on every ordinary query, forks its return contract from
  one record to many, and makes `query` sometimes-a-template. `registry_run_query.py:87-158` already
  hand-writes four docstring variants for `enable_params × enable_refresh`; this would multiply that
  again.
- **Replacing `run_query` with the combination tool.** It does not cover `refresh`, which chat
  enables (`chat/agent.py:291`) for DDL on `workspace`, and `RunQueryTool` serves ten research
  agents, three modulehub modules and two toolhub tools that have no interpretation concept. It also
  puts Jinja rendering on every ordinary query, where a doubled brace in a JSON literal becomes a
  baffling failure.
- **One atomic tool** that declares the space, runs everything and builds the panel. It forces every
  query to full arity — no per-card dimension subsets — and puts validation errors after all the
  query cost has been paid.
- **A `{combination → record id}` mapping table** written by the agent. More general, but 32 entries
  for three dimensions and four cards, it re-admits partial coverage, and it drops the guarantee that
  a card's variants differ only where the interpretation differs.
- **`applies_to` on the query tool** (positioning at run time). Cannot express a dimension that did
  not exist when the batch ran, which is the normal conversational case.
- **`applicable_to` instead of `not_applicable_reason`.** The positive region is already declared by
  `parts`/`at`, so an inclusion list restates it unverifiably, and reasons belong on exclusions.
- **Per-card `role` identifiers.** Only needed if the card set changes per combination. It does not.

## Implementation

### Layers

Both tools live in `toolhub`; `chat` continues to define no tools of its own.

`run_query_for_each_combination` has exactly `RegistryRunQueryTool`'s dependencies — `DBRegistry`
from `core.db_connector`, and `QueryHistory`. `show_artifacts` needs no chat imports either: it
validates against `QueryHistory` and stores a bundle of artifact ids, which `chat` hydrates into
display payloads. That is the split toolhub already uses — `ChartArtifact` (toolhub: spec + record
id) becomes `ChatResultChart` (chat: spec + rows + query).

`research/tools/` is not a precedent for a `chat/tools/`. Those tools depend upward, on
`research.types` (`ask_user`) or on the research task contract (`finish`); neither applies here.

Type placement:

- `QueryDimension` — `toolhub/run_query_for_each_combination.py`.
- `Dimension`, `Choice`, `At`, `Part`, `Artifact` — `toolhub/show_artifacts.py`, as pydantic models
  since the tool schema needs them. `chat/result.py` imports `Dimension`/`Choice` directly rather
  than mirroring: they carry no DataFrames, so there is nothing to hydrate.
- `QueryFamily` — `toolhub/query_history.py`, alongside the other artifact dataclasses.
- `ChatResultCard` — `chat/result.py`, the only genuinely chat-side new type, because it holds
  resolved payloads.

The declared bundle lives on the `ShowArtifactsTool` instance rather than in `QueryHistory`: it is
turn-scoped and not id-addressed. Same shape as `RunQueryTool._last_pred_query`.

### The citation block is also the answer boundary

`_TextStreamRouter` (`chat/agent.py:858`) uses `<artifacts>` for a second job: classifying a text run
as the final answer versus mid-turn narration. A run opening with the tag is the answer — held back
until `</artifacts>`, then streamed; anything else streams live as narration. pydantic-ai cannot
supply this signal earlier, since a response is only known to be terminal once it completes without
tool calls, which is too late to stream against.

`show_artifacts` returning replaces it: text before the call is narration, text after it is the
answer, and the router stops buffering entirely. This is why the call is required on every turn that
produces an answer, with `artifacts=[]` when there is nothing to show — the same discipline the
prompt enforces today for the empty block. If the model skips the call, fall back to treating the
trailing text run as the answer, buffered.

### Storage

As implemented in `toolhub/query_history.py`:

```python
@dataclass
class QueryFamily:
    family_id: str                             # QS<n>, own counter
    db_alias: str
    connector_type: Literal["sql", "property_graph"]
    dimensions: dict[str, list[str]]           # dim id -> choice ids, declared order
    query_template: str
    record_ids_by_selection: dict[str, str]    # selection key -> variant record id
```

Variants are ordinary `QueryRecord`s, so spill, hydrate and eviction work unchanged. Their ids must
avoid dots — `QS3_v0`, not `QS3.v0` — because `_persist` passes the record id straight through as a
DuckDB table name. Selections whose rendered query is identical share one variant. Variant ids are
not `Q<n>`, so `render_chart(Q17)` can never land on one.

`QueryHistory(max_in_memory=5)` is smaller than a single family. An 8-combination family evicts
everything else plus three of its own variants on creation, and `_build_chat_result` then hydrates
all eight to build the payload. Correct but thrashy — either raise the default or hydrate a family in
one pass. Unresolved, and it gets worse at the 50-combination cap.

### `ChatResult`

Today an artifact carries its own label and payload. With variants the label is card-level and fixed
while the payload moves, so the card becomes a wrapper:

```python
class ChatResultCard(BaseModel):
    label: str
    dims: list[str]                              # dimensions this card varies over
    variants: dict[str, ChatResultArtifact]      # selection key -> payload
    not_applicable_reason: str | None = None

class ChatResult(BaseModel):
    text: str
    artifacts: list[ChatResultCard]
    dimensions: list[Dimension] = []             # empty = no chooser
    usage: Usage | None = None
```

A plain card is `dims=[]`, `variants={"": ChatResultRecord(...)}` — one shape, no panel branch.
`primary_artifact_index` goes away; the first card is primary, matching the rule that position
encodes priority.

The cost lands entirely in `app`: every `artifact.df` / `artifact.label` access becomes
`card.at(sel).df`. A `card.at(selection)` helper keeps most call sites one token longer, but
`app/pane/cards.py`, `app/display.py` and `app/dump.py` all need touching. Since the pane is
deferred, only the TUI path must be correct in v1 — but the type change hits every consumer at once,
so the rest at least need to compile and render the first combination.

### Handoff

`_build_chat_result` reads the tool's bundle instead of parsing text, mirroring
`RunQueryTool.last_pred_query()` (`run_query.py:302`). Reset the bundle at the start of each
`run_stream` so a previous turn's cannot leak into a turn where the model skipped the call; on repeat
calls within one turn, the last wins.

### Deleted

`_ARTIFACT_REF_RE`, `_ARTIFACTS_OPEN` / `_ARTIFACTS_CLOSE`, `_parse_refs`, `_extract_result_refs`,
the block logic inside `_TextStreamRouter`, and the syntax half of the citing section in
`system_prompt.md`. `_artifacts_from_refs` becomes `_cards_from_bundle` and keeps most of its body —
per-kind resolution of record/chart/map/graph payloads is unchanged, just called per variant.

### Shared code

`RegistryRunQueryTool._get_tool` (`registry_run_query.py:69`) caches a `RunQueryTool` per alias and
rebuilds it when the alias is re-bound. The combination tool needs the same execution and formatting
path but registers a family instead of a record, so lift that resolution into a module-level helper
both call rather than copying the cache.

### Order

1. `QueryFamily` and `run_query_for_each_combination` — self-contained in toolhub, testable without
   touching chat.
2. `ChatResultCard` and the `app` call sites — mechanical, and it has to land before anything
   produces cards.
3. `show_artifacts`, the block removal and the prompt edit — one step, because the router change and
   the prompt change must be simultaneous.

## Open questions

1. **When the agent should offer a panel.** The bar needs writing: readings that change the answer
   materially, more than one genuinely plausible, cheap to compute. Below that bar, a stated
   assumption in prose. Related: panel versus a clarifying question — lean is panel when the choice
   is recognizable on sight, question when it needs a paragraph to explain.
2. **The prose contract.** The answer text is written under the first reading and goes stale on
   switch. Lean is a rule that prose accompanying a panel does not assert selection-dependent
   numbers. The alternative — a per-combination summary line — drags combination-sized authored
   content back into the payload.
3. **Selection state and panel lifecycle.** Does the user's current selection reach the agent (the
   `note_event` channel is the natural fit)? Without it, follow-up panels keep opening on the
   original guess. And does a refining turn emit a new panel above the old one, or update in place?
   Accumulating stale choosers in the transcript is the failure mode to avoid.
4. **Eager versus default-first execution.** Running all combinations before answering makes the
   user wait on queries they may never open. Running the first reading, answering, then filling the
   rest in the background is faster but changes the tool's return contract from "all done" to "one
   done, rest pending", and needs disabled choices in the UI meanwhile.
5. **Schema shape for dimension maps.** `dimensions` and `at` are specified above as lists of
   objects, following `LLMParameter` (`run_query.py:58`), because strict function schemas do not
   handle open-ended object keys. If strict schemas are not in use, `dict[str, list[str]]` is
   considerably lighter for the agent to write. Decide once, apply to both.
6. **ARCS evaluability.** Worth shaping `Dimension`/`Choice` to mirror `GoldAmbiguityPointFinite`
   (`research/types.py:144`) so predicted dimensions can be scored against gold ambiguity points and
   variant queries against gold queries per combination — that makes the feature measurable rather
   than demo-only. `research` cannot import `toolhub`'s tool module directly, so this would mean
   comparing recorded output, or hoisting the shape to `core`. The gold *infinite* kind (open-ended
   parameter plus operator) has no place in a choice-list model and is out of scope.
7. **Hydrate latency on switch.** An old family's rows come back from workspace DuckDB when the user
   switches interpretation. Needs confirming it stays fast enough to feel instant, which is the point
   of the feature — see [Storage](#storage) for the eviction arithmetic.

## Deferred

**Charts, maps and graphs over interpretations.** The intended shape is that `render_chart(QS1,
spec)` yields a chart set carrying QS1's dimensions — the spec is selection-invariant, only the data
moves — so the interpretation dimension propagates through the existing artifact pipeline rather than
being special-cased. Undesigned: whether the spec is validated against every variant's columns (they
differ, `net_revenue_usd` versus `orders`), what it returns, and how a map with several source
records behaves when only some vary. v1 panels hold table cards only; `render_chart` and friends keep
taking a single `Q<n>`.

**Browser output pane.** v1 is TUI-only. Open when it is taken up: whether variant data ships in the
turn payload or the pane server serves it per card (up to ~24 DataFrames in one `Finished` event
otherwise), how the card tab strip hosts the chooser, and whether `app/dump.py` exports a panel as
interactive or frozen at the current selection.
