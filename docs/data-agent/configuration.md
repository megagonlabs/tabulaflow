# Configuration

Most users only need to install TabulaFlow and set one model-provider API key.
TabulaFlow then selects suitable main-agent and subagent models automatically;
use `/config` to change them. The remaining settings control optional browser
support, resource limits, schema caching, and browser-pane networking.

## Installation

Choose an installation method:

=== "uv (recommended)"

    ```bash
    # Install as an isolated tool available from any directory
    uv tool install tabulaflow

    # Upgrade an existing installation
    uv tool upgrade tabulaflow
    ```

=== "pip"

    ```bash
    # Create and activate a virtual environment
    python -m venv .venv
    source .venv/bin/activate

    # Install TabulaFlow
    python -m pip install tabulaflow

    # Upgrade an existing installation
    python -m pip install --upgrade tabulaflow
    ```

## Model setup

The Data Agent includes recommended OpenAI and Anthropic models. Set a key for
the provider you use:

```bash
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
```

You need only one key. Without a saved configuration, TabulaFlow checks OpenAI
first, then Anthropic, and selects recommended models for both agent roles.

Run `/config` to configure the main agent and subagent independently. The model
picker accepts any provider-qualified identifier supported by the installed
model stack, such as `openai:gpt-5.6-sol`. Disabling the LLM turns off
conversational analysis but keeps data connections and browsing available.

TabulaFlow saves your selection in `~/.tabulaflow/app_config.json`. It reads API
keys from the environment and does not save them.

## Web browsing

We recommend installing Chromium to enable web browsing and get the full
TabulaFlow experience:

=== "uv"

    ```bash
    uv tool run --from playwright playwright install chromium
    ```

=== "pip"

    ```bash
    playwright install chromium
    ```

Database and local-file workflows do not use Chromium.

## Command-line options

These options apply to one launch:

| Option | Purpose |
| --- | --- |
| `--llm-service-tier` | Use `default` or `priority` request service; priority may cost more |
| `--enable-schema-cache` | Persist database schemas for faster repeated connections |
| `--log-level` | Set file logging to `debug`, `info`, `warning`, or `error` |
| `--output-pane-port` | Require a specific browser-pane port instead of the first free port in `61111–61130` |
| `--output-pane-host` | Change the bind host from `127.0.0.1` |
| `--output-pane-public-url` | Set the browser-facing base URL when the bind address is not directly reachable |

Run `tabulaflow --help` to see the full syntax.

## Use TabulaFlow on a remote server

If you can open an interactive SSH session on the server, you can run the full
TabulaFlow TUI in that terminal. The browser output pane runs as a separate
local web server, so accessing it from your computer requires a tunnel, direct
network access, or a reverse proxy.

### SSH port forwarding

SSH port forwarding is the recommended approach because the output pane does
not need to be exposed to the network. From your local computer, connect with a
fixed forwarded port:

```bash
ssh -L 61111:127.0.0.1:61111 user@server
```

Then launch TabulaFlow in the SSH session with the same port:

```bash
tabulaflow --output-pane-port 61111
```

Open the output-pane URL shown by the TUI in your local browser.

### Direct private-network access

If the server is reachable only through a trusted private network or VPN, you
can bind the output pane to the server's network interfaces:

```bash
tabulaflow \
  --output-pane-host 0.0.0.0 \
  --output-pane-port 61111 \
  --output-pane-public-url http://server.internal:61111
```

Allow the selected port through the server's firewall only for the trusted
network. `--output-pane-public-url` sets the address shown by the TUI;
TabulaFlow automatically appends the session token. Do not expose the port
directly to the public internet.

### Reverse proxy

For shared or publicly reachable environments, place the output pane behind an
authenticated HTTPS proxy. Keep the pane bound to the server's loopback
interface, configure the proxy to forward to it, and provide the browser-facing
URL:

```bash
tabulaflow \
  --output-pane-port 61111 \
  --output-pane-public-url https://example.com/tabulaflow
```

!!! warning "Secure remote output access"
    The output pane may display prompts, source data, and query results.
    TabulaFlow includes a per-session token in every output-pane URL as a safety
    measure, and requests without that token are rejected. Keep the URL private.
    When exposing the pane beyond a trusted machine, also restrict network
    access and use an authenticated HTTPS proxy.

## Environment variable reference

The following `TABULAFLOW_` environment variables affect the interactive Data
Agent; settings used only by the Python library or research toolkit are not
included. Set them before launching the app. Use `none` for limits that support
an unlimited value.

### Query execution

| Variable | Default | Purpose |
| --- | ---: | --- |
| `TABULAFLOW_MAX_RESULT_ROWS` | `1000000` | Maximum rows materialized by one query |
| `TABULAFLOW_QUERY_TIMEOUT_SECONDS` | `300` | Default query deadline |
| `TABULAFLOW_MAX_QUERY_CONCURRENCY` | `8` | In-flight queries per connector |
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

### Schema inspection and storage

| Variable | Default | Purpose |
| --- | ---: | --- |
| `TABULAFLOW_CACHE_DIR` | `~/.tabulaflow/cache` | Root directory for persistent caches |
| `TABULAFLOW_SQL_COLUMN_STATS_ENABLED` | `false` | Collect physical-table row counts and column statistics |
| `TABULAFLOW_GRAPH_SCHEMA_INTROSPECTION_MODE` | `fast` | Use `fast` metadata inspection or `full_scan` graph inspection |

The Data Agent keeps query-result and agent-preprocessing caches off. Schema
caching is also off by default; enable it for repeated connections with
`--enable-schema-cache`. Cached schemas can become stale when a source changes.

## Local state

TabulaFlow stores local state beneath `~/.tabulaflow/`:

| Path | Contents |
| --- | --- |
| `app_config.json` | Saved main-agent and subagent model configuration |
| `history.jsonl` | TUI input history |
| `sample_data/` | Shared copy of the bundled sample database |
| `cache/` | Optional persistent schemas and other cached data |
| `sessions/<id>/` | Workspace database, logs, trajectories, temporary files, and browser-pane artifacts |

Where supported, session directories use permissions for the current user
only. They may still contain prompts, results, and source data. Review them
before sharing or disposing of a machine.

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
