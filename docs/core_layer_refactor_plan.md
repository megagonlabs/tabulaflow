# Core Layer Refactor Plan

> Historical implementation plan. Paths and examples describe migration-time
> architecture; the current source tree and `AGENTS.md` are authoritative.

## Implementation status

Implemented on the `refactor/ultimate-layer-architecture` branch. The legacy
`datasources`, `toolhub`, `modulehub`, and top-level `chat` packages were removed;
there are no compatibility import shims. The final architecture is enforced by
import-linter.

## Goal

Refactor TabulaFlow into a small set of intuitive layers while keeping `core` clean, minimal, and stable.

Final top-level package shape:

```text
tabulaflow/
  config.py
  core/
  data/
  output/
  agents/
  app/
  research/
```

Layer meanings:

- `core`: stable primitives and deterministic helpers.
- `data`: connect to, load, introspect, and query data. Queryable backends are connectors; raw external inputs are loaded by loaders.
- `output`: structured output protocol: parameters, output sources, display artifacts, result storage/resolution, and output-facing formatting.
- `agents`: ChatSession, agent trace models, model-facing tools, LLM runtime, modules, and subagents.
- `app`: bundled end-user TUI/app.
- `research`: benchmarks, metrics, eval pipelines, and research-only agents.

Dependency direction:

```text
core
  ↓
data
  ↓
output
  ↓
agents
  ↓
app
```

`research` is a leaf consumer: it may import `core`, `data`, `output`, and `agents`, but nothing should import `research`.

## Final core layer decision

Use the name `core`, not `foundation`, `types`, `common`, or `shared`.

Reasoning:

- `core` is conventional and communicates central platform primitives.
- `foundation` is too broad now that live runtime machinery is moving to `data`, `output`, and `agents`.
- `types` is too narrow and implementation-oriented; these are domain primitives, not just type aliases.
- `common` / `shared` invite unrelated shared-code dumping.

Definition:

> `core` contains stable primitives and deterministic operations on those primitives. It must not contain concrete runtime integrations, product workflows, app state, or research concepts.

## Final `core/` file structure

```text
core/
  __init__.py
  schema.py
  results.py
  serialization.py
  registry.py
```

This is intentionally not one giant `types.py`, but also not one-file-per-small-concept fragmentation.

## `core/schema.py`

Owns database and graph schema primitives.

Move here:

- `SQLDialect`
- `GraphQueryLanguage`
- `TableRef`
- `ColumnRef`
- `ForeignKeySchema`
- `SQLColumnSchema`
- `NamePattern`
- `SQLTableSchema`
- `SQLSchema`
- `GraphPropertySchema`
- `NodeSchema`
- `RelationshipEndpoint`
- `RelationshipSchema`
- `PropertyGraphSchema`

Rationale: these are central data/schema structures consumed by data connectors, output rendering, agents, app, and research.

Do not split `TableRef` / `ColumnRef` into a separate `refs.py` initially; they are schema-adjacent and small.

## `core/results.py`

Owns raw execution result primitives.

Move here:

- `ErrorInfo`
- `GraphResultNode` (rename from `GraphViewNode`)
- `GraphResultEdge` (rename from `GraphViewEdge`)
- `GraphResult` (rename from `GraphView`)
- `ExecResult`

Rationale: `data` produces `ExecResult`, `output` stores/resolves/displays it, `agents` use it in tools, and `research` evaluates it. It is a core platform result shape.

Notes:

- `GraphResult` stays in core because it is attached to query results, especially graph query results. Rendering graph results belongs outside core.
- Rename `GraphView` / `GraphViewNode` / `GraphViewEdge` to `GraphResult` / `GraphResultNode` / `GraphResultEdge`. `View` sounds presentation/UI-oriented, while this object is a graph-shaped execution-result payload.
- `ErrorInfo` stays in `results.py`, not `errors.py`, because it is a structured result payload rather than an exception class.
- `ExecResult.to_markdown()` is presentation-ish. It can remain temporarily to reduce churn, but the clean target is to move result formatting to `output`.

Do not merge `results.py` into `schema.py`, `data`, or `output`. Execution results are a distinct platform primitive.

## No `core/trace.py`

Do not keep usage, messages, or trajectories in core.

Move these to `agents/trace.py`:

- `Usage`
- `SystemMessage`
- `UserMessage`
- `ToolCall`
- `AssistantMessage`
- `ToolResponse`
- `Message`
- `Trajectory`

Rationale: usage, messages, and trajectories are pure data models, but they describe the agents/LLM interaction domain. This mirrors the output-layer decision: pure data structures live in the layer whose domain they describe when there is a clear owner. `OutputSpec` belongs to `output`; `Usage` and `Trajectory` belong to `agents`.

Provider/runtime adapters also live with agents:

- `Usage.from_pydantic_ai_usage(...)` or a free `usage_from_pydantic_ai_usage(...)`
- `Trajectory.from_pydantic_ai_messages(...)` or a free `trajectory_from_pydantic_ai_messages(...)`
- `compute_api_cost(...)`
- `pydantic_ai_model_to_litellm_model(...)`
- trajectory markdown/debug formatting

Core keeps only cross-layer platform contracts with no clearer owning subsystem, such as schemas and execution results.

## `core/serialization.py`

Owns pure serialization/conversion helpers needed by core models.

Move/keep here:

- `json_ready`
- `dumps_strict_json`
- DataFrame serialization/sanitization helpers currently used by `SQLTableSchema.sampled_df` and `ExecResult.df`
- `_serialize_dataframe(...)`
- `_deserialize_dataframe(...)`
- `_sanitize_df(...)`
- helper functions needed by those DataFrame serializers

Rationale: `ExecResult` and `SQLTableSchema` currently store pandas DataFrames and need stable JSON round-tripping. Serialization is core; display formatting is not.

Do **not** keep file-writing helpers here:

- `write_strict_json(...)` should move out of core because it performs file I/O. Current app-pane usage can own a local helper or move to app/output I/O.

Move display helpers out of core:

- `format_dataframe(...)`
- `format_single_line_text(...)`
- `format_ratio_as_percent(...)`
- `format_column_type(...)`
- `format_json_schema_type(...)`

Target home for display formatting:

```text
output/
```

Do not split into `json.py` and `dataframe.py` initially. A single `serialization.py` is the minimal clear abstraction.

## `core/registry.py`

Owns only the generic named class/plugin registry.

Final name:

```python
class NamedClass(Protocol): ...
class ClassRegistry(Generic[T]): ...
```

Use `ClassRegistry`, not the broad name `Registry`.

Rationale: this distinguishes the generic class registry from live runtime registries:

```text
core.ClassRegistry = registry of named classes/plugins
data.DBRegistry    = registry of live database connectors
```

Consumers include formatter registries, preprocessor/module registries, research agent registries, dataset registries, and metric registries.

Keep methods:

- `register(cls)`
- `get_class(name)`
- `list_names()`

Move out:

- `DBRegistry` goes to `data/registry.py` because it owns live connectors and disconnect lifecycle.

## Final data layer shape

The finalized data layer shape is:

```text
data/
  __init__.py
  protocols.py
  registry.py
  url.py
  config.py
  _cache.py
  sql.py
  neo4j.py
  json_schema.py
  loaders/
    __init__.py
    _runner.py
    files.py
    huggingface.py
```

Concepts:

- **Connector**: a live queryable object. Examples: `SQLConnector`, `Neo4jConnector`.
- **Loader**: builds a connector from raw external data. Examples: `load_files`, `load_hf_dataset`.
- **Registry**: maps `db_alias` strings to live connectors. The class remains `DBRegistry` to align with the established `db_alias` vocabulary.

Naming decisions:

- Use `data/loaders/`, not `data/sources/`, because `source` is overloaded by the output layer (`SourceSpec`, `FixedResultSource`, `ParameterizedSource`).
- Use `loaders`, not `adapters` or `injectors`: these modules load external raw inputs into queryable connectors.
- Keep `DBRegistry`, not `ConnectorRegistry`, because the user/tool vocabulary is `db_alias`.
- Drop `NL2Q` from connector protocols/aliases. Use generic names such as `SQLConnectorProtocol`, `PropertyGraphConnectorProtocol`, and `DBConnector`.
- Use `data/neo4j.py`, not `data/graph.py`, because the file is backend-specific.
- Keep a single `data/sql.py` initially. Do not create `data/sql/` unless the file is later split.

