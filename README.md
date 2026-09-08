# tabulaflow

## Quick Start

```bash
git clone https://github.com/megagonlabs/tabulaflow.git
cd tabulaflow
uv tool install --editable .
uv tool run --from playwright playwright install chromium
```

Then run tabulaflow from the project you want it to work on, like Claude Code:

```bash
cd /path/to/your/project
export OPENAI_API_KEY=sk-...
tabulaflow
```

The app uses the provider's standard service tier by default. Priority processing
is a launch-only option and may incur premium API pricing:

```bash
tabulaflow --service-tier priority
```

tabulaflow uses the launch directory as its project directory, so local file
paths and shell commands resolve relative to `/path/to/your/project` in the
example above.

For development on tabulaflow itself, sync the repo environment and use the
developer commands below:

```bash
cd /path/to/tabulaflow
make sync
```

`make sync` also installs Playwright's Chromium browser.


Paste this after launch to a quick smoke test:

> Using the sample data, do a quick test of your tools and flag any non-functioning tools: use subagents, browser, use the file_editor and shell somewhere along the way. Write a markdown answer that first summarize the tool checks in small markdown table, then greet the user and introduce tabulaflow and what you can do using rich markdown syntax, and show artifacts in order: a filtered transactions data table, a bar chart showing top 5 merchants, a richer chart, a map of the taxi zones, a accounts-merchants graph, and two additional data tables, keep the artifact label short.

---
---
---
# ====== BELOW IS OUTDATED ======
---
---
---

## Library configuration

Agent runtime configuration is optional. Default values and `TABULAFLOW_*`
environment variables are resolved lazily on first use:

```python
import asyncio

from tabulaflow.agents import ChatSession
from tabulaflow.data import DBRegistry

async def main() -> None:
    session = ChatSession(
        registry=DBRegistry(),
        model="openai-responses:gpt-5",
        reasoning="medium",
        service_tier="priority",
    )
    try:
        result = await session.run("Which tables contain customer data?")
        print(result.text)
    finally:
        await session.aclose()

asyncio.run(main())
```

Lower-level LLM consumers accept `model_settings`; use the shared types and
helper so reasoning and service tiers retain their cross-provider semantics.
For `reasoning`, `None` leaves the setting unspecified, `False` disables it,
`True` uses the provider default, and a named level requests that effort:

```python
from tabulaflow.agents.llm import ReasoningLevel, ServiceTier, make_model_settings

reasoning: ReasoningLevel = "low"
service_tier: ServiceTier = "priority"
model_settings = make_model_settings(
    model="openai-responses:gpt-5-mini",
    reasoning=reasoning,
    service_tier=service_tier,
)
```

For programmatic runtime overrides, initialize once before creating agents:

```python
from tabulaflow.agents import AgentRuntimeConfig, initialize_agent_runtime

initialize_agent_runtime(
    AgentRuntimeConfig(
        max_llm_concurrency=8,
        browser_max_tabs=10,
    )
)
```

Logging and tracing are explicit application concerns:

```python
import logging

from tabulaflow.agents import instrument_agents

logging.basicConfig(level=logging.INFO)
# Configure an OpenTelemetry provider and exporter here if tracing is desired.
instrument_agents()
```

Each of these setup steps is independent: ordinary use requires no initializer,
and `instrument_agents()` is only needed when agent traces should be emitted.

### Output API

The output layer separates declarations from runtime state:

```text
OutputSpec + selection -> OutputResolver -> ResolvedOutput
                         ^
                         OutputStore
```

Import its APIs from the module that owns them:

```python
from tabulaflow.output.specs import OutputSpec
from tabulaflow.output.store import OutputStore
from tabulaflow.output.resolver import OutputResolver
from tabulaflow.output.formatting import format_dataframe
```

`specs` contains serializable parameters, sources, and artifacts. `OutputStore`
owns materialized results and parameterized-source caches; `OutputResolver`
applies a selection and returns display-ready table, chart, map, or graph
artifacts. Artifact grammar and validation live in `charts`, `maps`, and
`graphs`.



Use `/connect` to connect to a data source (Huggingface datasets, local csv/excel files, SQL databases, etc.), then either manually browse the data in the data explorer or say "Analyze" to have LLM analyze the data.
Without a supported API key, the app starts with the LLM off; choose `Off` or a named preset in `/config`.


## Utility Commands (for developers)

We use `make` to manage a few common commands we frequently use (see [`Makefile`](Makefile) for their definitions):

```bash
make format          # format and lint
make mypy            # type check with mypy
make sync            # sync the dependencies in pyproject.toml into the venv (e.g. when others have updated the dependencies)
make last-trajectory # print the path to the last trajectory of tabulaflow-cli agent
```

## Use Cases

- Chatting to SQL databases
- Chatting to local files (csv, excel, json, …)
- Chatting to built-in public data sources (Huggingface, FRED, Wikidata …)
  - "Analyze the query template distribution of CypherBench"
  - "GDP and unemployment rates in the last 5 quarters"
