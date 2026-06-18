"""CLI chat agent for interactive query chat."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Iterable
import json
import logging
from pathlib import Path
import re
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

from pydantic_ai.models.openai import OpenAIChatModelSettings

from tabulaflow.toolhub.message_store import (
    MESSAGE_THRESHOLD_CHARS,
    MessageStore,
    MessageStoreCapability,
    ScopedMessageStore,
    make_snippet,
)
from tabulaflow.toolhub.web_browser import (
    BROWSER_TOOL_NAMES,
    SNAPSHOT_SNIPPET_THRESHOLD_CHARS,
    snapshot_snippet,
)
from tabulaflow.core.llm import make_agent
from tabulaflow.chat.result import ChatResult, ChatResultRecord
from tabulaflow.chat.events import (
    ChatEvent,
    ColumnsReturned,
    AnswerDelta,
    Completed,
    Failed,
    Finished,
    NarrationDelta,
    RowsReturned,
    ThinkingDelta,
    ToolFinished,
    ToolOutcome,
    ToolProgress,
    ToolStarted,
    UsageUpdated,
)

if TYPE_CHECKING:
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelMessage, ToolReturnPart

    from tabulaflow.core.db_connector.db_registry import DBRegistry
    from tabulaflow.core.db_connector.sql_conn import SQLConnector
    from tabulaflow.core.types import Usage
    from tabulaflow.toolhub import (
        AddCanonicalNameTool,
        ConnectDataSourceTool,
        CreateDatasetTool,
        ExecuteBashTool,
        ExtractRowsFromDocumentsTool,
        FileEditorTool,
        QueryHistory,
        QueryRecord,
        RegistryGetColumnJsonSchemaTool,
        RegistryGetDBDocumentTool,
        RegistryGetTableSchemaTool,
        RegistryRunQueryTool,
        RegistryTransferRecordTool,
        RenderPlotextChartTool,
        RunSubagentForEachRowTool,
        WebBrowserTool,
    )

logger = logging.getLogger(__name__)

_QUERY_REF_RE = re.compile(r"\[\[record:(Q\d+)(?::([^\]]+))?\]\]")


SYSTEM_PROMPT = """\
You are tabulaflow, built by Megagon Labs.
You are an interactive tabular data assistant that answers the user's questions about their data.
You are an agent - please keep going until the task is solved.
If the question is ambiguous, choose the most natural interpretation and proceed. Only ask for clarification when you are truly blocked.
Be THOROUGH. Make sure you have the FULL picture before finishing. Use additional tool calls as needed.

<communicating_with_the_user>
CRITICAL: The user should feel as if they are directly interacting with their original dataset (e.g., "the GLUE dataset", "the IMDB dataset"). NEVER expose internal implementation details (e.g. database alias, connector, etc.) in your responses unless explicitly asked by the user:
- Refer to datasets by their original source name (e.g., "the GLUE MNLI dataset from Hugging Face", "your CSV file sales.csv").
- When describing what data is available, talk about the dataset's tables/splits and columns — not about database internals.
- Be concise and direct: match the level of detail to the task's complexity, address only what's asked, and add no extra explanation or summary unless requested — a 1-3 sentence answer is often enough for simple tasks.
- Your response is rendered in a terminal. Do not use markdown bold (**) or other rich formatting — use plain text only.
</communicating_with_the_user>

<presenting_results>
- Present data tables or tabular results using the format below when applicable for better readability.
  - You can only reference `run_query` results. To present data that isn't one yet (e.g. values you computed, or browser/subagent output), write it into `workspace` and `SELECT` it first.
- End every answer with a `---` on its own line: result references go above it, then `---`, then your plain-language answer. Only text AFTER the `---` reaches the user; text before it is intermediate narration. Always include the `---`, even with no references.
    - Reference a result as `[[record:Q<id>:<label>]]` (e.g. `[[record:Q3:num_players]]`); every reference needs a short label describing the table (e.g. `players`, `revenue_by_month`), or `result` if unsure — never the record id.
    - Example (with a table):
      [[record:Q3:num_players]]
      ---
      There are 42 players.
    - Example (no table):
      ---
      The connection succeeded.
- Do not reference every query you ran. Select only the most relevant results with minimal overlap.
- For count questions, if you are already showing the full entity list as one table, do not present a separate single-value count table.
- Our data browser handles large tables and long cell values automatically: present the full result (run `SELECT *` without `LIMIT`) and reference that record — no need to truncate.
- Our data browser supports viewing images, audio, videos and pdfs, so you can show them by including binary data in the table.
</presenting_results>

<data_model>
How data is organized — the vocabulary used throughout:
- Every data source is registered under an alias; the `db_alias` argument selects which source a tool call targets. Aliases are application-level handles, not SQL catalog/schema names.
- Tables in different aliases cannot be joined directly. To join across sources, first move the relevant tables into `workspace` with `transfer_record`, then join them there.
- Kinds of sources:
  - Connected sources — data the user or you connected, read-only: local files, databases, or HuggingFace datasets.
  - `workspace` — an always-available, writable scratch database for intermediate and transformation tables; tables in it persist for the whole session.
  - Datasets you create — `create_dataset` consolidates scattered local files into a named, queryable database (writable during the session). Session-scoped: not saved across sessions.
- `workspace` and any dataset you create are DuckDB; write their queries in DuckDB SQL. Single-quoted string literals do NOT process backslash escapes, so regex patterns use single backslashes: `regexp_extract_all(x, '\[(.*?)\]', 1)`, not `'\\['`.
</data_model>

