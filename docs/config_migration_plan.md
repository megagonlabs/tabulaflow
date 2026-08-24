# Configuration Migration Plan

## Status

Phase one is implemented in commit `010f6e37`:

- `tabulaflow.data.config` defines immutable SQL and Neo4j connector configuration.
- `tabulaflow.agents.config` defines immutable process-wide agent runtime configuration.
- Public configuration types are re-exported from their owning packages.
- The legacy `tabulaflow/config.py`, `tabulaflow.configure()`, and all current consumers remain in place until the migrations below are complete.

This plan is a clean break. There will be no compatibility aliases for old fields, environment-variable names, import paths, or mutation behavior.

## Goals

The final configuration system should be:

- explicit about ownership and scope;
- zero-configuration by default;
- configurable through a typed object or process-wide environment defaults;
- immutable after resolution;
- free of mutable process-global configuration;
- strict about invalid values and unknown explicit fields;
- simple for experiment scripts and normal library use;
- reproducible by serializing resolved configuration snapshots.

Field resolution is conventional Pydantic Settings behavior:

```text
explicit field value > environment variable > built-in default
```

For example, with:

```bash
export TABULAFLOW_MAX_LLM_CONCURRENCY=8
export TABULAFLOW_BROWSER_MAX_TABS=10
```

this configuration:

```python
AgentRuntimeConfig(max_llm_requests_per_minute=100)
```

resolves the explicit request rate, the two environment values, and built-in defaults for every other field. The resulting object is frozen. Later environment changes do not alter it.

## Final public configuration models

### Connector configuration

`tabulaflow.data.config` owns database execution, result safety, schema caching, and SQL-specific query caching.

Shared connector fields:

```python
cache_dir: Path = Path.home() / ".tabulaflow" / "cache"
max_result_rows: PositiveInt | None = 1_000_000
query_timeout_seconds: PositiveInt | None = 300
max_query_concurrency: PositiveInt = 8
schema_cache_mode: Literal[
    "off",
    "read_write",
    "refresh",
    "cache_only",
] = "read_write"
```

SQL-specific fields:

```python
collect_column_stats: bool = False
query_cache_mode: Literal[
    "off",
    "read_write",
    "refresh",
] = "off"
```

Neo4j-specific fields:

```python
schema_introspection_mode: Literal["fast", "full_scan"] = "fast"
max_graph_result_nodes: PositiveInt | None = 300
max_graph_result_edges: PositiveInt | None = 700
```

`fast` uses Neo4j metadata procedures. `full_scan` explicitly scans graph data
to derive observed node and relationship properties and topology.

The public types are:

```python
from tabulaflow.data import SQLConnectorConfig, Neo4jConnectorConfig
```

The common connector base remains private. Column statistics are an opt-in,
timeout-bounded enrichment. Every table and view uses one bounded row sample
for examples, inferred JSON structure, and displayed sample rows. Enabled
connectors additionally attempt exact row counts and full-table null and
distinct statistics for physical tables. Views are never exhaustively
profiled. Individual profiling failures retain usable structural metadata, and
the resulting best-effort schema is cached. Cache variants keep schemas built
with and without exact column statistics separate.
Cache literals remain inline because each defines one field.

### Agent runtime configuration

`tabulaflow.agents.config` owns process-wide agent infrastructure:

```python
cache_dir: Path = Path.home() / ".tabulaflow" / "cache"
preprocessor_cache_mode: Literal[
    "off",
    "read_write",
    "refresh",
    "cache_only",
] = "read_write"
max_llm_concurrency: PositiveInt | None = 64
max_llm_requests_per_minute: PositiveInt | None = 600
max_embedding_concurrency: PositiveInt | None = 16
max_embedding_requests_per_minute: PositiveInt | None = 150
browser_max_tabs: PositiveInt | None = 20
browser_headless: bool = True
```

The public type is:

```python
from tabulaflow.agents import AgentRuntimeConfig
```

Preprocessor caching belongs in this model because it is process-wide agent-layer operational policy. There is no separate `ModuleConfig`.