- Data manipulation
  - "Transform this dataset to the OpenAI finetuning format"
- Building data from web (covers all functionalities of Blue-delibird)
  - "Find all data agent benchmarks in 2025"
  - "List all popular scuba diving destinations and the flight prices from SFO on July 1st."
- Support semantic operators (handles all data questions that Blue can handle)
  - "Tag questions that are ambiguous where both pred and gold are valid in results_gpt5.json"
  - "Tune the prompt for 5 iterations on this dataset"
  - "Translate this dataset into English and Chinese"
- Labeling data
  - "Label 10 samples" -> Manual review -> "Label all data"
- Supports cross-data-source querying
  - "What is the difference of GITHUB_REPOS and GITHUB_REPOS_DATE?"
- Supports outputting multiple tables
  - "Analyze this dataset" → distribution of domains, question complexity, ground-truth

Most useful for the lab:
- Data analysis, visualization and manipulation
- Error analysis of model predictions
- Literature survey

Partially replaces:
- Partially replaces DBeaver for data browsing
- Replaces current open-source text-to-SQL agents: Chat2DB, PandasAI, DataBao
- Partially replaces Jupyter Notebook workflows for data analysis and visualization
- Partially replaces OpenAI Deep Research agents on challenging data building tasks


## TODOs

[old worklog](backup/README_Apr20_2026.md)

April 20
- [x] Switch to parquet for df serialization
- [x] Query history with persistence to workspace DuckDB
- [x] key_columns in run_subagent tool

April 21
- [x] Json loading
- [x] Fix error on concurrent DDLs
- [x] Improve data browsing
  - [x] Live browsing
  - [x] Error on preview loading
- [x] Improve run_subagent tool
  - [x] sql_filter for filtering
  - [x] Write trajectory and error metadata to each row
  - [x] Prompt tuning use case - direct mode
  - [x] Use sqlalchemy statement

April 22
- [x] Result preview UI

April 23
- [x] Result preview UI
- [x] Ctrl+C
- [x] Cancellation for sql_conn.py

April 24
- [ ] Refactor sql_conn.py
  - [x] Use subprocess for loaders
  - [x] from_files_async to loaders/
  - [x] Test for the bug
  - [x] UI bug, spinner with error
  - [x] Cancellation for write_dataframe_async and run_query_async

April 27
- [x] Refactor sql_conn.py
  - [x] Combine timeout and cancellation handling
  - [x] remove aiosqlite path
  - [x] Cancellation for all sql dialects, sync and async
  - [x] Check ThrottledEngine API, whether engine used externally
  - [x] Access sql_conn.py and refactor
  - [x] Documentation for sql_conn.py
- [x] Fix huggingface readme fetching

April 28
- [x] Submitted issue on duckdb for https://huggingface.co/datasets/stellalisy/HorizonBench
- [x] "Enter Inspect" aligned to the right
- [x] Pydantic AI partial trajectory on interrupt
- [x] Fix missing record label
- [x] Fix scroll on column sorting
- [x] Fix first column suppressed
- [x] Multi-line copy paste
- [x] Ambrosia use case

April 29
- [x] Run sub agent - show num instead of percentage
- [x] Tune prompt
  - [x] plan mode
  - [x] pass user instructions
  - [x] run on sampled subset
  - [x] rule-based vs subagent
  - [x] batch tools

May 4
- [x] web_browser.py
  - [x] Extraction
  - [x] Concurrency

May 6
- [x] Fix df dtypes (fix int with null becomes float)
- [x] refresh for run_query tool to allow refresh after DDL
- [x] Fix mypy and tests

May 11
- [x] browser tools for subagents

May 12
- [x] Offload long user prompts and tool responses to message store
- [x] Programmatic task instruction construction using task_query
  - [x] Fix json handling
- [x] Remove json stringify
- [x] Fix json display (e.g. for JSON[])

May 13
- Fix bugs
  - [x] Fix dtype introspection, add native_dtype
  - [x] Parse nested json string
  - [x] Fix json schema rendering
- Cell browser
  - [x] Fix large cell display (no truncation and auto-disabling soft wrap)
  - [x] "Loading cell..." status
  - [x] Open in browser

May 14
- [x] "Open in browser" for table
- [x] Support multimedia data

May 15
- [x] "Open in browser" for table

May 17 
- "Open in browser" for table
  - [x] Support pdf
  - [x] "Opening..."

May 18
- UI improvements
  - [x] shift+up/down for past results
  - [x] auto-focus last result
  - [x] typeahead
  - [x] Hint colors
  - [x] Speed up table rendering in preview and data browser (binary and long cell)
  - [x] Fix image/audio support for huggingface
  - [x] "Open data explorer" button

May 19
- UI improvements
  - [x] Highlight result when focused
  - [x] New UI - "Esc" instead of "Shift+up/down"
  - [x] Input row style

