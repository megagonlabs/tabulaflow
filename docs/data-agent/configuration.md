# Configuration

The defaults suit local use. Change them to select a model, control resources,
enable caching, or expose the output pane on another host.

## Model selection

The Data Agent includes OpenAI and Anthropic presets. Set a key for the provider
you use:

```bash
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
```

You need only one key. Without a saved preference, TabulaFlow checks OpenAI
first, then Anthropic, and selects a balanced preset.

Run `/config` to view the presets and save your choice. **Off** disables
conversational analysis but keeps data connections and browsing available.

Override the saved preset for one launch:

```bash
tabulaflow --llm-preset "OpenAI budget"
tabulaflow --llm-preset off
```

TabulaFlow saves your selection in `~/.tabulaflow/app_config.json`. It reads API
keys from the environment and does not save them.

## In-app commands

| Command | Purpose |
| --- | --- |
| `/help` | Show available commands |
| `/config` | Open model configuration |
| `/connect <source...> [--alias name]` | Connect a data source |
| `/disconnect [alias]` | Disconnect a user source |
| `/clear` | Start a new conversation in the current session |
| `/exit` | Close the app |

Commands autocomplete as you type. `/connect` also completes local paths.

## Command-line options

These options apply to one launch:

| Option | Purpose |
| --- | --- |
| `--llm-preset`, `-p` | Override the saved model preset or use `off` |
| `--llm-service-tier` | Use `default` or `priority` request service; priority may cost more |
| `--enable-schema-cache` | Persist database schemas for faster repeated connections |
| `--log-level` | Set file logging to `debug`, `info`, `warning`, or `error` |
| `--output-pane-port` | Require a specific browser-pane port instead of the first free port in `61111–61130` |
| `--output-pane-host` | Change the bind host from `127.0.0.1` |
| `--output-pane-public-url` | Set the browser-facing base URL when the bind address is not directly reachable |

Run `tabulaflow --help` to see the full syntax.

!!! warning "Exposing the output pane"
    Keep the default loopback host unless you need remote access. Output pages
    may contain session data and query results. TabulaFlow adds a session token
    to the public URL, but you must still secure the network and proxy.

## Runtime environment variables

Set `TABULAFLOW_` variables before you launch the app. Use `none` for limits
that support an unlimited value.

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

Cached metadata and results can become stale when a source changes. Keep
caching off unless repeated remote work makes it useful. Use `refresh` to
rebuild a cache.

## Local state

TabulaFlow stores local state beneath `~/.tabulaflow/`:

| Path | Contents |
| --- | --- |
| `app_config.json` | Saved model selection and custom presets |
| `history.jsonl` | TUI input history |
| `sample_data/` | Shared copy of the bundled sample database |
| `cache/` | Optional persistent schema, query, and preprocessing caches |
| `sessions/<id>/` | Workspace database, logs, trajectories, temporary files, and browser-pane artifacts |

Where supported, session directories use permissions for the current user
only. They may still contain prompts, results, and source data. Review them
before sharing or disposing of a machine. See [Security and
privacy](../reference/security-and-privacy.md).