`query_timeout_seconds` does not belong here. Query execution and cancellation are connector responsibilities, including for non-agent callers.

`disable_bigquery_tracing` does not belong here. TabulaFlow should not mutate BigQuery's OpenTelemetry module global. Span suppression, if genuinely needed, belongs at the observability/export boundary.

## Environment namespace

Use one flat, user-oriented `TABULAFLOW_*` namespace. Python model boundaries already express ownership; environment variables describe process-wide defaults.

Connector variables:

```text
TABULAFLOW_CACHE_DIR
TABULAFLOW_MAX_RESULT_ROWS
TABULAFLOW_QUERY_TIMEOUT_SECONDS
TABULAFLOW_SCHEMA_CACHE_MODE
TABULAFLOW_MAX_QUERY_CONCURRENCY
TABULAFLOW_COLLECT_COLUMN_STATS
TABULAFLOW_QUERY_CACHE_MODE
TABULAFLOW_QUERY_CACHE_STORE
TABULAFLOW_SCHEMA_INTROSPECTION_MODE
TABULAFLOW_MAX_GRAPH_RESULT_NODES
TABULAFLOW_MAX_GRAPH_RESULT_EDGES
```

Agent variables:

```text
TABULAFLOW_CACHE_DIR
TABULAFLOW_PREPROCESSOR_CACHE_MODE
TABULAFLOW_MAX_LLM_CONCURRENCY
TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE
TABULAFLOW_MAX_EMBEDDING_CONCURRENCY
TABULAFLOW_MAX_EMBEDDING_REQUESTS_PER_MINUTE
TABULAFLOW_BROWSER_MAX_TABS
TABULAFLOW_BROWSER_HEADLESS
```

A shared name has shared meaning. For example, `TABULAFLOW_MAX_RESULT_ROWS` applies to both SQL and Neo4j connectors. Per-instance differences use explicit config objects.

Use the string `none` for an unlimited optional positive limit:

```bash
TABULAFLOW_MAX_LLM_CONCURRENCY=none
```

Zero and negative limits are invalid rather than aliases for unlimited.

Credentials and external observability configuration retain their established environment variables, such as `OPENAI_API_KEY`, database credentials, `OTEL_EXPORTER_OTLP_ENDPOINT`, and `OTEL_SERVICE_NAME`. They are not fields in TabulaFlow operational config models.

## Cache mode semantics

Schema and preprocessor caches support four modes:

| Mode | Read existing cache | Compute on miss | Write result |
|---|---:|---:|---:|
| `off` | no | yes | no |
| `read_write` | yes | yes | yes |
| `refresh` | no | yes | yes |
| `cache_only` | yes | no; fail | no |

Mapping from the legacy booleans:

| New mode | Legacy flags |
|---|---|
| `off` | `enabled=False` |
| `read_write` | `enabled=True`, `overwrite=False`, `required=False` |
| `refresh` | `enabled=True`, `overwrite=True`, `required=False` |
| `cache_only` | `enabled=True`, `overwrite=False`, `required=True` |

This removes meaningless or invalid combinations such as disabled-plus-overwrite and required-plus-overwrite.

Query caching supports only `off`, `read_write`, and `refresh`. It does not expose `cache_only`, because failing every uncached query is not existing or desired behavior.

Query cache operation and result eligibility are separate:

```python
query_cache_mode="read_write"
```

## Public construction behavior

Normal callers do nothing:

```python
db = await SQLConnector.from_url_async(...)
session = ChatSession(...)
```

A connector omitted config resolves a fresh immutable connector configuration from explicit defaults and environment variables:

```python
config = SQLConnectorConfig()
```

Advanced connector callers pass one object:

```python
db = await SQLConnector.from_url_async(
    ...,
    config=SQLConnectorConfig(
        max_result_rows=50_000,
        schema_cache_mode="refresh",
    ),
)
```

Do not duplicate configuration fields as flattened connector keyword overrides. Keep required identity, source, and dependency arguments direct; keep operational policy in the config object.