May 20
- UI improvements
  - [x] PgUp/down when input is focused
  - [x] "(first 50 rows)" in data explorer
  - [x] Persistent schema browser state (expand/collapse state, cursor location)
  - [x] Do not allow disconnecting workspace
- Web browsing
  - [x] ScopedMessageStore with agent_id
  - [x] Remove agentic mode
  - [x] enable_nested_subagents
  - [x] enable_run_query_tool

May 21
- Web browsing
  - [x] Offloading mechanism for subagents
  - [x] Tune tool description for run_subagent_for_each_row tool
  - [x] Tune agent prompt
  - [x] Concurrency control for web browsing

May 22
- web_browser.py
  - [x] Fix no snapshot included when submit=False
  - [x] Type slowly
  - [x] wait for text/text_gone
  - [x] native <select>
  - [x] Include options, state, current value
  - [x] Include leaf clickable generic
  - [x] Rewrite snapshot by direct aria-to-markdown conversion - inline all elements

May 26
- web_browser.py
  - [x] Debug gpt-5-mini browser use -> Reason: agent reuses old refs
  - [x] Fix refs re-use (prompt + always full snapshot)
  - [x] Add tab param to browser_navigate
  - [x] Allow subagent to abort task with abort_task tool
  - [x] Fallback to el.click() when normal click fail
  - [x] Auto-dismiss JS dialog
  - [x] "Downloads are disabled"
  - [x] Save subagent trajectories
  - [x] Fix CancelledError handling
  - [x] _POST_LOAD_SETTLE_MS=1s
  - [x] Fix combobox options rendering
  - [x] Always type slowly
  - [x] Skip unamed textual inputs
  - [x] Hints on popup shadowing siblings
  - [x] "typing directly into combobox"

May 28
- [x] Support pdf for browser tool
- [x] extract_rows_from_documents tool

May 29
- [x] add_canonical_name tool

June 4 - June 5
- [x] Refactor to tabulaflow
- [x] Rewrite ChatAgent interface with streaming API
- [x] New banner!
- Fix bugs
  - [x] Fix inconsistent error message color
  - [x] Disable "open data explorer" button when workspace not ready

June 8
- [x] New banner that looks nice on every terminal!
- [x] Starting examples and sample_data
- Fix bugs
  - [x] web_browser.py - Paragraphs dropped on https://megagon.ai/our-team/yanlin-feng/

June 9
- Fix bugs
  - [x] Bug when disconnecting sample_data
  - [x] Remove /database /db /schema commands
  - [x] Fix PK FK colors
  - [x] Fix progress callback when concurrent tools are called at one turn
- [x] chunking for extract_rows_from_documents tool - markdown_splitter.py
- [x] Tune prompt

June 10
- [x] Automatically suspend browser during fan-out
- [x] Refactor aria_to_markdown and cover all aria roles
- [x] Refresh in schema browser
- [x] Always offload for subagents

June 11
- [x] Relax regex parsing constraint in prompt
- [x] Improve tool progress display
- [x] "empty results" -> "statement executed successfully" for DDL statements in run_query tool
- [x] Update schema browser - expand workspace tables, hide internal schemas
- [x] Fix schema resolution during write_dataframe_async (fix "(default)" schema)
- [x] Support int, numeric, boolean, date, datetime columns for extract_rows_from_documents tool
- run_subagent_for_each_row tool 
  - [x] Validate key columns
  - [x] Ensure write-back correctness - surface error, ensure exactly one row got updated
  - [x] Multi-column output
  - [x] Validate placeholder vars in task_instruction
- sql_conn.py
  - [x] ExecResult.return_rows for signaling DDL success
  - [x] ExecResult.affected_rows for signaling DML affected rows
- [x] ref-aware snippet for browser snapshots
- [x] Improve schema browser
- [x] aria_to_markdown.py - fix list items collapsed to one line
- [x] Note on deep links in web browser

June 15
- UI Improvements
  - [x] Option + left/right for input box cursor movement
  - [x] Fix schema browser table count mismatch due to visibility
  - [x] Clickable url in browser table
  - [x] Fix bug: tool progress disappears on error
  - [x] User message background
  - [x] Text selection
- Streaming API
  - [x] Move "---" handling from app/ layer to chat/ layer
  - [x] NarrationDelta and AnswerDelta

June 16
- [x] Fix bugs
  - [x] Fix bug: if ask question before workspace ready, workspace load forever
  - [x] Fix unpatched tool calls on agent error
- agent data sources
  - [x] execute_bash
  - [x] connect_data_source
  - [x] create_dataset
  - [x] url.py
  - [x] Revise prompt

June 17
- [x] Fix bugs in bash tool
- [x] Show latency in run_query
- [x] `extra_instructions` for agent

June 21
- [x] file_editor tool
- [x] Improve tool progress display, +N -M for file edits
- [x] Remove create_dataset tool
- [x] is transfer_record needed? -> yes

