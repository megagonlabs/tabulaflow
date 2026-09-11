# Configuration

The default settings are suitable for local use. Configure TabulaFlow when you
need to select a model, control resource limits, enable caching, or expose the
browser output pane through another host.

## Model selection

TabulaFlow supports OpenAI and Anthropic presets in the Data Agent. Provide the
credential for the provider you use:

```bash
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
```

Only one key is required. When no preference has been saved, startup selects a
balanced preset from the available credentials, checking OpenAI first and then
Anthropic.

Run `/config` inside the app to inspect the available presets and save a
selection. Choosing **Off** disables conversational analysis while leaving data
connection and browsing available.

Override the saved selection for one launch with `--llm-preset`:

```bash
tabulaflow --llm-preset "OpenAI budget"
tabulaflow --llm-preset off
```

The interactive selection is stored in `~/.tabulaflow/app_config.json`. API
keys are read from the environment and are never written to that file.

## In-app commands

| Command | Purpose |
| --- | --- |
| `/help` | Show available commands |
| `/config` | Open model configuration |
| `/connect <source...> [--alias name]` | Connect a data source |
| `/disconnect [alias]` | Disconnect a user source |
| `/clear` | Start a new conversation in the current session |
| `/exit` | Close the app |

The input offers command completion as you type. After `/connect`, it also
completes local file paths.

## Command-line options

Launch options apply only to the current process:

| Option | Purpose |
| --- | --- |
| `--llm-preset`, `-p` | Override the saved model preset or use `off` |
| `--llm-service-tier` | Use `default` or `priority` request service; priority may cost more |
| `--enable-schema-cache` | Persist database schemas for faster repeated connections |
| `--log-level` | Set file logging to `debug`, `info`, `warning`, or `error` |
| `--output-pane-port` | Require a specific browser-pane port instead of the first free port in `61111–61130` |
| `--output-pane-host` | Change the bind host from `127.0.0.1` |
| `--output-pane-public-url` | Set the browser-facing base URL when the bind address is not directly reachable |

Run `tabulaflow --help` for the current command syntax.

!!! warning "Exposing the output pane"
    Keep the default loopback host unless remote access is intentional. Output
    pages can contain query results and other session data. The session token is
    appended to the configured public URL automatically, but the surrounding
    network and proxy still need appropriate access controls.

## Runtime environment variables

Runtime settings use the `TABULAFLOW_` prefix. Set them before launching the
app. The value `none` disables limits that allow an unlimited setting.

### Query execution

| Variable | Default | Purpose |
| --- | ---: | --- |
| `TABULAFLOW_MAX_RESULT_ROWS` | `1000000` | Maximum rows materialized by one query |
| `TABULAFLOW_QUERY_TIMEOUT_SECONDS` | `300` | Default query deadline |
| `TABULAFLOW_MAX_QUERY_CONCURRENCY` | `8` | In-flight queries per connector |
| `TABULAFLOW_SQL_COLUMN_STATS_ENABLED` | `false` | Collect exact physical-table row counts and column statistics |
| `TABULAFLOW_MAX_GRAPH_RESULT_NODES` | `300` | Maximum nodes in a Neo4j graph result |
| `TABULAFLOW_MAX_GRAPH_RESULT_EDGES` | `700` | Maximum edges in a Neo4j graph result |
| `TABULAFLOW_MAX_SPARQL_RESPONSE_BYTES` | `52428800` | Maximum decompressed SPARQL response size |

### Agent resources

| Variable | Default | Purpose |
| --- | ---: | --- |
| `TABULAFLOW_MAX_LLM_CONCURRENCY` | `64` | Simultaneous model requests |
| `TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE` | `600` | Process-wide model request rate |
| `TABULAFLOW_MAX_EMBEDDING_CONCURRENCY` | `16` | Simultaneous embedding requests |
| `TABULAFLOW_MAX_EMBEDDING_REQUESTS_PER_MINUTE` | `150` | Process-wide embedding request rate |
| `TABULAFLOW_BROWSER_MAX_TABS` | `20` | Simultaneously open browser pages |
| `TABULAFLOW_BROWSER_HEADLESS` | `true` | Run the shared Chromium process without a visible window |

### Caching and schema inspection

| Variable | Default | Purpose |
| --- | ---: | --- |
| `TABULAFLOW_CACHE_DIR` | `~/.tabulaflow/cache` | Root directory for persistent caches |
| `TABULAFLOW_SCHEMA_CACHE_MODE` | `off` | Schema cache mode: `off`, `read_write`, `refresh`, or `cache_only` |
| `TABULAFLOW_SQL_QUERY_CACHE_MODE` | `off` | SQL result cache mode: `off`, `read_write`, or `refresh` |
| `TABULAFLOW_PREPROCESSING_CACHE_MODE` | `off` | Agent preprocessing cache mode: `off`, `read_write`, `refresh`, or `cache_only` |
| `TABULAFLOW_GRAPH_SCHEMA_INTROSPECTION_MODE` | `fast` | Use `fast` metadata inspection or `full_scan` graph inspection |

Caching can return stale metadata or query results when the underlying source
changes. Prefer the defaults unless repeated remote work justifies persistence;
use `refresh` when rebuilding a cache deliberately.

## Local state

TabulaFlow stores local state beneath `~/.tabulaflow/`:

| Path | Contents |
| --- | --- |
| `app_config.json` | Saved model selection and custom presets |
| `history.jsonl` | TUI input history |
| `sample_data/` | Shared copy of the bundled sample database |
| `cache/` | Optional persistent schema, query, and preprocessing caches |
| `sessions/<id>/` | Workspace database, logs, trajectories, temporary files, and browser-pane artifacts |

Session directories are created with user-only permissions where the platform
supports them. They can still contain prompts, results, and source-derived
data; review them before sharing or disposing of a machine used with sensitive
information. See [Security and privacy](../reference/security-and-privacy.md).