Higher-level loaders and benchmark objects accept a connector config once and forward it to connectors they construct. Ordinary users do not pass the same config through every internal `from_url_async()` call.

## Process-wide agent runtime

LLM and embedding limits and the browser page cap are intentionally process-wide. Passing an `AgentRuntime` through every chat session, tool, module, research agent, metric, and pipeline would add broad dependency plumbing while implying that independent per-session limits are supported. They are not: multiple independent limiters could collectively exceed the provider's process/account budget.

Use one private, lazily initialized process-wide runtime:

```python
class _AgentRuntime:
    config: AgentRuntimeConfig
    # LLM and embedding limiters
    # shared model/client caches
    # shared browser manager
```

Internal access:

```python
def _get_agent_runtime() -> _AgentRuntime:
    ...
```

Central infrastructure uses it:

- `make_agent()` obtains model/client caches and LLM throttles from it.
- `embedding_throttle()` obtains embedding throttles from it.
- the default browser manager is owned by it.
- cached preprocessors read `cache_dir` and `preprocessor_cache_mode` from its immutable snapshot.

No runtime argument is added across `core`, `data`, `output`, app state, chat sessions, research agent protocols, or individual LLM helpers.

Normal use lazily constructs `_AgentRuntime(AgentRuntimeConfig())`. This preserves the researcher workflow:

```bash
TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=100 uv run experiment.py
```

without changing the experiment script.

Advanced programmatic setup uses one-time initialization:

```python
from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime

initialize_agent_runtime(
    AgentRuntimeConfig(
        max_llm_concurrency=8,
        max_llm_requests_per_minute=100,
    )
)
```

Initialization rules:

1. It is optional.
2. It must happen before first runtime use.
3. A second initialization raises an error.
4. The resolved config is immutable.
5. There is no public reset or reconfiguration API.
6. Tests may use a private reset fixture.

A private process-wide runtime is shared resource state, not mutable process-global configuration.

## Query timeout behavior

The legacy timeout is currently captured by agent query tools and the result-population CLI; direct connector calls are unbounded. The final design moves the default to connector configuration so all connector users receive consistent execution safety.

Connector methods use a private `_UNSET` sentinel so all three useful states remain
available:

```text
timeout omitted → use connector configuration
timeout=None    → explicitly disable the timeout
timeout=60      → override with 60 seconds
```

Connectors resolve the effective timeout before execution and use it consistently
for execution, cancellation, driver calls, and query-cache keys. A plain private
`object()` sentinel is sufficient; it is not part of the public API.

Agent query tools stop reading global configuration. With no explicit tool timeout, they delegate to the connector default. A numeric tool timeout remains an operation-specific override.

The result-population CLI uses `--timeout` as an optional override. Omitting it delegates to each connector's configured default.

## Cache paths and global identifiers

Keep cache directories flat by artifact kind:

```text
cache/schemas/v1[@<variant>]@<global_id>.json
cache/query_results/v1@<global_id>@<query-hash>.json
```

Do not repeat connector type in the directory hierarchy. `global_id` is a genuine
cross-backend uniqueness contract and must also be filename-safe. Schema filenames
include a cache-format version. SQL variants include profiling policy plus a
fingerprint of schema scope and structural-reuse assumptions; Neo4j variants include
the introspection mode.
Query-result caching is disk-only, atomic, and available only for read-only connectors.

## Settings that are intentionally removed

### Logging level

Delete `log_level` from TabulaFlow configuration. Libraries emit logs but do not call `logging.basicConfig()` or choose the application's log level.

- The app configures logging in its entry point and may expose `--log-level`.
- Research pipelines configure logging from their CLI, including existing debug behavior.
- Direct library users use standard Python logging configuration.

### Instrumentation enabled

Delete `instrument_enabled`. Instrumentation activation is a process-wide side effect, not a runtime setting.

Add an explicit, idempotent agent observability function, such as:

```python
from tabulaflow.agents.observability import instrument_agents

instrument_agents()
```