June 22
- [x] Support viewing local pdf in file_editor tool
- [x] Open visualization in browser

June 23
- [x] Constent verb-based tool progress display for all tools
- [x] Fix visualization issues
- [x] Output pane

June 24
- [x] Output pane

June 29
- Fix bugs
  - [x] Fix "too many open files" error
  - [x] Fix huggingface already imported warning
  - [x] Debug "analyze root directory" (mdc) -> cause is command itself is slow
  - [x] Fix output pane freezed caused by tabulator
- [x] Output pane refactor
- [x] Improve output pane UI

June 30
- [x] Map rendering

July 1
- [x] per-session token for safety
- [x] Vector map using maplibre + OpenStreetMap vector tiles

July 2
- Map rendering
  - [x] Map legend
  - [x] US highway labels and icons
  - [x] Airport icon
  - [x] Thinner borders
  - [x] Show islands
  - [x] Darken colors
- [x] Tune agent prompt - decouple source-of-truth data representation from user-facing data representation

July 6
- [x] Remove shadows of pins
- [x] Allow links in tooltip
- [x] Multiple records for map

July 7 
- [x] Revise output pane code boundary -> /pane package
- [x] Graph rendering

July 8
- Graph rendering
  - [x] Support property graphs in data explorer
  - [x] Fix PropertyGraphSchema representation
  - [x] Fix render_graph for generic Cypher queries like db.schema.visualization()
  - [x] Physics simulation for graphs
- Fix bugs
  - [x] Fix chart not shown bug
  - [x] Fix map viewport fitting  

July 9
- Graph rendering
  - [x] Refactor - docs/output_pane_lifecycle_plan.md
  - [x] Fix edge selection panning bug
  - [x] Graph - node/edge selection style
  - [x] Fix tab change fail in TUI using left/right arrow
  - [x] Make tooltip style and behavior consistent across chart/map/graph
  - [x] Fix zoom not working
  - [x] Fix node label overflow
  - [x] Disable hover tooltip for graph
  - [x] Improve node style
  - [x] Show all properties in tooltip
  - [x] Fix life cycle model - do not destroy when hidden, only when evicted
- [x] Fix chat agent not aware of non-empty registry

July 10
- [x] app/config.py and config panel

July 11
- Config panel
  - [x] Fix response format - change "---" to "<artifacts>...</artifacts>"
  - [x] Subagent model config
  - [x] Generalize provider-specific configuration
  - [x] Fix LLM configuration inconsistencies
  - [x] Hint bar
  - [x] New config UI based on LLM presets

July 12
- [x] Improve LLM configuration

July 13
- [x] Improve LLM configuration
- [x] Fix structured output for Claude - UserError: Anthropic does not support thinking and output tools at the same time. Use `output_type=NativeOutput(...)` instead.

July 14
- [x] API key detection for first time startup
- Output pane
  - [x] Fix flickering on card switch
  - [x] Fix "lodaing..." card height mismatch
  - [x] Card height animation
  - [x] View transition for turn switch
- [x] Upgrade textual to fix text selection crash
- [x] Markdown rendering in TUI and output pane
- [x] Code highlighting theme

July 15
- [x] Improve markdown rendering
- [x] Markdown syntax instructions in system prompt
- [x] Rewrite prompt

July 16
- [x] Tune prompt
  - [x] Proactiveness
  - [x] Reorder sections
  - [x] Bash safeguard
  - [x] env
  - [x] env resolution (connected sources -> repo -> web -> ...) -> deferred
- [x] Browser installation in make sync
- [x] Fix graph coloring
- [x] Per-card view stepper
- [x] Smoke test for first-time user

July 17
- [x] Fix shell messed up after exiting
- [x] Remove file editor sandbox
- [x] Make chart "view chart in browser" caption consistent
- [x] Decouple chart and data record
- [x] Avoid auto-disconnect sample_data
- [x] Fix multi-layer chart coloring
- [x] Fix Claude subagent stucked - subagent timeout at 120s

July 20
- Improve browser pane
  - [x] Remove date from session IDs, show session IDs in output pane
  - [x] Artifact icon and user icon

July 21
- Improve browser pane
  - [x] Improve code highlighting
  - [x] Copy button feedback
  - [x] Focus rings
  - [x] Latex rendering
  - [x] Image rendering
- [x] Include line numbers in view file calls

July 22
- [x] grep tool -> deferred
- [x] OpenAI/claude subscription plan -> not possible
- [x] apply_patch
- [x] Refactor toolhub
- [x] Notify model identity
- [x] Refactor chat/agent.py

July 23
- [x] Refactor toolhub
  - [x] Fix tool outcome display racing
  - [x] Fix tool error outcome display - standardize to "(error: ...)"
- [x] Mermaid rendering? flowchart support? -> defered
- [x] Fix `git diff` hung bug
- [x] Graph rendering - auto-detect Cypher graph
- [x] Fix JSON serialization bug
- [x] Fix commands.py crash
- [x] Tune prompt - "report verification concisely"
- [x] Tune prompt - coding instructions from codex

