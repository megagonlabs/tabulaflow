# mintq

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
make mypy          # mypy mintq/ tests/
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
uv run mintq/pipelines/run_agent.py --agent <agent> --dataset <dataset> --debug
uv run mintq/pipelines/populate_exec_results.py --debug
uv run mintq/pipelines/evaluate.py --debug
uv run mintq/pipelines/analyze_errors.py --debug
```

## Project Structure

```
mintq/
├── agenthub/        # text-to-query agents (sql_agent, ambig_*_sql_agent, etc.)
├── toolhub/         # agent tools (run_query, get_schema, search_keywords, etc.)
├── datahub/         # dataset loaders (bird_sql, spider2, beaver, arcs, ambrosia)
├── db_connector/    # database connectors (sql_conn, etc.)
├── metrics/         # evaluation metrics (bird_sql_ex, simple_ex, etc.)
├── pipelines/       # run_agent.py, populate_exec_results.py, evaluate.py
├── preprocessors/   # schema preprocessing and caching
├── formatters/      # schema formatters (sql_basic, sql_ddl)
├── schema.py        # core data structures
├── config.py        # configuration
└── registry.py      # agent/dataset/metric registry
tests/               # pytest tests
scripts/             # utility scripts
output/              # experiment results
cache/               # schema and preprocessing cache
```

## Environment Variables

Managed via `direnv` (`.envrc` file, not committed):
- `OPENAI_API_KEY`
- `SF_USER`, `SF_PASSWORD`, `SF_ACCOUNT` — Snowflake (Spider 2.0)
- `MINTQ_SCHEMA_CACHE_ENABLED`, `MINTQ_SCHEMA_CACHE_REQUIRED` — schema cache control
- `MINTQ_PREPROCESSOR_CACHE_ENABLED`, `MINTQ_PREPROCESSOR_CACHE_REQUIRED` — preprocessor cache control
- `MINTQ_MAX_LLM_CONCURRENCY`, `MINTQ_MAX_LLM_REQUESTS_PER_MINUTE` — rate limiting
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

Run long experiments in tmux session `mintq`:
```bash
tmux send-keys -t mintq "<command>" Enter
```

For experiment scripts in `exp/`, run them in tmux session `mintq`:
```bash
bash exp/123_xxx.sh &> log/123.out &
```

If (and only if) resuming an interrupted experiment, append to the log file:
```bash
bash exp/123_xxx.sh &>> log/123.out &
```

## Guidelines

- Think from first principles.
- Fail fast.
- Fix the root cause, don't just mask the symptom.
- Before writing code, always assess whether the idea aligns with common practice and if not, stop and provide such feedback to the user.
- Use Google style for all Python docstrings.