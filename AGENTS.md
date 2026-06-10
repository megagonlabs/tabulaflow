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
(`make lint-arch`): **`core < datasources < toolhub < modulehub < {chat | research} < app`**.
`chat` and `research` are siblings and must not import each other.

```
tabulaflow/
├── core/            # deterministic foundation — depends on nothing else in tabulaflow
│   ├── types.py     #   core data structures (schema, queries, ExecResult, Usage, Trajectory)
│   ├── dataframe.py #   Arrow/DataFrame (de)serialization
│   ├── er_diagram.py schema_compressor.py   # ERD data types + deterministic schema compression
│   ├── config.py registry.py utils.py llm.py
│   └── db_connector/  formatters/
├── datasources/     # acquire external data → a connector (files, HuggingFace, …) — depends on core
├── toolhub/         # agent tools — depends on core
│                    #   BaseTool, run_query, registry_* (wrap the plain tools),
│                    #   web_browser, render_chart, run_subagent, message_store, ...
├── modulehub/       # LLM-powered schema-analysis modules — depends on toolhub, core
│                    #   db_summarizer, er_diagram (synth), fk_predictor, column_profiler,
│                    #   text_summarizer, schema_preprocessor + the caching base
├── chat/            # the interactive tabulaflow agent (ChatAgent.run_stream → ChatEvent stream, ChatResult)
├── research/        # NL2SQL research — sibling of chat, never imports it
│   ├── agenthub/  benchmarks/  metrics/  pipelines/   # benchmarks = eval datasets (tasks+gold+metrics)
│   ├── tools/       #   research-only tools (ask_user, run_dbt, finish, get_schema, ...)
│   └── types.py utils.py question_embedder.py   # NL2QTask/NL2QDataset/GoldQuery, dataset-level analysis
└── app/             # end-user TUI — tui, dump (HTML export), widgets, main, assets
tests/               # pytest tests
scripts/             # utility scripts
output/              # experiment results
cache/               # schema and preprocessing cache
```

Public types are re-exported from each layer's `__init__` (e.g.
`from tabulaflow.core import SQLSchema, ExecResult, Usage`); prefer those over
deep module paths.

## Environment Variables

Managed via `direnv` (`.envrc` file, not committed):
- `OPENAI_API_KEY`
- `SF_USER`, `SF_PASSWORD`, `SF_ACCOUNT` — Snowflake (Spider 2.0)
- `TABULAFLOW_SCHEMA_CACHE_ENABLED`, `TABULAFLOW_SCHEMA_CACHE_REQUIRED` — schema cache control
- `TABULAFLOW_PREPROCESSOR_CACHE_ENABLED`, `TABULAFLOW_PREPROCESSOR_CACHE_REQUIRED` — preprocessor cache control
- `TABULAFLOW_MAX_LLM_CONCURRENCY`, `TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE` — rate limiting
- `OTEL_EXPORTER_OTLP_ENDPOINT`, `LOGFIRE_TOKEN` — tracing (optional)

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

## Design Language (HTML table dumps in `tabulaflow/app/dump.py`)

Dark-app feel, mint accent, modern data-app references (Linear, Stripe, GitHub).

- **Engine**: Tabulator (`tabulator_midnight.min.css` + overrides). Keep custom CSS thin — let the bundled theme do the work.
- **Palette**:
  - Page bg: `#0f1117` (deepest)
  - Card / table surface: `#131720`
  - Even-row stripe: `#1a1f2a` (subtle ~4% lift)
  - Row hover: `#1f2532`
  - Border: `#21262d`
  - Mint accent: `#3eb489` (headers, banner logo, focus highlights)
  - Text primary `#e4e4e7`; dim / row-numbers `#6a737d`
- **Layout**:
  - Sticky top banner with `tabulaflow` mint-mono logo (left) and GitHub repo link (right).
  - Table sits in a bordered card that `min-height`s the viewport — short tables still anchor a panel, no floating-in-void.
  - Table layout `fitDataFill`: columns are content-sized, rows fill container width (blank space on the right is intentional).
  - Width: card fills page. Height: only force a pixel height when row count > 100 (so virtual scroll engages); otherwise free-flow.
- **No double boxes**: kill midnight's inner `.tabulator` border, the only frame is the outer card.
- **Row separators**: none on body cells; vertical 1px dividers on header cells only.

## Guidelines

- Think from first principles.
- Fail fast.
- Fix the root cause, don't just mask the symptom.
- Prioritize long term cleanliness and maintainability.
- Before writing code, always assess whether the idea aligns with common practice and if not, stop and provide such feedback to the user.
- Use Google style for all Python docstrings.
- This is a research library, do not over-abstract.
- Do not write comments if the code is self-explanatory. Only write comments for complicated or tricky logic.
- For large changes with multiple design decisions or multiple alternative implementations, discuss with me first.