Aug 4 - 7
- [x] Fix typing/scrolling slow in 50+ turn conversation
- [x] Parametrized source

Aug 10 - Aug 13
- [x] Parametrized source

Aug 14
- [x] output pane state indicator and favicon
- [x] Repo refactor: core, data, output, agents, {app, research}
- [x] core layer cleanup

Aug 17
- [x] core layer cleanup
- [x] configuraion migration design and cleanup

Aug 18 - 19
- data layer and output layer cleanup
  - [x] graph extraction
  - [x] schema and query cache
  - [x] column stats profiling
  - [x] simplify artifact normalization api
  - [x] backend and langauge fields
  - [x] shared query concurrency configuration
- [x] parametrized graphs and maps

Aug 23
- [x] data layer and output layer cleanup
  - [x] schema compression
  - [x] find_table and find_column
  - [x] close_async and release_connections_async
  - [x] preserve schema description across refresh
- [x] Fix /clear semantics

Aug 24
- agents layer cleanup
  - [x] runtime.py
  - [x] remove engines/
  - [x] omit params
  - [x] standardize `execute` vs `__call__`
  - [x] remove modules/ and fix preprocssing caching
  - [x] summarization.py
- [x] Standardize imports
- [x] Standardize to protocols.py and registry.py, no base.py
- app
  - [x] Fix startup rendering
  - [x] New artifact browser pane life cycle to fix flicker when change selection in answer controls
  - [x] Fix artifact with empty df display
  - [x] Improve empty df artifact display
  - [x] Improve map markers and marker size legend
  - [x] Fix map popup scrolling

Aug 25
- agents layer cleanup
  - [x] chat/
  - [x] `<answer>` -> `ANSWER:`
- app
  - [x] align to browser pane column width
  - [x] map artifact no data box
  - [x] control panel UI
  - [x] redesign artifact tab menu
  - [x] subgraph title color
  - [x] disable range selection, add table copy table button
- [x] Share updates to #mintq and Hongjie

Aug 26
- app
  - [x] redesign artifact menu layout
  - [x] fix scrolling when switching artifact/view
- [x] agents layer cleanup
  - [x] redesign bash tool
  - [x] model price tracking, move to genai-pricing
  - [x] trace.py and llm.py
  - [x] message store
- [ ] app layer cleanup
- [ ] research layer cleanup

Aug 27
- [x] app layer cleanup
- [ ] research layer cleanup
- [x] dataclasses cleanup

Aug 28
- [x] research layer cleanup
- [x] tests cleanup

Aug 31
- [x] Unify reasoning and service priority configuration
- [x] Bump pydantic-ai to 2.x and type llm.py
- [x] pyprojec.toml, simplify dependencies, package metadata
- [x] Benchmark download cli
- [x] scripts cleanup

Sep 1
- [x] cli
- [x] context compaction
- [x] bash command display

Sep 2
- [x] new compaction algorithm
- [x] Set model retry limit to 3
- Multimodal
  - [x] infra
  - [x] pasting images
  - [x] media in files and web

Sep 3
- [x] Split file_editor tool
- [x] Multimodal
  - [x] run_query
  - [x] run_subagent and extract_rows
  - [x] sample_data
- [x] Rewrite df serialization and spill connector
- [x] Rewrite write_dataframe_async and write_result_table

Sep 4
- [x] Multimodal
  - [x] Test huggingface multimodal datasets
  - [x] Multi-media-items cell
  - [x] Refactor
  - [x] Multi-media-items cell display
  - [x] Audio/Video support -> deferred
  - [x] Detail -> deferred
- app
  - [x] Fix scrolling
  - [x] Fix manual table
  - [x] Copy table with media in output pane
  - [x] Stable colors across parameter selection

Sep 6
- SPARQL
  - [x] core and data layer clean up
- [x] Fix media cells display in TUI
- Output pane
  - [x] Fix arrow key automatically focus on close button
  - [x] Focus ring of item in media collection in output pane

Sep 7
- SPARQL
  - [x] SPARQL connector
  - [x] Data source catalog and `/connect wikidata`
  - [x] Unify data source connection
- Output pane
  - [x] Long text/json cell in output pane
  - [x] Fix images alignment
- [x] Fix `Agent error: status_code: 404, model_name: gpt-5.6-sol, body: {'message': "Item with id 'rs_06adf3bb2187a080006a9f31a7284887d0be062ed07f3a350a' not found.", 'type': 'invalid_request_error', 'param': 'input', 'code': None}`


Sep 8
- [ ] Finish SPARQL and data layer cleanup
  - [ ] "db" cleanup
  - [ ] Neo4j graph extraction
- [ ] Fix input history order
- [ ] Huggingface connect split selection and better url cleaning
- [ ] Authentication

- [ ] Avoid AGENTS.md CLAUDE.md re-read after compaction
- [ ] Merge registry tool variants