It owns `Agent.instrument_all()` and supported backend initialization. Entry points that want instrumentation call it; those that do not simply omit the call.

### Instrumentation prefix

Delete `instrument_prefix`. Experiment identity should not be concatenated into every span name. Use parent experiment spans, span attributes, backend project metadata, or `OTEL_SERVICE_NAME`. Keep child span names stable, such as `qid=123`.

### BigQuery tracing suppression

Delete `disable_bigquery_tracing` and the monkey patch that sets BigQuery's `HAS_OPENTELEMETRY` module global. If BigQuery spans need suppression, filter them through the observability exporter/span processor or entry-point instrumentation configuration.

## Migration phases

### Phase 1: configuration models — complete

- Add immutable data and agent config models.
- Use flat environment names.
- Validate explicit-over-environment-over-default precedence.
- Validate `none`, positive limits, unknown fields, and immutability.
- Re-export public config types from their owning packages.
- Leave legacy consumers unchanged.

### Phase 2: data layer — complete

1. Add optional `config` to SQL and Neo4j connector factories.
2. Resolve `SQLConnectorConfig()` or `Neo4jConnectorConfig()` when omitted.
3. Store the immutable config on each connector.
4. Replace all data-layer `tabulaflow_config` reads with the stored connector config.
5. Replace schema-cache booleans with `schema_cache_mode` behavior.
6. Replace SQL query-cache booleans with `query_cache_mode`.
7. Cache only successful row-returning query results; never cache errors or no-result statements.
8. Apply `max_result_rows=1_000_000` by default.
9. Apply connector-level `query_timeout_seconds` when no operation override is supplied.
10. Use `Path` operations for cache paths.
11. Update Hugging Face loading/cache code to receive relevant config from its owning loader or connector workflow.
12. Update app workspace/sample-data construction and research benchmark loaders.
13. Replace global-mutation result-limit tests with explicitly configured connector instances.
14. Remove every data-layer import of `tabulaflow.config`.

Connector-specific constructor booleans that duplicate config policy, such as `enable_schema_caching` and `enable_query_caching`, should be removed. Special connectors use explicit config objects, for example workspace caching modes set to `off`.

### Phase 3: process-wide agent runtime — complete

1. Implement private `_AgentRuntime` and `_get_agent_runtime()`.
2. Add public one-time `initialize_agent_runtime(config)`.
3. Move LLM and embedding throttle caches into the runtime.
4. Move shared base model/client caches into the runtime.
5. Move the process-wide browser manager into the runtime.
6. Make `make_agent()`, `embedding_throttle()`, and browser defaults use the runtime.
7. Make cached preprocessors use runtime `cache_dir` and `preprocessor_cache_mode`.
8. Replace preprocessor cache booleans with the four cache modes.
9. Make agent query tools delegate timeout defaults to connectors.
10. Remove all agent-layer imports of `tabulaflow.config`.
11. Add tests for lazy initialization, explicit initialization, conflicting second initialization, shared throttles, environment resolution, and private test reset.

Do not add runtime parameters throughout chat, tools, modules, app, or research.

### Phase 4: observability and entry points

1. Add explicit, idempotent agent instrumentation setup.
2. Move `Agent.instrument_all()`, Phoenix, and Langfuse initialization to the observability owner.
3. Remove the global-config check from the research instrumentation decorator.
4. Replace instrumentation prefixes with parent spans and structured attributes.
5. Remove BigQuery tracing suppression.
6. Move logging setup into app and research entry points.
7. Remove no-op calls to `tabulaflow.configure()` from scripts and pipelines.

### Legacy `tabulaflow.configure()` call sites

Migrate every call according to the responsibility it currently changes; do not
mechanically replace `tabulaflow.configure()` with another general initializer.

