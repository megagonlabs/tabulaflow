# tabulaflow

Minimalist Text-to-Query toolkit for NL2SQL research. Supports BIRD-SQL, Spider 2.0, Beaver, ARCS, and AMBROSIA datasets.

## Package Manager

Use `uv` for all Python operations:
- Run scripts: `uv run <script.py>` (python interpreter at `.venv/bin/python`)
- Add dependencies: `uv add <package>`
- Sync dependencies: `make sync` (runs `uv sync --all-extras --all-packages --group dev`)

## Common Commands

```bash
make test          # pytest with all caching disabled
make format        # ruff format + ruff check --fix
make lint          # ruff check
make mypy          # mypy tabulaflow/ tests/
make sync          # sync uv dependencies
```

Key experiment targets (see Makefile for full list):
```bash
make test-bird-agent           # bird-sql with sql_agent
make test-arcs-structured      # arcs with ambig_structured_sql_agent
make test-spider2-agent        # spider2-snow with sql_agent
make test-spider2-dbt-agent    # spider2-dbt with dbt_agent
make test-simple               # bird-sql, spider2-snow, beaver with simple_zero_shot
```

Pipeline scripts (used directly):
```bash
uv run tabulaflow/research/pipelines/run_agent.py --agent <agent> --dataset <dataset> --debug
uv run tabulaflow/research/pipelines/populate_exec_results.py --debug
uv run tabulaflow/research/pipelines/evaluate.py --debug
uv run tabulaflow/research/pipelines/analyze_errors.py --debug
```

## Project Structure

The package is organized into dependency layers, enforced by `import-linter`
(`make lint-arch`): **`core < data < output < agents < app`**. `research`
is a separate leaf consumer of the platform layers; it may import
`core`/`data`/`output`/`agents`, but neither `app` nor platform layers may
import `research`, and `research` must not import `app`.

```
tabulaflow/
├── core/            # stable schema/result primitives, serialization, and class registry
├── data/            # connectors, live DB registry, schema services, and external-data loaders
├── output/          # output specs, result storage/resolution, formatting, and schema renderers
├── agents/          # ChatSession, LLM/runtime infrastructure, extraction, summarization, and tools
│   ├── chat/        #   reusable stateful chat runtime and semantic event stream
│   ├── extraction/  #   reusable structured document extraction
│   └── tools/       #   model-facing tools grouped by implementation domain
├── research/        # NL2SQL research — a leaf consumer of the platform layers
│   ├── agents/  benchmarks/  metrics/  pipelines/  preprocessing/
│   ├── tools/       #   research-only tools (ask_user, run_dbt, finish, get_schema, ...)
│   └── types.py reporting.py execution.py query_analysis.py ambiguity.py
└── app/             # end-user TUI and browser output pane
tests/               # pytest tests
scripts/             # utility scripts
output/              # experiment results
cache/               # schema and preprocessing cache
```

Stable core primitives are re-exported from `tabulaflow.core`; use explicit
submodules for layer-specific APIs such as `tabulaflow.agents.trace` and
`tabulaflow.output.specs`.

## Environment Variables

Managed via `direnv` (`.envrc` file, not committed):
- `OPENAI_API_KEY`
- `SF_USER`, `SF_PASSWORD`, `SF_ACCOUNT` — Snowflake (Spider 2.0)
- `TABULAFLOW_CACHE_DIR` — shared cache root
- `TABULAFLOW_SCHEMA_CACHE_MODE`, `TABULAFLOW_QUERY_CACHE_MODE`, `TABULAFLOW_PREPROCESSING_CACHE_MODE` — cache policies
- `TABULAFLOW_MAX_RESULT_ROWS`, `TABULAFLOW_QUERY_TIMEOUT_SECONDS`, `TABULAFLOW_MAX_QUERY_CONCURRENCY` — connector limits
- `TABULAFLOW_MAX_LLM_CONCURRENCY`, `TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE` — LLM rate limiting
- `TABULAFLOW_MAX_EMBEDDING_CONCURRENCY`, `TABULAFLOW_MAX_EMBEDDING_REQUESTS_PER_MINUTE` — embedding rate limiting
- `TABULAFLOW_BROWSER_MAX_TABS`, `TABULAFLOW_BROWSER_HEADLESS` — browser runtime
- `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_API_KEY` — Phoenix tracing (optional)
- `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` — Langfuse tracing (optional)

## LLM Identifiers

- OpenAI: `openai-responses:gpt-5-mini`, `openai-responses:gpt-5`
- Anthropic: `anthropic:claude-sonnet-4-5-20250929`
- Google: `google-vertex:gemini-2.0-flash`, `google-vertex:gemini-2.5-flash`
- Fireworks: `fireworks:accounts/fireworks/models/<model-name>`
- Together: `together:<org>/<model>`

## Key Datasets