- [ ] Show pending turns in output pane
- [ ] Inline artifact citation
- [ ] IMPORTANT: decouple data and rendered format (show unit "cm" while still enabling sorting by value)
- [ ] TUI
  - [ ] Do not auto-scroll when browsing old turns
  - [ ] Onboarding - browser install
- [ ] Open-source LLM (e.g. Fireworks) preset

- v2 features
  - TUI
    - [ ] Bell icon when finished
    - [ ] Bug: Warning sign emoji display width
    - [ ] Session resume
    - [ ] /reconnect
    - [ ] NL tool progress
    - [ ] Schema browser for very large db (1000+ tables/columns)
  - Multimodal
    - [ ] hydrate_media tool?
    - [ ] image/pdf detail level
    - [ ] Multimodal output
  - Data
    - [ ] Provenance
    - [ ] Remote files
    - [ ] Government/academic data
    - [ ] Graph extraction for sparql
  - Subagent
    - [ ] Subagent context reuse
  - Coding
    - [ ] code diff rendering
  - Web browsing
    - [ ] web_fetch tool for static html
    - [ ] Chrome browser, browser resolution
    - [ ] Captcha

  
- [ ] Allowed roots policy
- [ ] Shell messed up after ssh disconnect
- [ ] Check if uv tool install install browser

- [ ] Waiting spinner before Thinking to indicate latency due to low service tier
- [ ] "result" -> "response", Escape go to last viewed response


- [ ] Debug /Users/yanlinf/.tabulaflow/sessions/20260716T222109Z-be2c/trajectories/trajectory.md


- [ ] Kushan: better error message for /connect failure
- [ ] put removed stale tables in workspace in a user-invisible schema rather than deleting

- [ ] View menu location?


- [ ] Context for canonicalization (e.g. pool vs swimming)
- [ ] Offload truncated cell + read_message tool
- [ ] Inlucde table schema for add_canonical_name tool
- [ ] Handle records with empty results or zero-row results
- [ ] One-time subagent tool
- [ ] Partial trajectory when exeption during agent turn

- General
  - [ ] Table readiblity: small table -> readible (e.g. KB, MB, GB), large table -> normalized
  - [ ] Semantic join - cross join
  - [ ] Support interrupting preview loading
  - [ ] Pass db doc on connect for small dbs?
  - [ ] Multimodal data processing in subagent
  - [ ] Disable compression for small dbs?
  - [ ] Enriched with other data in huggingface repo
  
  - [ ] "connect to data" instead of "paste data"
  - [ ] Consider huggingface compatibility when designing export format
  - [ ] Pagination for direct data browsing
- Data/Cell/Query Browser
  - [ ] Support multi-modal data browsing (images, audio, video, etc.)
  - [ ] Query browser - show language and database
  - [ ] Refresh for get_column_json_schema and get_db_document
  - [ ] Pagination for cell browser
  - [ ] /export
  - [ ] /import with auto LLM import

- Scenarios
  - [ ] Data browsing (replace DBeaver)
  - [ ] Multi-source querying on databases
    - [ ] Compare two similar databases
    - [ ] Profile all 152 spider2-snow databases
  - [ ] Public data sources
    - [ ] Huggingface, analyze, preprocessing (replace jupyter notebook)
    - [ ] Wikidata
    - [ ] Government/academic data
  - [ ] Error analysis
  - [ ] Running inference
  - [ ] Semantic operators
  - [ ] Web deep research (replace aisheets)
- Study other open-source projects
  - [ ] Claude code - tool description in system prompt or tool schema?
  - [ ] OpenClaw

- [ ] v2: streaming data support (e.g. auto-updating artifacts like chart for stock price data)

---

===== BELOW IS OUTDATED =====

===== BELOW IS OUTDATED =====

===== BELOW IS OUTDATED =====

---

# tabulaflow

**Min**imalist **T**ext-to-**Q**uery Library

A **Min**imalist **T**ext-to-**Q**uery Library that offers:

📐 **Everything Structured**: All data—including database schemas—is structured and explicitly [defined](tabulaflow/schema.py). No more dealing with complex black-box dictionaries or parsing massive schema strings.

🔍 **Type-safe**: Every method is type-hinted and checked with static type checker mypy.

🧩 **Modular**: Stable platform layers cover data, outputs, and reusable agents, while the research layer contains benchmark adapters, research strategies, and evaluation metrics.

🔌 **Extensible**: Intefaces are designed to be minimal and flexible, without heavy abstractions. You are free to use any agent library to build your own text-to-query agent.

🌐 **Multi-DBMS**: Works with a wide variety of databases including all SQL databases (e.g. PostgreSQL, MySQL, SQLite) supported by sqlalchemy as well as graph databases like Neo4j.

⚡ **First-class Asyncio Support**: The library is built with asyncio with built-in rate limiting and maximum concurrency control.