<loading_data>
Load a source you can point at (a file, database, or HuggingFace dataset) into a queryable form. (Extracting structured entities from unstructured content is a separate task — see <collecting_records>.) Pick the lightest option that fits the goal:
- One-off read of a file (only choose this if it is truly one-off and you don't want user to see it in the data explorer) → create nothing; read it inline with `run_query` against `workspace`, e.g. `SELECT avg(score) FROM read_csv_auto('output/results.csv')`.
- Query one file multiple times, or expose it to user in `workspace` → load it into a `workspace` table once: `CREATE TABLE runs AS SELECT * FROM read_csv_auto('output/results.csv')`.
- Expose an existing, finished source for the user to keep querying as a separate source to the `workspace` → `connect_data_source` (read-only): a local file (CSV/TSV/JSON/Parquet/Excel), a local database file (SQLite/DuckDB), a database URL, or a HuggingFace dataset. If a database URL needs a password you don't have, ask the user to connect it with `/connect <url>`.
- Consolidate scattered local files into one named dataset the user can query this session → `create_dataset`, then build its tables with `run_query` reading the files, e.g. `CREATE TABLE runs AS SELECT * FROM read_csv_auto('output/**/*.csv', union_by_name=true)` (also `read_parquet`/`read_json_auto`); add more during the session.
</loading_data>

<task_modes>
Most user requests fall into one of three task modes — answering a question, transforming data, or extracting structured data. Identify which applies and follow the matching guidance below.

<answering_questions>
- Answer the user's question by running database queries; this mode is read-only — no writes needed.
- If the ambiguity is consequential and the plausible interpretations are few, cover them all — present one table per interpretation rather than committing to one.
- Pay attention to whether the user is asking for one table or multiple tables.
- Do not include the execution results or the query in your final user-facing response as they will be automatically rendered in a separate view for all referenced records (see <presenting_results>).
- For huggingface datasets that exceed 500MB, the dataset is loaded as a view and a materialized sample table is created. Use the sample table unless explicitly requested by the user.
</answering_questions>

<transforming_data>
Use `workspace` for data transformation and semantic operations (e.g., LLM-based filtering, joining, or extraction); never modify the original tables in-place.
- Use `transfer_record` to move data into or out of `workspace`. To transfer a full table, run `SELECT * FROM <table>` without `LIMIT`, then transfer that `record_id`.
- Prefer `run_subagent_for_each_row` over fuzzy regex matching or LIKE-based SQL for semantic operations (classifying free text, matching names with naming variations, extracting sentiment). See <concurrent_task_handling>.
</transforming_data>

<collecting_records>
- When asked to build a structured set of records (e.g. listing all records that satisfy a condition, or pulling rows out of documents/web pages), ensure completeness: gather the full set rather than a sample, and do not stop early. Do this work in `workspace` (the fan-out and mining tools work only there).
- When there are multiple alternative sources, choose the most commonly used one.
- If full completeness is not achievable, deliver what you collected and tell the user what is missing and why.
- For large-scale or context-heavy collection, decompose the work into independent subtasks and run them in parallel with `run_subagent_for_each_row` rather than going over each item one by one yourself — this avoids context bloat and reduces latency (see <concurrent_task_handling>).
- To turn unstructured content into structured rows — documents you've loaded into `workspace` (PDFs, long text; see <loading_data>) or web pages — use the most efficient approach that still guarantees completeness and accuracy:
  - When the target data follows a simple, consistent textual pattern, use regex parsing, falling back to `extract_rows_from_documents` if the pattern proves unreliable.
  - When the data is irregularly formatted or requires semantic understanding to extract, use LLM-based `extract_rows_from_documents`.
- For data on the web, first gather the pages with the `browser_*` tools (prefer direct URLs over search engines; default to duckduckgo.com if you must search), then extract as above.
- Normalize collected values so the dataset is clean and queryable:
  - Numeric values: store in a numeric column (never as strings) and convert to one consistent unit, encoding that unit in the column name (e.g., `price_usd`, `weight_kg`).
  - String values: normalize to a canonical form where possible — consistent casing, spelling, and format; use `add_canonical_name` to unify entity variants across rows.
</collecting_records>
</task_modes>

<exporting_data>
Saving a result to a file is the only way to durably keep data, since datasets and `workspace` don't survive the session. Export with DuckDB COPY via `run_query`, against a writable database (a dataset or `workspace`, never a read-only source):
- `COPY (SELECT ...) TO '<path>' (FORMAT parquet)`
- `COPY (SELECT ...) TO '<path>' (FORMAT csv, HEADER)`
- `COPY (SELECT ...) TO '<path>' (FORMAT json)`
The SELECT may read source files inline. Match FORMAT to the file extension the user asked for. For xlsx / markdown / other formats, COPY to parquet or csv first, then convert with the shell.
</exporting_data>

<concurrent_task_handling>
When a task decomposes into many similar, independent sub-tasks (one per row, entity, date, URL, etc.), do NOT loop through them in your own context. Lay the sub-tasks out as rows of a `workspace` table and process them concurrently with `run_subagent_for_each_row` — each row gets its own subagent running in parallel, and their intermediate work never enters your context (only a summary returns; per-row failures land in `_subagent_exception` / `_subagent_trajectory`). See the tool description for task setup and the optional capability flags.
- The subagent sees only its rendered `task_instruction`, not this conversation — encode any requirements the user mentioned into it.
- Ambitious tasks can be decomposed across multiple levels: a subagent's task can itself fan out further sub-tasks with `run_subagent_for_each_row` (set `enable_nested_subagents=True`). Reach for this when one level of rows is too coarse — break the task into a tree of sub-tasks rather than one flat sweep.
- Treat it as expensive. For large tables (>= 100 rows) or when the task is complex (e.g. when involving web browsing), run on a sampled subset first, verify, then apply to the full table. For a small number of simple tasks, skip the sampling step and run directly — the extra pass only hurts latency and user experience.
- Decide per task whether plain SQL rules suffice or a subagent is needed; combine both when different parts of a table need different methods.
</concurrent_task_handling>

<long_message_offloading>
To keep your context lean, every browser response is mirrored into the `_internal.messages(message_id, kind, tool_name, tool_call_id, created_at, char_len, content)` table of the `workspace` database, and very long user prompts and tool responses are offloaded before they reach you: their full content stays in that table and you can process it progammtically or hand it to a subagent.
- For responses that carry a leading marker line `[message_id=M<n>]`, you can fetch the full content back with `run_query(db_alias="workspace", "SELECT content FROM _internal.messages WHERE message_id='M<n>'")`.
- To hand a long message to a subagent without pulling its full content into your own context, leave it offloaded and JOIN `_internal.messages` in a workspace-targeted `task_query` so the content arrives as a column — e.g. `SELECT m.message_id, m.content AS chunk FROM _internal.messages m WHERE m.message_id = 'M7'`; the per-row `task_instruction` then references it as `{{ chunk }}`.
- Offloading also applies one level down, but only to subagents that can spawn nested subagents (`enable_nested_subagents=True`): their own long prompts and tool responses are offloaded the same way and fetched back via `run_query`, so deep multi-level decompositions never overflow context at any level. Leaf subagents (no nesting) are not offloaded.
</long_message_offloading>

<tool_calling>
General:
- Try to batch tool calls if they can be run in parallel to reduce latency.

Paths, the shell, and files:
- Relative paths — in `run_query` (reads and `COPY`) and in the shell — resolve against the user's project directory. Keep intermediate files in the scratch directory (OUTSIDE the project); do NOT write to the project directory unless the user explicitly asks you to save or export there. Reference scratch files by their absolute path (given in <session_paths>); `$SCRATCH` is a shell variable and does NOT expand in SQL, so put that literal absolute path in the query.
- Shell (`execute_bash`): use only when plain SQL can't gather or transform the data (heterogeneous formats, custom parsing, pandas); it has network access and can explore the project's files (`ls`/`find`/`head`). Stage intermediate files as Parquet in the scratch directory, then read them back with `read_parquet('<scratch abs path>')`.
- File editor (`file_editor`): `view` / `write_file` / `str_replace` for text files, paths relative to the project. Use it to author or edit files the user wants kept in the project (e.g. dbt models, scripts) — not to stage intermediate data (that goes to scratch via DuckDB/shell). Prefer it over shell `sed`/`echo` for writing or editing files.
- Before running any destructive or irreversible command (deleting or overwriting files, changing system state), stop and ask the user to confirm first.

Inspecting schemas and data:
- For most databases, call `get_db_document` to understand the database structure.
- For SQL databases, you may use `get_table_schema` to get the schema of relevant tables before constructing the query.
- For SQL databases, you may use `get_column_json_schema` to inspect the internal structure of semi-structured columns (e.g. VARIANT, OBJECT, ARRAY, JSON, JSONB).
- You may use `run_query` to run exploratory queries or inspect some sample values to determine the data format if necessary.

Writing database queries:
- Ensure you have collected enough information and fully understand the database structure before composing the task query.
- Build complex queries with multiple CTEs incrementally.
- Format the query for readability and avoid long one-line queries.

Visualization:
- Call `render_chart` with a Vega-Lite JSON spec if the result lends itself to a chart (e.g. counts by category, trends over time, distributions).
- `render_chart` accepts an optional `record_id`. Omit it to chart the most recent query result, or pass a prior `record_id` if you want to visualize an earlier query.
- Do NOT render charts for single-row results, heterogeneous tables, or when the user only asks for a specific value.
- Supported marks: bar, line, point, rect. Only simple specs with x/y encoding are supported.
- Prefer bar for categorical comparisons, line for time series, point for correlations.
</tool_calling>

<plan_mode>
If the user says "plan first" or "discuss first", present a plan and wait for approval before executing.
- Multiple lightweight read-only tool calls are allowed to undertand the data, task and ground the plan.
- Do NOT run heavy or stateful tools yet (e.g. `run_subagent_for_each_row`, `transfer_record`, `render_chart`, or any writes to `workspace`).
</plan_mode>
""".strip()


# Appended to the (static) system prompt per session when the host provides the project
# and scratch dirs, so the agent has their absolute paths without spending a shell call to
# discover them. Kept at the tail so the large static prefix still prompt-caches.
_SESSION_PATHS_BLOCK = """

<session_paths>
- Project directory — the shell's working dir; relative paths in the shell and in `run_query` resolve here: {project_dir}
- Scratch directory — for intermediate files; use this absolute path when referencing scratch files in SQL (also available as `$SCRATCH` in the shell): {scratch_dir}
</session_paths>"""


# Fixed reasoning effort for the subagent-backed fan-out / extraction tools — an
# internal detail of the chat lib, independent of the (app-configured) interactive
# agent's ``reasoning_effort``.
_SUBAGENT_REASONING_EFFORT: Final = "medium"

# Reasoning config shared by the subagent-backed tools (the fan-out / extraction
# tools). ``run_subagent_for_each_row`` additionally requests reasoning summaries.
_SUBAGENT_MODEL_SETTINGS = OpenAIChatModelSettings(
    openai_service_tier="priority",
    openai_reasoning_effort=_SUBAGENT_REASONING_EFFORT,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class _Toolset:
    """Typed bundle of agent tools (internal to ``ChatAgent``)."""

    run_query: RegistryRunQueryTool
    get_db_document: RegistryGetDBDocumentTool
    get_column_json_schema: RegistryGetColumnJsonSchemaTool
    get_table_schema: RegistryGetTableSchemaTool
    transfer_record: RegistryTransferRecordTool
    # The fan-out tools are bound to the session workspace (the only DB they may
    # read from and write to); ``None`` when the agent runs without a workspace.
    run_subagent_for_each_row: RunSubagentForEachRowTool | None
    extract_rows_from_documents: ExtractRowsFromDocumentsTool | None
    add_canonical_name: AddCanonicalNameTool
    render_chart: RenderPlotextChartTool
    web_browser: WebBrowserTool
    # Host-facing tools; ``None`` when the app didn't supply the dirs they need.
    create_dataset: CreateDatasetTool | None
    connect_data_source: ConnectDataSourceTool | None
    bash: ExecuteBashTool | None
    file_editor: FileEditorTool | None


@dataclass
class ChatAgent:
    """Streaming agent for interactive database chat."""

    registry: DBRegistry
    model: str
    # Reasoning effort for the interactive agent (OpenAI models only):
    # minimal | low | medium | high. Required — the app owns the default (its
    # ``--reasoning-effort`` option), as it does for ``model``. Mutable at runtime via
    # ``set_reasoning_effort`` (peer of ``model``/``set_model``); the subagent fan-out
    # tools keep their own fixed effort (``_SUBAGENT_REASONING_EFFORT``).
    reasoning_effort: str
    # Host-supplied instructions appended to the baseline prompt — a persona, domain
    # guidance, or frontend-specific phrasing (e.g. slash-command vocabulary). ``None``
    # (default) uses the baseline alone. Composed between the static prefix and the
    # session-paths tail (see ``_compose_system_prompt``), so the large prefix still
    # prompt-caches; keep it stable across a session's turns. A full prompt replacement
    # is intentionally not offered: the baseline ``SYSTEM_PROMPT`` is half of a contract
    # with this module's tools and citation parser, so callers extend rather than swap it.
    extra_instructions: str | None = None
    # Where to persist conversation + subagent trajectories. ``None`` (default)
    # disables all trajectory persistence — set a dir to enable it. Servers leave it
    # off (avoids per-turn disk I/O and cross-conversation clobbering of the single
    # ``trajectory.md``); a single interactive session passes a dir.
    trajectory_log_dir: Path | None = None
    # The session workspace — a SQL scratch DB used to spill query-result DataFrames,
    # offload long messages, and back canonical-name resolution. ``None`` (default)
    # runs in-memory with those persistence features off.
    workspace: SQLConnector | None = None
    # The directory the app was launched from (the user's project, where source data
    # lives) and the agent's transient working area for staging intermediate files.
    # ``None`` (default, e.g. server contexts) disables the host-facing shell/dataset
    # tools that depend on them. Wired in by the app from ``RuntimePaths``.
    project_dir: Path | None = None
    scratch_dir: Path | None = None
    # Directory under which agent-created writable datasets are materialized. ``None``
    # (default, e.g. server contexts) omits the ``create_dataset`` tool. Wired in by the app.
    data_dir: Path | None = None
    last_usage: Usage | None = None
    _message_history: list[ModelMessage] = field(init=False, default_factory=list)
    _system_prompt: str = field(init=False, default=SYSTEM_PROMPT)
    _pydantic_ai_agent: Agent[None, str] | None = field(init=False, default=None)
    _query_history: QueryHistory = field(init=False)
    _message_store: MessageStore = field(init=False)
    _main_scope: ScopedMessageStore = field(init=False)
    _tools: _Toolset = field(init=False)
    _running: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        from tabulaflow.toolhub import QueryHistory

        self._query_history = QueryHistory(spill_connector=self.workspace)
        self._message_store = MessageStore()
        self._main_scope = self._message_store.scoped("main")
        subagent_dir = self.trajectory_log_dir / "subagents" if self.trajectory_log_dir is not None else None
        self._tools = self._build_tools(subagent_dir)
        if self.workspace is not None:
            self._message_store.attach_connector(self.workspace)
            self._tools.add_canonical_name.attach_connector(self.workspace)
        self._system_prompt = self._compose_system_prompt()
        self._build_agent()

    def _compose_system_prompt(self) -> str:
        """Assemble the agent's instructions: the baseline ``SYSTEM_PROMPT``, then any
        host ``extra_instructions``, then the session-paths tail (when the project and
        scratch dirs are known). The ordering keeps the large static prefix first so it
        prompt-caches, and the per-session paths last."""
        parts = [SYSTEM_PROMPT]
        if self.extra_instructions:
            parts.append(self.extra_instructions.strip())
        if self.project_dir is not None and self.scratch_dir is not None:
            parts.append(
                _SESSION_PATHS_BLOCK.format(project_dir=self.project_dir, scratch_dir=self.scratch_dir).strip()
            )
        return "\n\n".join(parts)

    def _build_tools(self, subagent_dir: Path | None) -> _Toolset:
        """Construct the agent's toolset, wiring in the shared query history and
        message store. ``subagent_dir`` (if set) is where subagent trajectories land."""
        from tabulaflow.core.formatters.sql_ddl import SQLDDLSchemaFormatter
        from tabulaflow.modulehub.db_summarizer import DBSummarizer
        from tabulaflow.toolhub import (
            AddCanonicalNameTool,
            ConnectDataSourceTool,
            CreateDatasetTool,
            ExtractRowsFromDocumentsTool,
            FileEditorTool,
            RegistryGetColumnJsonSchemaTool,
            RegistryGetDBDocumentTool,
            RegistryGetTableSchemaTool,
            RegistryRunQueryTool,
            RegistryTransferRecordTool,
            RenderPlotextChartTool,
            RunSubagentForEachRowTool,
            WebBrowserTool,
        )

        # The fan-out tools operate on the workspace only: sub-tasks are laid out
        # as workspace tables and results written back there (user data reaches
        # them via transfer_record). Without a workspace they are disabled.
        run_subagent_for_each_row = None
        extract_rows_from_documents = None
        if self.workspace is not None:
            run_subagent_for_each_row = RunSubagentForEachRowTool(
                self.workspace,
                registry=self.registry,
                message_store=self._message_store,
                model_settings=OpenAIChatModelSettings(
                    openai_service_tier="priority",
                    openai_reasoning_effort=_SUBAGENT_REASONING_EFFORT,
                    openai_reasoning_summary="detailed",
                ),
                store_metadata=True,
                trajectory_log_dir=subagent_dir,
            )
            extract_rows_from_documents = ExtractRowsFromDocumentsTool(
                self.workspace,
                model_settings=_SUBAGENT_MODEL_SETTINGS,
                trajectory_log_dir=subagent_dir,
            )

        return _Toolset(
            run_query=RegistryRunQueryTool(self.registry, history=self._query_history, enable_refresh=True),
            get_db_document=RegistryGetDBDocumentTool(
                self.registry,
                db_summarizer_cls=DBSummarizer,
                model_settings={"openai_service_tier": "priority"},
                enable_refresh=True,
            ),
            get_column_json_schema=RegistryGetColumnJsonSchemaTool(self.registry),
            get_table_schema=RegistryGetTableSchemaTool(self.registry, SQLDDLSchemaFormatter(), enable_refresh=True),
            transfer_record=RegistryTransferRecordTool(self.registry, self._query_history),
            run_subagent_for_each_row=run_subagent_for_each_row,
            extract_rows_from_documents=extract_rows_from_documents,
            add_canonical_name=AddCanonicalNameTool(
                model_settings=_SUBAGENT_MODEL_SETTINGS,
                trajectory_log_dir=subagent_dir,
            ),
            render_chart=RenderPlotextChartTool(history=self._query_history),
            web_browser=WebBrowserTool(),
            create_dataset=(CreateDatasetTool(self.registry, self.data_dir) if self.data_dir is not None else None),
            connect_data_source=(
                ConnectDataSourceTool(self.registry, self.data_dir) if self.data_dir is not None else None
            ),
            bash=self._build_bash_tool(),
            file_editor=(FileEditorTool(str(self.project_dir)) if self.project_dir is not None else None),
        )

    def _build_bash_tool(self) -> ExecuteBashTool | None:
        """Build the shell tool, or ``None`` when the host dirs aren't available.

        Runs commands in the user's project dir, exposes the session scratch dir as
        ``$SCRATCH``, and guards against catastrophic commands via the denylist."""
        if self.project_dir is None or self.scratch_dir is None:
            return None
        import os
        import shlex

        if os.name != "posix":
            # The shell tool is POSIX-only (PTY-based). Omit it so the rest of the app
            # still runs on Windows; the agent just loses shell-based gather/transform.
            logger.warning("execute_bash is unavailable on this platform; the agent runs without a shell tool")
            return None

        # The shell tool runs with cwd=project_dir, while in-process run_query/DuckDB
        # resolve relative paths against the live process cwd. The "relative = project
        # dir" design requires these to be equal — assert it loudly rather than silently
        # reading/writing the wrong files if something ever changed cwd.
        if os.path.realpath(os.getcwd()) != os.path.realpath(self.project_dir):
            raise RuntimeError(
                f"process cwd ({os.getcwd()!r}) != project_dir ({str(self.project_dir)!r}); "
                "relative-path resolution would diverge between the shell tool and run_query."
            )

        from tabulaflow.toolhub import ExecuteBashTool
        from tabulaflow.toolhub.shell_guard import dangerous_command_reason

        return ExecuteBashTool(
            working_dir=str(self.project_dir),
            init_commands=[f"export SCRATCH={shlex.quote(str(self.scratch_dir))}"],
            command_filter=dangerous_command_reason,
        )

    @property
    def query_history(self) -> QueryHistory:
        """The live query history — results the agent's answers reference."""
        return self._query_history

    def set_model(self, model: str) -> None:
        """Update the model and rebuild the bound runtime agent. Use this rather
        than assigning ``self.model`` directly — a bare assignment skips the rebuild."""
        if self.model == model:
            return
        self.model = model
        self._build_agent()

    def set_reasoning_effort(self, reasoning_effort: str) -> None:
        """Update the interactive agent's reasoning effort and rebuild the bound
        runtime agent. Use this rather than assigning ``self.reasoning_effort``
        directly — a bare assignment skips the rebuild. (Affects the main agent only;
        subagent tools stay on ``_SUBAGENT_REASONING_EFFORT``.)"""
        if self.reasoning_effort == reasoning_effort:
            return
        self.reasoning_effort = reasoning_effort
        self._build_agent()

    def note_event(self, description: str) -> None:
        """Make the agent aware of a host/app event (typically a user action — e.g.
        connecting a data source, uploading a file) by appending it to the
        conversation. The caller supplies ``description`` in its own domain terms;
        the agent owns how it enters the conversation: a system-tagged turn in the
        message history.

        Events go in the message history, not the system instructions, on purpose:
        the instructions stay static so the model's large prompt prefix is fully
        prompt-cached, and each event is a pure append to the history tail — itself
        cache-friendly. The message also gives the agent temporal awareness (it
        knows the event *just* happened)."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        self._message_history.append(ModelRequest(parts=[UserPromptPart(content=f"[system: {description}]")]))

    async def aclose(self) -> None:
        """Release session-scoped resources — currently the persistent shell session."""
        if self._tools.bash is not None:
            await self._tools.bash.close()

    def _build_agent(self) -> None:
        from tabulaflow.toolhub.run_subagent_for_each_row import ReleaseBrowserBeforeFanout

        fanout_tools = [
            tool.as_pydantic_ai_tool()
            for tool in (self._tools.run_subagent_for_each_row, self._tools.extract_rows_from_documents)
            if tool is not None
        ]
        host_tools = [
            tool.as_pydantic_ai_tool()
            for tool in (
                self._tools.create_dataset,
                self._tools.connect_data_source,
                self._tools.bash,
                self._tools.file_editor,
            )
            if tool is not None
        ]
        self._pydantic_ai_agent = make_agent(
            self.model,
            tools=[
                self._tools.run_query.as_pydantic_ai_tool(),
                self._tools.get_db_document.as_pydantic_ai_tool(),
                self._tools.get_table_schema.as_pydantic_ai_tool(),
                self._tools.get_column_json_schema.as_pydantic_ai_tool(),
                self._tools.transfer_record.as_pydantic_ai_tool(),
                *fanout_tools,
                *host_tools,
                self._tools.add_canonical_name.as_pydantic_ai_tool(),
                self._tools.render_chart.as_pydantic_ai_tool(),
                *self._tools.web_browser.as_pydantic_ai_tools(),
            ],
            capabilities=[
                self._tools.web_browser.lifecycle_capability(),
                # Suspend the root agent's browser around any fan-out it triggers,
                # so it holds no page permits while awaiting subagent rows that
                # need them (same deadlock-avoidance as for non-leaf subagents).
                ReleaseBrowserBeforeFanout(browser_tool=self._tools.web_browser),
                MessageStoreCapability(
                    store=self._main_scope,
                    tool_allowlist=BROWSER_TOOL_NAMES,
                    snippet_fn=snapshot_snippet,
                    threshold_chars=SNAPSHOT_SNIPPET_THRESHOLD_CHARS,
                ),
            ],
            instructions=self._system_prompt,
            model_settings={
                "openai_service_tier": "priority",
                "openai_reasoning_effort": self.reasoning_effort,
                "openai_reasoning_summary": "detailed",
            },
        )

    async def run_stream(self, question: str) -> AsyncIterator[ChatEvent]:
        """Run the agent on a user question, yielding progress as ``ChatEvent``s.

        The stream ends with exactly one ``Finished`` (carrying the ``ChatResult``)
        on normal completion. Failures propagate as exceptions. To interrupt, cancel
        the task iterating this generator: it raises ``CancelledError`` and the
        agent's message history / ``last_usage`` are left reflecting the partial run.

        The agent loop runs as a background task (``_run_to_queue``) that pushes
        events onto a queue; this is what lets fan-out tools' progress callbacks
        (which fire deep inside tool execution, not at a ``yield``) reach the
        consumer live. The producer signals end-of-stream with a ``None`` sentinel.

        A ``ChatAgent`` runs one turn at a time — its conversation state is mutable,
        so calling this while a turn is already in flight raises ``RuntimeError``
        rather than silently corrupting history. Run separate conversations on
        separate ``ChatAgent`` instances.
        """
        if self._running:
            raise RuntimeError("a turn is already in progress on this ChatAgent")
        self._running = True
        queue: asyncio.Queue[ChatEvent | None] = asyncio.Queue()
        task = asyncio.create_task(self._run_to_queue(question, queue))
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
            await task  # surface any exception raised by the producer
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            self._running = False

    async def run(self, question: str) -> ChatResult:
        """Non-streaming convenience: run a turn and return its ``ChatResult``.

        Equivalent to draining ``run_stream`` and taking the terminal ``Finished``
        payload — for callers (tests, batch jobs) that want the result, not the live
        events. Cancellation and the one-turn-at-a-time guard behave as in
        ``run_stream``."""
        async for event in self.run_stream(question):
            if isinstance(event, Finished):
                return event.result
        raise RuntimeError("run_stream ended without a Finished event")

    async def _run_to_queue(self, question: str, queue: asyncio.Queue[ChatEvent | None]) -> None:
        """Run the agent loop in the background task, pushing events onto ``queue``
        and a terminating ``None`` sentinel. Uses ``agent.iter()`` so that on
        cancellation we can still snapshot the partial trajectory and accumulated
        usage from the live run."""
        from pydantic_ai import CallToolsNode, ModelRequestNode
        from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

        from tabulaflow.core.types import Usage

        emit = queue.put_nowait
        # Each fan-out tool passes its tool_call_id so the UI can route concurrent
        # tools' progress to the right step.
        if self._tools.run_subagent_for_each_row is not None:
            self._tools.run_subagent_for_each_row.on_row_complete = lambda c, t, tcid: emit(
                ToolProgress(completed=c, total=t, tool_call_id=tcid)
            )
        if self._tools.extract_rows_from_documents is not None:
            self._tools.extract_rows_from_documents.on_rows_extracted = lambda c, tcid: emit(
                ToolProgress(completed=c, total=None, unit="rows", tool_call_id=tcid)
            )
        self._tools.add_canonical_name.on_progress = lambda stage, c, t, tcid: emit(
            ToolProgress(completed=c, total=t, stage=stage, tool_call_id=tcid)
        )

        assert self._pydantic_ai_agent is not None

        message_id = await self._main_scope.add(kind="user_prompt", content=question)
        if len(question) > MESSAGE_THRESHOLD_CHARS:
            question = make_snippet(message_id, question)

        answer_text = ""
        final_usage: Usage | None = None
        interrupted = False
        completed_normally = False
        completed_results: dict[str, ToolReturnPart] = {}
        text_router = _TextStreamRouter()

        try:
            try:
                async with self._pydantic_ai_agent.iter(
                    question,
                    message_history=self._message_history or None,
                ) as agent_run:
                    try:
                        async for node in agent_run:
                            if not isinstance(node, (ModelRequestNode, CallToolsNode)):
                                continue
                            async with node.stream(agent_run.ctx) as stream:
                                async for event in stream:
                                    if isinstance(event, FunctionToolResultEvent) and isinstance(
                                        event.result, ToolReturnPart
                                    ):
                                        completed_results[event.tool_call_id] = event.result
                                    await _emit_stream_event(
                                        event, emit, self._query_history, self._tools.get_table_schema, text_router
                                    )
                                    await asyncio.sleep(0)
                            emit(UsageUpdated(usage=Usage.from_pydantic_ai_usage(agent_run.usage(), self.model)))
                        completed_normally = True
                    except asyncio.CancelledError:
                        interrupted = True
                        raise
                    finally:
                        final_usage = Usage.from_pydantic_ai_usage(agent_run.usage(), self.model)
                        partial_messages = list(agent_run.all_messages())
                        # Any abnormal exit — user interrupt or an error (LLM API
                        # failure, a tool raising) — can leave the trailing
                        # ModelResponse with unanswered ToolCallParts, which every
                        # provider rejects on the next turn. Patch them either way;
                        # only a clean finish keeps the history verbatim.
                        if completed_normally:
                            self._message_history = partial_messages
                        else:
                            self._message_history = _patch_incomplete_messages(
                                partial_messages, completed_results, interrupted=interrupted
                            )
                        self.last_usage = final_usage
                        if agent_run.result is not None:
                            answer_text = agent_run.result.output
            finally:
                if self._tools.run_subagent_for_each_row is not None:
                    self._tools.run_subagent_for_each_row.on_row_complete = None
                if self._tools.extract_rows_from_documents is not None:
                    self._tools.extract_rows_from_documents.on_rows_extracted = None
                self._tools.add_canonical_name.on_progress = None
                self._save_trajectory_for_debug()

            # Only reached on normal completion (cancellation re-raised above): emit
            # the authoritative final usage, then the terminal result.
            if final_usage is not None:
                emit(UsageUpdated(usage=final_usage))
            result = await _build_chat_result(answer_text, self._query_history)
            result.usage = final_usage
            emit(Finished(result=result))
        finally:
            queue.put_nowait(None)  # sentinel: stream exhausted (success, error, or cancel)

    def _save_trajectory_for_debug(self) -> None:
        """Persist the latest conversation trajectory to disk, when a
        ``trajectory_log_dir`` was provided (otherwise a no-op)."""
        if self.trajectory_log_dir is None or not self._message_history:
            return
        try:
            from tabulaflow.core.types import Trajectory

            trajectory = Trajectory.from_pydantic_ai_messages(self._message_history, id="TRJY-CHAT")
            self.trajectory_log_dir.mkdir(parents=True, exist_ok=True)
            path = self.trajectory_log_dir / "trajectory.md"
            path.write_text(trajectory.to_markdown(), encoding="utf-8")
        except Exception:
            logger.exception("Failed to persist trajectory debug file")


async def _build_chat_result(
    answer_text: str,
    query_history: QueryHistory,
) -> ChatResult:
    display_text, refs = _extract_result_refs(answer_text)
    records = await _records_from_refs(refs, query_history)
    primary_record_index: int | None = 0 if records else None
    return ChatResult(text=display_text, records=records, primary_record_index=primary_record_index)


def _patch_incomplete_messages(
    messages: list[ModelMessage],
    completed_results: dict[str, ToolReturnPart],
    *,
    interrupted: bool,
) -> list[ModelMessage]:
    """Make ``messages`` valid as ``message_history`` for the next agent run.

    A run that ends before completing — the user interrupts it, or it raises
    (an LLM API failure, a tool error) — leaves the trailing ``ModelResponse``
    with unanswered ``ToolCallPart``s, because pydantic-ai's ``CallToolsNode``
    only appends the aggregated tool-return ``ModelRequest`` once all tools
    finish. Every provider rejects a tool call with no matching result, so each
    pending call must be answered: with its real ``ToolReturnPart`` if the result
    event reached us before the break, otherwise a synthetic placeholder. A
    trailing system turn records why the run stopped. ``interrupted`` selects
    the wording (user cancel vs. error).
    """
    from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart, UserPromptPart

    cause = "was interrupted by the user" if interrupted else "failed with an error"

    out = list(messages)
    last = out[-1] if out else None
    pending = [p for p in last.parts if isinstance(p, ToolCallPart)] if isinstance(last, ModelResponse) else []

    if pending:
        out.append(
            ModelRequest(
                parts=[
                    completed_results.get(p.tool_call_id)
                    or ToolReturnPart(
                        tool_name=p.tool_name,
                        tool_call_id=p.tool_call_id,
                        content=(
                            f"[system: the run {cause} before this result was captured. "
                            "The tool may have completed first — any side effects "
                            "(e.g. writes) may or may not have taken effect.]"
                        ),
                    )
                    for p in pending
                ]
            )
        )
    out.append(ModelRequest(parts=[UserPromptPart(content=f"[system: the previous run {cause}.]")]))
    return out


_SEPARATOR = "---"


def _parse_refs(text: str) -> list[tuple[str, str | None]]:
    """Extract ``(record_id, label)`` pairs from ``[[record:Q<id>:<label>]]`` markers
    (label normalized to ``None`` when absent or blank)."""
    return [(m.group(1), (m.group(2) or "").strip() or None) for m in _QUERY_REF_RE.finditer(text)]


def _is_citation_block(prefix: str) -> bool:
    """True if ``prefix`` (the text before the first ``---``) is a citation block:
    only ``[[record:...]]`` markers and whitespace, possibly empty. This is what
    makes the ``---`` a refs/answer separator rather than content in a plain answer
    that happens to contain a ``---``."""
    return _QUERY_REF_RE.sub("", prefix).strip() == ""


def _extract_result_refs(answer_text: str) -> tuple[str, list[tuple[str, str | None]]]:
    # A leading ``---`` is the refs/answer separator only when the text before it is
    # a citation block (refs lines and/or empty) — otherwise the ``---`` is content.
    if _SEPARATOR in answer_text:
        prefix, display_text = answer_text.split(_SEPARATOR, 1)
        if _is_citation_block(prefix):
            return display_text.strip(), _parse_refs(prefix)
    # No citation block: the whole output is user-facing. Still strip any inline
    # ``[[record:...]]`` markers the agent may have left in the prose.
    refs = _parse_refs(answer_text)
    if refs:
        answer_text = _QUERY_REF_RE.sub("", answer_text)
    return answer_text.strip(), refs


class _TextStreamRouter:
    """Routes a streamed text run into the final answer vs. mid-turn narration, and
    strips the citation-refs block from the answer.

    A run that opens with a citation block — zero or more ``[[record:...]]`` lines
    terminated by ``---`` (the final answer's format; the refs may be empty) — is the
    **answer**: held back until the ``---``, then the text after it streams. Any other
    run is **narration** and streams live. After the first chunk that yields text,
    :attr:`is_answer` says which it is. Reset via :meth:`reset` per text part.

    Kept here (not the frontend) so the ``---``/refs convention — owned by this
    agent's prompt — never crosses the layer boundary.
    """

    _MARKER = "[[record:"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._raw = ""
        self._open = False  # True once text has begun streaming
        self.is_answer = False  # whether the opened run is the final answer

    def feed(self, chunk: str) -> str:
        """Accumulate ``chunk``; return its newly emittable text (``""`` until known).
        Once non-empty, :attr:`is_answer` is set for the run."""
        self._raw += chunk
        if self._open:
            return chunk
        # A citation block (refs and/or empty) ends at the first ``---``: that's the
        # answer — hide the block, stream the rest. A ``---`` preceded by prose isn't
        # a citation block, so the run is narration streamed whole.
        if _SEPARATOR in self._raw:
            prefix, answer = self._raw.split(_SEPARATOR, 1)
            if _is_citation_block(prefix):
                answer = answer.lstrip("\n")
                if not answer:
                    return ""  # separator seen but the answer hasn't started — wait
                self._open = True
                self.is_answer = True
                return answer
            self._open = True
            self.is_answer = False
            return self._raw  # ``---`` after prose: narration streamed whole
        # No separator yet: keep waiting while the lead could still be a citation
        # block — its tail (after complete refs) is empty, a partial ref marker (a
        # prefix of one, or one being built), or a partial ``---``. Else it's narration.
        tail = _QUERY_REF_RE.sub("", self._raw).lstrip()
        building_ref = tail.startswith(self._MARKER) or self._MARKER.startswith(tail)
        if tail and not building_ref and not _SEPARATOR.startswith(tail):
            self._open = True
            self.is_answer = False
            return self._raw  # narration (or an answer the model failed to delimit)
        return ""


async def _records_from_refs(
    refs: Iterable[tuple[str, str | None]],
    query_history: QueryHistory,
) -> list[ChatResultRecord]:
    records: list[ChatResultRecord] = []
    for record_id, label in refs:
        try:
            query_record = await query_history.get(record_id)
        except (KeyError, ValueError):
            continue
        records.append(_chat_result_record_from_query_record(query_record, label))
    return records


def _chat_result_record_from_query_record(
    query_record: QueryRecord,
    label: str | None,
) -> ChatResultRecord:
    pred = query_record.pred_query
    return ChatResultRecord(
        record_id=query_record.record_id,
        label=label,
        query=pred.query,
        df=pred.exec_result.df if pred.exec_result else None,
        chart_spec=query_record.vegalite_spec,
        query_lexer="cypher" if query_record.connector_type == "property_graph" else "sql",
    )


# ---------------------------------------------------------------------------
# Stream event handlers
# ---------------------------------------------------------------------------


async def _emit_stream_event(
    event: object,
    emit: Callable[[ChatEvent], None],
    query_history: QueryHistory,
    get_table_schema_tool: RegistryGetTableSchemaTool | None,
    text_router: "_TextStreamRouter",
) -> None:
    """Map one pydantic-ai stream event to ``ChatEvent``s and emit them.

    Events carry structured data only: ``ToolStarted.args`` is the raw call args
    (a frontend renders them); ``ToolFinished.outcome`` is the structured
    ``ToolOutcome`` (built here because it needs the agent's query history).

    Text and reasoning each arrive as a ``PartStartEvent`` (the first chunk — its
    content is non-empty on content-bearing streaming providers) followed by
    ``PartDeltaEvent``s. Both points must be handled or the first chunk is dropped.
    """
    from pydantic_ai.messages import (
        FunctionToolCallEvent,
        FunctionToolResultEvent,
        PartDeltaEvent,
        PartStartEvent,
        TextPart,
        TextPartDelta,
        ThinkingPart,
        ThinkingPartDelta,
    )

    if isinstance(event, FunctionToolCallEvent):
        emit(
            ToolStarted(tool_call_id=event.tool_call_id, name=event.part.tool_name, args=_coerce_args(event.part.args))
        )

    elif isinstance(event, FunctionToolResultEvent):
        tool_name = event.result.tool_name or ""
        outcome = await _build_outcome(tool_name, query_history, get_table_schema_tool)
        emit(ToolFinished(tool_call_id=event.tool_call_id, name=tool_name, outcome=outcome))

    elif isinstance(event, PartStartEvent):
        part = event.part
        if isinstance(part, ThinkingPart) and part.content:
            emit(ThinkingDelta(content=part.content))
        elif isinstance(part, TextPart):
            text_router.reset()  # a new text part begins a fresh run
            visible = text_router.feed(part.content) if part.content else ""
            if visible:
                emit((AnswerDelta if text_router.is_answer else NarrationDelta)(content=visible))

    elif isinstance(event, PartDeltaEvent):
        delta = event.delta
        if isinstance(delta, ThinkingPartDelta) and delta.content_delta:
            emit(ThinkingDelta(content=delta.content_delta))
        elif isinstance(delta, TextPartDelta) and delta.content_delta:
            visible = text_router.feed(delta.content_delta)
            if visible:
                emit((AnswerDelta if text_router.is_answer else NarrationDelta)(content=visible))


def _coerce_args(args: object) -> dict[str, Any]:
    """Normalize a tool call's ``args`` (pydantic-ai gives a JSON string or dict) to a dict."""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, TypeError):
            return {}
    return args if isinstance(args, dict) else {}


async def _build_outcome(
    tool_name: str,
    query_history: QueryHistory,
    get_table_schema_tool: RegistryGetTableSchemaTool | None,
) -> ToolOutcome:
    """Derive the structured tool outcome from the agent's recorded state. Only
    ``run_query`` (rows / error) and ``get_table_schema`` (columns) report a count;
    everything else is ``Completed``. See ``chat.events`` for the tool→outcome map."""
    if tool_name == "run_query":
        try:
            record = await query_history.last()
            pred = record.pred_query
            if pred.exec_result and pred.exec_result.df is not None:
                return RowsReturned(count=len(pred.exec_result.df))
            if pred.exec_result and pred.exec_result.error:
                return Failed()
        except ValueError:
            pass
    if tool_name == "get_table_schema" and get_table_schema_tool is not None:
        n = get_table_schema_tool.last_columns_returned
        if n is not None:
            return ColumnsReturned(count=n)
    return Completed()