| Key | Description |
|-----|-------------|
| `bird-sql` | BIRD-SQL (splits: `dev_20240627`, `dev_20251106`, `a199`, `train`) |
| `spider2-snow` | Spider 2.0 Snowflake |
| `beaver` | Beaver MySQL |
| `arcs` | ARCS ambiguous NL2SQL |
| `ambrosia-s` | AMBROSIA structured |
| `cypherbench` | CypherBench text-to-Cypher (Neo4j; splits: `test`, `train`; data: clone HF `megagonlabs/cypherbench` to `data/cypherbench`) |

## Tmux Sessions

Run long experiments in tmux session `tabulaflow`:
```bash
tmux send-keys -t tabulaflow "<command>" Enter
```

For experiment scripts in `exp/`, run them in tmux session `tabulaflow`:
```bash
bash exp/123_xxx.sh &> log/123.out &
```

If (and only if) resuming an interrupted experiment, append to the log file:
```bash
bash exp/123_xxx.sh &>> log/123.out &
```

## Design Language (HTML rendering in `tabulaflow/app/render/`, shown in the output pane)

Dark-app feel, mint accent, modern data-app references (Linear, Stripe, GitHub).

- **Engine**: Tabulator (`tabulator_midnight.min.css` + overrides) for tables, Vega for charts. Keep custom CSS thin — let the bundled theme do the work.
- **Palette**:
  - Page bg: `#0f1117` (deepest)
  - Card / panel surface: `#1a212c` (lifted clearly off the page so the borderless panel reads as a distinct surface)
  - Even-row stripe: `#232b38` (lift above the panel)
  - Row hover: `#2c3441`
  - Border: `#21262d`
  - Mint accent: `#3eb489` (headers, focus highlights, active pane tab)
  - Text primary `#e4e4e7`; dim / row-numbers `#6a737d`
- **Layout**:
  - Views render **bare** (no banner/page chrome), sized to their content, so they embed cleanly in the output pane (`app/pane.py`) — which frames each cited result as a card with a `Chart | Data | Query` tab strip and caps the stack width. The `tabulaflow` banner is reserved for standalone share exports.
  - When developing the output pane, preview fast fixtures with `uv run scripts/preview_output_pane.py --port 61211`; add `--full` only for stress fixtures.
  - Table layout `fitColumns`: columns stretch to panel width with renderer-assigned `minWidth` values.
  - Height: only force a pixel height when row count > 100 (so virtual scroll engages); otherwise free-flow at content height.
- **No double boxes**: kill midnight's inner `.tabulator` border, the only frame is the outer card.
- **Row separators**: none on body cells; vertical 1px dividers on header cells only.

## Guidelines

- Think from first principles.
- Think out-of-the-box. Find the cleanest and most elegant solution.
- Fail fast.
- Fix the root cause, don't just mask the symptom.
- Prioritize long term cleanliness and maintainability.
- When a change moves responsibility between modules, move related helpers to the new owning module in the same change.
- Take the principled approach, not the one based on heuristics.
- Before writing code, always assess whether the idea aligns with common practice and if not, stop and provide such feedback to the user.
- Use Google style for all Python docstrings.
- Keep code clean, minimal and intuitive. Do not over-engineer or over-abstract.
- Do not write comments if the code is self-explanatory. Only write comments for complicated or tricky logic.
- For large changes with multiple design decisions or multiple alternative implementations, discuss with me first.
- Be honest when what I say has flaws or does not make sense.
- When writing agent-facing tool description, just describe the tool's functionality and use cases, don't lecture the agent on how or when to use it or mention verbosely commonsense knowledge.
- The repo has not been published yet, so always do a clean break and remove unused code, refactor to better architecture if necessary. Optimize for long-term cleanliness over compatibility.
- When the current architecture or abstraction is not optimal for the new feature, stop and discuss with me first on a refactoring plan. You can suggest removal of current features if that can lead to a cleaner architecture.
- Do not commit code unless I explicitly ask you to.
- For UI changes, ask me to verify it visually for you (without taking screenshot yourself) to save time.

## Toolhub Development Principles

- Keep `__call__` as the LLM-facing adapter; put reusable logic in `execute(...)`.
- Reusable `execute(...)` methods raise expected validation/runtime errors;
  `__call__` catches them and returns the model-facing `(error: ...)` string.
- Use structured result dataclasses only when fields have real consumers; otherwise return the output string.
- Do not bridge awaited calls with shared `last_*` state; return per-call data from `execute(...)`.
- Registry tools resolve aliases, call the underlying `execute(...)`, and convert results to `ToolReturn` metadata.
- Model-facing errors should be `(error: ...)` strings, unless immediately caught and converted.
- Reserve/increment user-visible ids before awaits that can interleave.
- Prefer small tool-specific dataclasses; do not add broad result hierarchies.
- Rebuild cached per-alias tools when an alias is rebound.
- Keep metrics in the shared execution path.
- In tests, assert `ToolReturn.return_value` is a string before searching it.