🧠 **Built for Researchers**: Key features:
- Out-of-the-box support for BIRD-SQL, Beaver, Spider 2.0 and ARCS
- Equivalent re-implementation of official leaderboard metrics
- Re-implementation of state-of-the-art agents on leaderboards
- Lightning-fast inference and evaluation using asyncio
- Tracing with langfuse and other LLM observability platforms
- Local trajectory tracing
- Agent tool call and token usage tracking
- Support for interactive task with user simulator
- Schema compression for database with thousands of tables

## 🚀 Quick Start

### Installation

First, follow the [Development](#-development) section to install the library. Next, follow the [Dataset Setup](#-dataset-setup) section to download the datasets you want to use.

### Using `tabulaflow` as a library

```python
import asyncio
from tabulaflow.research.agents import SchemaLinkingAgent, BasicAgentConfig
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx
from tabulaflow.research.pipelines import run_agent_async, populate_exec_results_async, evaluate_async


async def main() -> None:
    dataloader = BirdSQLDatasetLoader()
    # dataset includes the text-to-query tasks and the database connectors
    dataset = await dataloader.get_split_async("dev")
    dataset.tasks = dataset.tasks[:3]

    # define the model arguments
    # the `run_model` function below uses this to construct a separate model instance for each sample to avoid race condition
    config = BasicAgentConfig(llm="openai-responses:gpt-4.1-mini", schema_formatter="sql_basic")
    # run the model on the dataset using async coroutines
    result = await run_agent_async(SchemaLinkingAgent, config, dataset, batch_size=2)
    print(result.tasks[0].pred_query.query)
    # SELECT MAX(CASE WHEN "Enrollment (K-12)" > 0 THEN "Free Meal Count (K-12)" / "Enrollment (K-12)" ELSE NULL END) AS Highest_Eligible_Free_Rate
    # FROM frpm
    # WHERE "County Name" = 'Alameda' AND "Enrollment (K-12)" > 0;
    print()
    print(result.aggregated_inference_metrics)
    # {'latency_seconds': {'avg': 7.4654, ...

    # populate exec results
    result = await populate_exec_results_async(result, dataset, batch_size=2, timeout=30)

    # evaluate execution accuracy
    metrics = [BirdSQLEx()]
    result_with_metrics = await evaluate_async(result, metrics, batch_size=2)
    print(result_with_metrics.aggregated_eval_metrics)
    # {'bird_sql_ex': {'avg': 0.3333}}


if __name__ == "__main__":
    asyncio.run(main())

```

### Running experiments with provided scripts

We also provide the [run_model.py](tabulaflow/run_model.py) and [evaluate.py](tabulaflow/evaluate.py) scripts for convenience:

```bash
uv run tabulaflow/research/pipelines/run_agent.py --agent schema_linking --dataset bird-sql --llm "openai-responses:gpt-4o-mini" --output-dir output/test/
uv run tabulaflow/research/pipelines/populate_exec_results.py output/test/
uv run tabulaflow/research/pipelines/evaluate.py output/test/
```

## Project Structure

```
tabulaflow/research
├── agents/                 # text-to-query research strategies
├── benchmarks/             # benchmark dataset adapters
├── metrics/                # evaluation metrics and aggregators
├── preprocessing/          # schema and question preprocessing
├── tools/                  # research-only agent tools
├── pipelines/              # experiment orchestration and CLIs
├── types.py                # research data models
├── reporting.py            # readable reports and persisted outputs
├── query_execution.py            # execution of research query objects
├── query_analysis.py       # static query analysis
├── ambiguity.py            # ambiguity ordering and identifiers
└── observability.py        # research tracing policy and instrumentation
```

## 📚 Dataset Setup

Benchmark data is installed once for all splits under
`~/.tabulaflow/benchmarks`:

```bash
tabulaflow benchmark list
tabulaflow benchmark download cypherbench
```

Loading a missing benchmark fails with the exact download command instead of
starting network activity inside an experiment. Downloads are verified and
installed atomically. Large downloads show byte progress and resume from the
hidden staging directory after interruption.

Currently, the following datasets are supported:

| Dataset | Key | Splits |
|---------|-----|------------------|
| BIRD-SQL | `bird-sql` | `dev`, `dev_20251106`, `train` |
| Spider 2.0 Snow | `spider2-snow` | `test` |
| Spider 2.0 Lite | `spider2-lite` | `test` |
| Spider 2.0 DBT | `spider2-dbt` | `test` |
| Beaver | `beaver` | `test` |
| ARCS | `arcs` | `test`, `test_unsampled` |
| AMBROSIA-S | `ambrosia-s` | `test`, `few_shot_examples` |
| CypherBench | `cypherbench` | `test`, `train` |

### BIRD-SQL

```bash
tabulaflow benchmark download bird-sql
```

### Spider 2.0

Download the static benchmark data and local databases:

```bash
tabulaflow benchmark download spider2-lite
tabulaflow benchmark download spider2-snow
tabulaflow benchmark download spider2-dbt
```

Snowflake-backed tasks require a Spider 2.0 Snowflake account. Configure it with:

```bash
export SF_USER="your_username"
export SF_PASSWORD="your_password"
export SF_ACCOUNT="your_account"
```

BigQuery-backed tasks require the standard Google Cloud application credentials.

### Beaver

```bash
tabulaflow benchmark download beaver
tabulaflow benchmark start beaver
```

`tabulaflow benchmark stop beaver` stops both MySQL containers without deleting
their initialized databases.

### AMBROSIA-S

```bash
tabulaflow benchmark download ambrosia-s
```

### CypherBench

```bash
tabulaflow benchmark download cypherbench
tabulaflow benchmark start cypherbench
tabulaflow benchmark start cypherbench --split train
```

`tabulaflow benchmark stop cypherbench` stops the test databases without
deleting their imported graph data. Pass `--split train` to stop the train
databases instead.

### ARCS

ARCS does not yet have a canonical downloadable artifact. Running
`tabulaflow benchmark download arcs` shows the required local layout.


## 💻 Development

### Dependencies

We use `uv` to manage dependencies (the modern replacement of pip/conda/poetry).

First, run `uv --version` to ensure that [uv](https://docs.astral.sh/uv/getting-started/installation/) is installed.

After cloning the repository, run `uv venv` to create a local venv at `.venv/`. Then run `make sync` (which runs [`uv sync`](Makefile#L3) behind the scenes) to install the dependencies into the venv.

To add a new dependency, run `uv add <dependency>`. The `pyproject.toml` file and `uv.lock` should be committed to the repository.

To run a python script, run `uv run <script.py>` (this is the preferred way but you can also either activate the venv using `source .venv/bin/activate` first or directly run the python binary `.venv/bin/python <script.py>`).

### Environment variables

We use `direnv` to manage environment variables.

First, run `direnv --version` to ensure that [direnv](https://direnv.net/) is installed.

Next, create a `.envrc` file in the root directory and add the environment variables to it. This file should NOT be committed to the repository.

```bash
export OPENAI_API_KEY="your_openai_api_key"

# for Spider 2.0 (optional)
export SF_USER="your_snowflake_username"
export SF_PASSWORD="your_snowflake_password"
export SF_ACCOUNT="RSRSBDK-YDB67606"

# for tracing (optional)
export PHOENIX_COLLECTOR_ENDPOINT="your_phoenix_collector_endpoint"
export PHOENIX_API_KEY="your_phoenix_api_key"
export LANGFUSE_HOST="your_langfuse_host"
export LANGFUSE_PUBLIC_KEY="your_langfuse_public_key"
export LANGFUSE_SECRET_KEY="your_langfuse_secret_key"
```

Then, run `direnv allow` to load the environment variables. In the future, the env vars will be loaded automatically when you enter the directory.

### Utility commands

We use `make` to manage a few common commands we frequently use (see [`Makefile`](Makefile) for their definitions):

```bash
make format      # format and lint
make mypy        # type check with mypy
make test-bird-schema-linking  # test schema_linking
make sync        # sync the dependencies in pyproject.toml into the venv (e.g. when others have updated the dependencies)
```




## TODOs

- [ ] Rename db_connector to connectors?
- [ ] Try OpenAI plain text tool?
- [ ] Analyze spider2-snow:
  - unfinished period like the current year to a finished one
  - If the identifier name itself contains a double quote, escape it by using **two double quotes**. To query a table named `Client"Data`, write: `SELECT * FROM "Client""Data"`
- [ ] bash tool for dbt agent
- [ ] Answer asking for number but instead pred query returns separate rows - analyze trivial errors
- [ ] Randomization for ensembling
- [ ] Update spider2-lite instructions
  - [ ] Quoting identifiers for snowflake?
  - [ ] Check not executable queries (both spider2-snow and spider2-lite)
- [ ] Revise db_summarizer prompt - "used for efficient navigation and SQL writing by SQL experts"
- [ ] schema linking for schema_discovery
- [ ] Code edit tool for editting complex queries
- [ ] non-empty ratio
- [ ] partial trajectories on error
- [ ] column descriptions all used

- [ ] ARCS
  - [ ] "lengthen over-specified questions" in intro (emphasize that questions in existing benchmarks are too long)
  - [ ] Section on ease of use in paper and website
  - [ ] Rationale for multiple resolution sampling - prevent LLM from guessing
  - [ ] Data sheet
  - [ ] Remove `extra_info` in ARCS data
  - [ ] Update website layout with top bar
  - [ ] Set schema formatter to sql_basic in scripts
  - [ ] Include example ambiguity in BIRD-SQL to showcase importance
    - bird-sql_dev_20240627_87

### Release test

- [ ] Remove cache
- [ ] Schema caching
- [ ] all gold queries executable
- [ ] Test ARCS
- [ ] Test BIRD
- [ ] Test Spider 2.0


---

Contact: yanlin@megagon.ai

---