## Final output layer shape

The finalized output layer shape is:

```text
output/
  __init__.py
  specs.py
  store.py
  resolver.py
  charts.py
  maps.py
  graphs.py
  schema_compression.py
  formatting/
    __init__.py
    _core.py
    _sql.py
    schema.py
    sql_basic.py
    sql_ddl.py
    cypher.py
```

Concepts:

- **Result**: a concrete materialized query result. Runtime forms include `ResultMetadata` and `ResultPayload`.
- **Source**: a declarative output source that can produce or point to a result. Examples: `FixedResultSource`, `ParameterizedSource`.
- **Artifact**: a display object over one or more output sources. Examples: table, chart, map, graph artifacts.
- **Output**: a bundle of parameters, sources, and artifacts. Represented by `OutputSpec`.

Naming decisions:

- Use the layer name `output`, not `artifacts`, because the layer is broader than display artifacts.
- Keep `OutputSpec`, `OutputStore`, and `OutputResolver` as names.
- Keep source terminology inside the output layer. `SourceSpec`, `FixedResultSource`, and `ParameterizedSource` are output source specs, distinct from data loaders.
- Keep artifact terminology for table/chart/map/graph display specs.
- Rename generic `formatter_registry` to `schema_formatter_registry` when schema formatters move here.

File ownership:

- `output/specs.py`: pure declarative output models and helpers, including `OutputSpec`, parameter specs, source specs, artifact specs, `canonical_selection_key`, and `artifact_source_ids`.
- `output/store.py`: `OutputStore`, `ResultMetadata`, `ResultPayload`, `SourceNotApplicable`, `render_parameterized_query`, `OUTPUT_STORE_SCHEMA`, and runtime result/source/artifact storage.
- `output/resolver.py`: `OutputResolver` and resolved artifact/result payload types.
- `output/charts.py`, `output/maps.py`, and `output/graphs.py`: artifact-specific grammar validation, normalization, and materialization.
- `output/formatting/`: output-facing human/LLM formatting functions and schema/ERD formatter implementations.
- `output/schema_compression.py`: lossy schema compaction for prompt and display consumption.

Dependency decisions:

- `output` may depend on `data` because `OutputStore` and `OutputResolver` materialize query-backed output sources via `db_alias` / `DBRegistry`.
- `output` must not depend on `agents`, `app`, or `research`.
- Agents produce outputs, but the output layer should not know about agents.

API cleanup:

- `OutputStore` should stop accepting `PredQuery`. Use explicit query/result arguments or a local neutral record instead:

```python
await output_store.add_fixed_result_source(
    db_alias=db_alias,
    connector_type=connector_type,
    query=query,
    exec_result=exec_result,
)
```

and:

```python
await output_store.cache_parameterized_result(
    source_id=source.id,
    connector_type=connector.connector_type,
    selection=selection,
    query=query,
    exec_result=exec_result,
)
```

`PredQuery` remains a research type only.

## Final agents layer shape

The finalized agents layer shape is:

```text
agents/
  __init__.py
  llm.py
  trace.py
  response_parsing.py
  chat/
    __init__.py
    session.py
    events.py
    toolset.py
  tools/
    __init__.py
    ...
  modules/
    __init__.py
    ...
```

Concepts:

- **ChatSession**: the reusable stateful conversation object. It owns message history, output/message stores, tool instances, model profile, workspace/registry references, and lifecycle cleanup.
- **Trace**: agent/LLM interaction records such as `Usage`, messages, tool calls, and `Trajectory`, plus provider/runtime adapters for those records.
- **LLM runtime**: model factory/settings/provider glue currently in `core/llm.py`.
- **Tools**: model-facing tools currently in `toolhub/`.
- **Modules**: LLM-powered support modules currently in `modulehub/`.

Naming decisions:

- Rename current `ChatAgent` to `ChatSession`. The current object is session-like, not a stateless agent definition.
- Move current `chat/agent.py` to `agents/chat/session.py`.
- Move current `chat/events.py` to `agents/chat/events.py`.
- Move current `core/llm.py` to `agents/llm.py`.
- Move usage/messages/trajectory models and adapters to `agents/trace.py`.
- Move current `toolhub/` to `agents/tools/`.
- Move current `modulehub/` to `agents/modules/`.
- Do not add top-level `llm/`, `chat/`, `toolhub/`, or `modulehub/` in the final architecture.
- Do not add `sdk.py` yet; make `ChatSession` clean first.