| Current caller pattern | Final treatment |
|---|---|
| `tabulaflow.configure()` with no arguments | Delete the call. Initialize logging or observability explicitly only where that entry point needs it. |
| App startup disables query caching | Construct the app's connector config once and pass it through app source/workspace construction. |
| App startup sets `instrument_enabled=False` | Delete it; the app simply does not call `instrument_agents()`. |
| App startup sets `log_level="WARNING"` | Configure standard Python logging in the app entry point. |
| Schema-cache scripts set enabled/required/overwrite flags | Construct `SQLConnectorConfig` with `schema_cache_mode="read_write"`, `"refresh"`, `"cache_only"`, or `"off"` and pass it to the loader/connector workflow. |
| Preprocessing scripts set preprocessor enabled/required/overwrite flags | Initialize the agent runtime once with the corresponding `preprocessor_cache_mode`. |
| Result-population pipeline enables or disables query caching | Construct connector configs with `query_cache_mode="read_write"` or `"off"`; keep `--timeout` as an operation override. |
| Utility scripts disable schema caching | Pass connector config with `schema_cache_mode="off"`. |

This includes app startup, research pipelines, and scripts such as schema caching,
schema printing, dataset statistics, result population, preprocessing, and database
editing tests. After migration, a repository-wide search for
`tabulaflow.configure(` must return no call sites.

### Phase 5: delete the legacy system

1. Verify no imports of `tabulaflow.config` or `tabulaflow_config` remain.
2. Delete `tabulaflow/config.py`.
3. Delete `tabulaflow.configure()` from the package root.
4. Delete legacy validators, proxy behavior, mutable overrides, and old environment names.
5. Update `AGENTS.md` environment-variable documentation.
6. Update public usage documentation and experiment examples.
7. Run the complete test, lint, type-check, and architecture suites.

## Test plan

### Configuration models

- built-in defaults;
- environment over defaults;
- explicit fields over environment;
- explicit one field while unrelated fields still use environment;
- SQL and Neo4j shared environment defaults;
- `none` parsing for every optional positive limit;
- rejection of zero and negative limits;
- rejection of unknown explicit fields;
- frozen snapshots;
- environment changes do not affect existing snapshots;
- cache mode validation.

### Data migration

- default and explicit result limits for SQL and Neo4j;
- connector timeout default and operation override;
- timeout included in query-cache identity using its effective value;
- every schema cache mode;
- every query cache mode;
- errors and successful no-result statements are never cached;
- independent explicit configs for two connector instances;
- shared flat environment defaults;
- workspace caching disabled explicitly.

### Agent runtime migration

- lazy runtime creation from environment;
- explicit config before first use;
- second initialization rejection;
- all root and subagent model calls share one LLM limiter;
- all embedding calls share one embedding limiter;
- all browser tools share one page cap and manager;
- preprocessors share one immutable cache policy;
- changing the environment after initialization has no effect;
- existing zero-configuration `ChatSession` and research workflows remain ergonomic.

### Final removal

Searches must return no production references to:

```text
tabulaflow_config
TabulaflowConfig
tabulaflow.configure
schema_cache_enabled
schema_cache_overwrite
schema_cache_required
preprocessor_cache_enabled
preprocessor_cache_overwrite
preprocessor_cache_required
query_cache_enabled
query_cache_overwrite
instrument_enabled
instrument_prefix
disable_bigquery_tracing
```

## Final developer experience

Default library use:

```python
db = await SQLConnector.from_url_async(...)
session = ChatSession(...)
```

Experiment-wide environment adjustment:

```bash
TABULAFLOW_MAX_LLM_REQUESTS_PER_MINUTE=100 \
TABULAFLOW_QUERY_TIMEOUT_SECONDS=120 \
uv run experiment.py
```

Per-connector specialization:

```python
db = await SQLConnector.from_url_async(
    ...,
    config=SQLConnectorConfig(
        max_result_rows=50_000,
        schema_cache_mode="refresh",
    ),
)
```

One-time programmatic agent-runtime specialization:

```python
initialize_agent_runtime(
    AgentRuntimeConfig(
        max_llm_concurrency=8,
        browser_max_tabs=10,
    )
)
```

There is no mutable global config, no repeated runtime argument plumbing, no duplicated flattened config fields, and no package-level logging or third-party tracing mutation.