File ownership:

- `agents/llm.py`: `make_agent`, `make_model_settings`, `model_display_name`, provider wrappers, throttling, and provider setup.
- `agents/trace.py`: `Usage`, normalized message models, `Trajectory`, Pydantic AI usage/message conversion, cost calculation, and trajectory markdown/debug formatting.
- `agents/chat/session.py`: `ChatSession` turn execution, conversation state, model profile switching, progress/event streaming, and lifecycle.
- `agents/chat/events.py`: `ChatEvent`, `ChatResult`, and event models produced by `ChatSession.run_stream()`.
- `agents/chat/toolset.py`: default chat toolset construction and tool wiring helpers.
- `agents/tools/`: model-facing tools.
- `agents/modules/`: LLM-powered modules and preprocessors.

Dependency decisions:

- `agents` may depend on `core`, `data`, and `output`.
- `agents` must not depend on `app` or `research`.
- `app` and `research` are consumers of `agents`.

API cleanup:

- `RunQueryTool` should stop exposing `last_pred_query`. Use a neutral `QueryExecution` record and `last_execution()` instead.

```python
@dataclass(frozen=True)
class QueryExecution:
    output: str
    query: str
    parameter_values: dict[str, Any]
    exec_result: ExecResult
```

Research agents can convert `QueryExecution` into `research.PredQuery` when needed.

- Keep `app.SessionState` separate from `ChatSession`; it owns app-specific preset selection, source dedupe, TUI lifecycle, and workspace setup.
- Rename app fields from `_chat_agent` / `active_chat_agent` to `_chat_session` / `active_chat_session` during the app update.

Public imports should be lightweight:

```python
from tabulaflow.agents import ChatSession
from tabulaflow.agents.trace import Usage, Trajectory
from tabulaflow.agents.llm import make_agent
```

Avoid importing all tools from `agents/__init__.py` if that pulls heavy dependencies such as browser/runtime packages.

## Final app layer shape

The app layer remains the bundled end-user application and should stay a leaf over `core`, `data`, `output`, and `agents`.

Final app shape should stay close to the current structure:

```text
app/
  __init__.py
  main.py
  state.py          # renamed from session.py
  config.py
  commands.py
  tui.py
  screens.py
  widgets.py
  runtime_paths.py

  pane/
    __init__.py
    server.py
    cards.py
    tables.py
    charts.py
    maps.py
    graphs.py
    types.py
    assets/

  sample_data.py
  debug.py
  display.py
  theme.py
  banner.py
  media.py
```

Naming decisions:

- Rename `app/session.py` to `app/state.py`.
- Rename `SessionState` to `AppState`.
- Rename `_chat_agent` / `active_chat_agent` / `_build_chat_agent` to `_chat_session` / `active_chat_session` / `_build_chat_session`.
- Keep `ChatSession` in `agents/chat/session.py`; do not call the app object `AppSession` because that creates two competing session concepts.

Ownership decisions:

- `AppState` owns app-level environment and lifecycle: selected LLM preset, `DBRegistry`, workspace connector, project/scratch/data dirs, trajectory dir, source alias tracking, active `ChatSession`, and app-level cleanup.
- `ChatSession` owns one stateful conversation runtime: history, tools, output/message stores, model runtime, event stream, and chat-owned cleanup.
- Keep `create_workspace_connector(...)` in the app for now; workspace creation is app lifecycle setup. Move it lower only if a non-app SDK needs the same workspace abstraction.
- Keep app config, commands, TUI, screens, widgets, sample data, debug helpers, and pane server/rendering in `app`.
- Do not split or merge app UI files just for architecture cleanliness. App layers naturally have many concrete files; the boundary matters more than file count.

Pane boundary:

- `output/` owns output specs, result/source/artifact storage and resolution, and generic formatting.
- `app/pane/` owns concrete browser-pane rendering/server/assets for already-resolved payloads.
- The pane should not own output source resolution or query/materialization logic.

Dependency decisions:

- `app` may import `core`, `data`, `output`, and `agents`.
- Nothing in `core`, `data`, `output`, `agents`, or `research` should import `app`.
- `research` should not import `app`; any reusable rendering/reporting should live in `output` or `research`, not app.

## Final research layer decision

The later research-layer cleanup retained the same domains while clarifying their
ownership:

```text
research/
  agents/
  benchmarks/
  metrics/
  tools/
  pipelines/
  types.py
  reporting.py
  query_execution.py
  query_analysis.py
  ambiguity.py
  observability.py
```

Research is a leaf consumer of `core`, `data`, `output`, and `agents`. Nothing in the platform layers should import `research`.

The cohesive research schema remains in `types.py`; reporting and query execution
live separately. Research registries (`agent_registry`, `dataset_registry`, and
`metric_registry`) remain research concepts, and pipelines are the outermost layer.

Necessary move:

- Move `PredQuery` from core to `research/types.py`, near `GoldQuery`.
- Keep the name `PredQuery`.
- Product/tool/output code should stop using `PredQuery`; use explicit query/result arguments or a neutral `QueryExecution` record instead.
- Research agents can convert `QueryExecution` into `PredQuery` when needed.

## What must leave core

### `PredQuery`

`PredQuery` should not be in core.

Reasoning:

- The name is research-specific: it means predicted query.
- Research already has the counterpart `GoldQuery`.
- Product/tool/output usages are using it only as a generic `query + exec_result` carrier, which is a smell.
- It has research/reporting methods like `to_directory()` and `to_markdown()`.

Final home:

```text
research/types.py
```

Keep the name `PredQuery`.

Product/tool/output code should stop using `PredQuery`. Prefer explicit arguments or a local neutral execution record:

```python
@dataclass(frozen=True)
class QueryExecution:
    output: str
    query: str
    parameter_values: dict[str, Any]
    exec_result: ExecResult
```

`RunQueryTool.last_pred_query` should become something like `last_execution` or `last_query_execution`. Research agents can convert that into `PredQuery` when needed.

### DB connectors

Move all of current `core/db_connector/` to `data/`.

Target ownership:

- `SQLConnector` → `data/sql.py`
- `Neo4jConnector` → `data/neo4j.py`
- connector protocols / aliases → `data/protocols.py`
- `DBRegistry` → `data/registry.py`
- URL connection helpers / `connect_url` → `data/url.py`
- file and HuggingFace loaders → `data/loaders/`

Use `data/neo4j.py`, not `data/graph.py`, because the implementation is Neo4j-specific. Generic graph schema/result primitives stay in `core`; generic graph connector protocols stay in `data/protocols.py`.

Do not split `sql.py` during the first move. Move current `sql_conn.py` to `data/sql.py`, update imports, get tests passing, then split internals later only if needed.

### LLM runtime

Move current `core/llm.py` to `agents/llm.py`.

Reasoning: LLM provider setup, Pydantic AI wrappers, throttling, model settings, Anthropic/OpenAI/LiteLLM specifics are agent/runtime concerns, not core primitives.

### Output specs

Move current `core/outputs.py` to `output/specs.py`.

Reasoning: output specs are pure data models, but they are output-domain models, not foundational platform primitives.

This includes:

- `OutputSpec`
- `ParameterSpec`
- `ChoiceParameter`
- `NumberParameter`
- `FixedResultSource`
- `ParameterizedSource`
- `ArtifactSpec`
- `TableArtifactSpec`
- `ChartArtifactSpec`
- `MapArtifactSpec`
- `GraphArtifactSpec`

### Schema formatters

Move current `core/formatters/` to:

```text
output/formatting/
```

Reasoning: schema formatting is presentation/prompt/output behavior, not core schema modeling.

### `schema_compression.py`

Do not keep in core.

It is deterministic but lossy: it merges physical tables into logical name
patterns for compact prompt and display consumption. It therefore belongs in
`output/schema_compression.py`, not in the source-of-truth data layer.

### `er_diagram.py`

Do not keep in core unless it becomes a truly central primitive.

Recommended homes:

- `research/agents/_erd.py` while it remains an implementation detail of the research SQL agent

## Core import policy

`core` may import lightweight dependencies needed for primitives and serialization:

- `typing`
- `dataclasses`
- `decimal`
- `json`
- `math`
- `pathlib`
- `pydantic`
- `pandas` / `pyarrow` only as needed for `ExecResult` and schema sampled-DataFrame serialization

`core` must not import:

- SQLAlchemy
- Neo4j
- Pydantic AI
- LiteLLM
- Anthropic/OpenAI provider packages
- Playwright
- Textual
- Jinja2
- tabulate
- tqdm
- sqlglot
- `tabulaflow.data`
- `tabulaflow.output`
- `tabulaflow.agents`
- `tabulaflow.app`
- `tabulaflow.research`

## Refactor sequence for core

Recommended order:

1. Create the new `core/` files while keeping behavior unchanged.
2. Move schema primitives from `core/types.py` to `core/schema.py`.
3. Move result primitives to `core/results.py`.
4. Move JSON/DataFrame serialization helpers to `core/serialization.py`.
5. Rename `Registry` → `ClassRegistry` in `core/registry.py` and update consumers.
6. Move usage/messages/trajectory data models and adapters to `agents/trace.py`.
7. Remove `PredQuery` from core and move it to `research/types.py`.
8. Update `core/__init__.py` to export only stable primitives.
9. Update imports to use package boundaries where possible:

```python
from tabulaflow.core import SQLSchema, ExecResult
from tabulaflow.agents.trace import Usage, Trajectory
```

10. Delete the old `core/types.py` once all consumers are updated.

## Final `core/__init__.py` policy

Export stable primitives only.

Good exports:

- schema primitives
- result primitives
- `ClassRegistry`

Do not export:

- `Usage`
- `Trajectory`
- message/trace models
- `PredQuery`
- `OutputSpec`
- `SQLConnector`
- `DBRegistry`
- `make_agent`
- schema formatter registries
- app/research/tool classes

## Overall implementation order

Move by ownership first; split internals second.

1. Create `data/`, `output/`, and `agents/` packages.
2. Split `core/types.py` into `core/schema.py`, `core/results.py`, and `core/serialization.py`; rename `Registry` to `ClassRegistry`.
3. Move trace models/adapters to `agents/trace.py`; move `PredQuery` to `research/types.py`.
4. Move data runtime to `data/`: connectors, URL helpers, registry, schema compressor, and loaders.
5. Move output runtime to `output/`: specs, store, resolver, formatting, and schema formatters.
6. Move agent runtime to `agents/`: LLM helper, ChatSession, tools, and modules.
7. Rename app `SessionState` to `AppState` and update app imports.
8. Update import-linter rules and `AGENTS.md`.
9. Delete old modules/paths once all imports are migrated.

Do not leave permanent compatibility shims for old import paths; this repo is still pre-publication and the goal is clean architecture.

## Import-linter target

Enforce the product/platform chain:

```text
core < data < output < agents < app
```

Research is a separate leaf:

- `research` may import `core`, `data`, `output`, and `agents`.
- `research` must not import `app`.
- Nothing in `core`, `data`, `output`, `agents`, or `app` may import `research`.

## Config decision

Configuration lives at top-level `tabulaflow/config.py`. It is intentionally
cross-cutting and is not part of the stable core primitive layer. Existing
configuration behavior is preserved; splitting settings by subsystem remains a
separate concern.

## Utilities cleanup

Delete `core/utils.py` eventually by moving helpers to their owning layers:

- strict JSON helpers → `core/serialization.py`
- file-writing helpers such as `write_strict_json` → app/output I/O code
- display/table/schema formatting → `output/formatting/`
- SQL source-column analysis → `data` (for SQL analysis) or agents if only used for prompting
- metrics aggregation helpers → `research`
- LLM response parsing helpers such as `extract_code` → `agents` or `research`, depending on consumers
- async progress helpers such as `tqdm_gather_with_exceptions` → `agents` or `research`, depending on consumers

## Documentation scope

For this refactor, update only:

- this design document
- `AGENTS.md` after implementation

Leave other docs untouched unless a specific test or command depends on them. Broad documentation cleanup can happen after code stabilizes.

## Summary

Final core is:

```text
core/
  __init__.py
  schema.py
  results.py
  serialization.py
  registry.py
```

Core means:

> Stable TabulaFlow primitives and deterministic helpers.

Everything that connects, executes, resolves, renders, prompts, chats, evaluates, or manages session lifecycle belongs outside core.
