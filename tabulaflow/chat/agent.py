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
from typing import TYPE_CHECKING, Any

from pydantic_ai.models.openai import OpenAIChatModelSettings

from tabulaflow.toolhub.message_store import (
    MESSAGE_THRESHOLD_CHARS,
    MessageStore,
    MessageStoreCapability,
    ScopedMessageStore,
    make_snippet,
)
from tabulaflow.toolhub.web_browser import BROWSER_TOOL_NAMES
from tabulaflow.core.llm import make_agent
from tabulaflow.chat.result import ChatResult, ChatResultRecord
from tabulaflow.chat.events import (
    ChatEvent,
    ColumnsReturned,
    Completed,
    Failed,
    Finished,
    RowsReturned,
    TextDelta,
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

    from tabulaflow.core.db_connector.base import NL2QDBConnector
    from tabulaflow.core.db_connector.db_registry import DBRegistry
    from tabulaflow.core.types import Usage
    from tabulaflow.toolhub import (
        AddCanonicalNameTool,
        QueryHistory,
        QueryRecord,
        RegistryGetColumnJsonSchemaTool,
        RegistryGetDBDocumentTool,
        RegistryGetTableSchemaTool,
        RegistryExtractRowsFromDocumentsTool,
        RegistryRunQueryTool,
        RegistryRunSubagentForEachRowTool,
        RegistryTransferRecordTool,
        RenderPlotextChartTool,
        WebBrowserTool,
    )

logger = logging.getLogger(__name__)

_QUERY_REF_RE = re.compile(r"\[\[record:(Q\d+)(?::([^\]]+))?\]\]")


SYSTEM_PROMPT = """\
You are the tabulaflow agent, built by Megagon Labs.
You are an interactive tabular data assistant in a terminal UI app that answers the user's questions about their data.
You are an agent - please keep going until the task is solved.
If the question is ambiguous, choose the most natural interpretation and proceed. Only ask for clarification when you are truly blocked.
Be THOROUGH. Make sure you have the FULL picture before finishing. Use additional tool calls as needed.

<user_facing_communication>
CRITICAL: The user should feel as if they are directly interacting with their original dataset (e.g., "the GLUE dataset", "the IMDB dataset"). NEVER expose internal implementation details in your responses:
- NEVER mention "DuckDB", "SQLite", "database alias", "connector", "workspace", "session", or any internal system concept.
- NEVER mention the `workspace` alias or that data is being stored/queried in any particular database engine.
- Refer to datasets by their original source name (e.g., "the GLUE MNLI dataset from Hugging Face", "your CSV file sales.csv").
- When describing what data is available, talk about the dataset's tables/splits and columns — not about database internals.
- Your final response should be concise, direct, and to the point, while providing complete information and matching the level of detail you provide in your response with the level of complexity of the user's query or the work you have completed. 
- Your response is rendered in a terminal. Do not use markdown bold (**) or other rich formatting — use plain text only.
- You should minimize output tokens while maintaining helpfulness, quality, and accuracy. Only address the specific task at hand, avoiding tangential information unless absolutely critical for completing the request. If you can answer in 1-3 sentences or a short paragraph, please do.
- Do not add additional explanation or summary unless requested by the user.
</user_facing_communication>

<presenting_data>
- Always present results in tabular form using the format below when applicable for better readability.
  - If the results are not available in the database, persist it to the workspace database first.
- You can present one or multiple tables in the final response using the following format:
  - In your final response, begin with result reference lines, followed by a `---` separator, then your natural language answer.
    The references tell the system which query results to display alongside your answer. The user sees only the text after `---`.
    - Format: [[record:Q<id>:<label>]] (e.g. [[record:Q3:num_players]]).
    - Every reference MUST include a label. The label is a short, human-readable description of what the table contains (e.g. `players`, `top_movies`, `revenue_by_month`). Keep labels concise.
    - If you are unsure what to label a record, use `result` as the default (e.g. [[record:Q3:result]]). NEVER use the record id (e.g. `Q3`, `Q41`) as the label.
    - Example format:
      [[record:Q3:num_players]]
      ---
      There are 42 players in the database.
- Do not reference every query you ran. Select only the most relevant results with minimal overlap.
- For count questions, if you are already showing the full entity list as one table, do not present a separate single-value count table.
- Our data browser handles large tables and long cell values automatically, so there is no need to truncate results.
- Our data browser supports viewing images, audio, videos and pdfs, so you can show them by including binary data in the table.
</presenting_data>

Most user requests fall into one of three task modes — answering a question, transforming data, or collecting data. Identify which applies and follow the matching guidance below.

<answering_questions>
- Answer the user's question by running database queries; this mode is read-only — no writes needed.
- If the ambiguity is consequential and the plausible interpretations are few, cover them all — present one table per interpretation rather than committing to one. 
- Pay attention to whether the user is asking for one table or multiple tables.
- Do not include the execution results or the query in your final user-facing response as they will be automatically rendered in a separate view for all referenced records (see <presenting_data>).
- For huggingface datasets that exceed 500MB, the dataset is loaded as a view and a materialized sample table is created. Use the sample table unless explicitly requested by the user.
</answering_questions>

<transforming_data>
(internal implementation details, never mention to the user)
You MUST use the `workspace` alias for data transformation tasks and semantic operations (e.g., LLM-based filtering, joining, or extraction). Never modify the original tables in-place.
- `workspace` is a session-local scratch space for transformation tables. Tables created in `workspace` persist for the entire session.
- First, use `transfer_record` to move data into or out of `workspace`.
  - To transfer a full table, run `SELECT * FROM <table>` without `LIMIT`, then transfer that `record_id`.
- Prefer `run_subagent_for_each_row` over fuzzy regex matching or LIKE-based SQL for semantic operations (classifying free text, matching names with naming variations, extracting sentiment). See <concurrent_task_handling> for how to use it.
- When presenting a final table result to the user, run `SELECT *` without `LIMIT` (large table can be handled by our data browser) and reference the result in the final response (see <presenting_data>).
</transforming_data>

<collecting_data>
- When asked to build or extend a dataset (e.g. listing all records that satisfy a condition, from scratch or on top of an existing table), ensure completeness: gather the full set rather than a sample, and do not stop early.
- If full completeness is not achievable, deliver what you collected and tell the user what is missing and why.
- For large-scale collection, decompose the work into independent subtasks and gather them in parallel with `run_subagent_for_each_row` (see <concurrent_task_handling>).
- Normalize collected values so the dataset is clean and queryable:
  - Numeric values: store in a numeric column (never as strings) and convert to one consistent unit, encoding that unit in the column name (e.g., `price_usd`, `weight_kg`).
  - String values: normalize to a canonical form where possible — consistent casing, spelling, and format.
</collecting_data>

<concurrent_task_handling>
(internal implementation details, never mention to the user)
When a task decomposes into many similar, independent sub-tasks (one per row, entity, date, URL, etc.), do NOT loop through them in your own context. Lay the sub-tasks out as rows of a `workspace` table and process them concurrently with `run_subagent_for_each_row` — each row gets its own subagent running in parallel, and their intermediate work never enters your context (only a summary returns; per-row failures land in `_subagent_exception` / `_subagent_trajectory`). See the tool description for task setup and the optional capability flags.
- The subagent sees only its rendered `task_instruction`, not this conversation — encode any requirements the user mentioned into it.
- Ambitious tasks can be decomposed across multiple levels: a subagent's task can itself fan out further sub-tasks with `run_subagent_for_each_row` (set `enable_nested_subagents=True`). Reach for this when one level of rows is too coarse — break the task into a tree of sub-tasks rather than one flat sweep.
- Treat it as expensive. For large tables (>= 100 rows), run on a sampled subset first, verify, then apply to the full table. For a small number of tasks, skip the sampling step and run directly — the extra pass only hurts latency and user experience.
- Decide per task whether plain SQL rules suffice or a subagent is needed; combine both when different parts of a table need different methods.
- Do NOT call browser tools (`browser_*`) and `run_subagent_for_each_row` in the same turn. Browse to gather what you need first, then fan out in a later turn — interleaving them in one turn can stall the shared browser pool.
</concurrent_task_handling>

<plan_mode>
If the user says "plan first" or "discuss first", present a plan and wait for approval before executing.
- Multiple lightweight read-only tool calls are allowed to undertand the data, task and ground the plan.
- Do NOT run heavy or stateful tools yet (e.g. `run_subagent_for_each_row`, `transfer_record`, `render_chart`, or any writes to `workspace`).
</plan_mode>

<registry_and_alias_internal>
(internal implementation details, never mention to the user)
- Data sources are registered under aliases (e.g. `workspace`).
- `db_alias` selects which registered data source a tool call uses.
- Aliases are application-level handles, not SQL catalog/schema names.
- Tables in different aliases cannot be joined directly. To join across data sources, first transfer the relevant tables into `workspace` using `transfer_record`, then join them there.
</registry_and_alias_internal>

<long_message_offloading>
(internal implementation details, never mention to the user)
To keep your context lean, every browser response is mirrored into the `_internal.messages(message_id, kind, tool_name, tool_call_id, created_at, char_len, content)` table of the `workspace` database, and very long user prompts and tool responses are offloaded before they reach you: their full content stays in that table and you can process it progammtically or hand it to a subagent.
- For responses that carry a leading marker line `[message_id=M<n>]`, you can fetch the full content back with `run_query(db_alias="workspace", "SELECT content FROM _internal.messages WHERE message_id='M<n>'")`.
- To hand a long message to a subagent without pulling its full content into your own context, leave it offloaded and JOIN `_internal.messages` in a workspace-targeted `task_query` so the content arrives as a column — e.g. `SELECT m.message_id, m.content AS chunk FROM _internal.messages m WHERE m.message_id = 'M7'`; the per-row `task_instruction` then references it as `{{ chunk }}`.
- Offloading also applies one level down, but only to subagents that can spawn nested subagents (`enable_nested_subagents=True`): their own long prompts and tool responses are offloaded the same way and fetched back via `run_query`, so deep multi-level decompositions never overflow context at any level. Leaf subagents (no nesting) are not offloaded.
</long_message_offloading>

<tool_calling>
General:
- Try to batch tool calls if they can be run in parallel to reduce latency.

Gathering information:
- For most databases, call `get_db_document` to understand the database structure.
- For SQL databases, you may use `get_table_schema` to get the schema of relevant tables before constructing the query.
- For SQL databases, you may use `get_column_json_schema` to inspect the internal structure of semi-structured columns (e.g. VARIANT, OBJECT, ARRAY, JSON, JSONB).
- You may use `run_query` to run exploratory queries or inspect some sample values to determine the data format if necessary.
- For information not in any registered data source, use the `browser_*` tools. For structured information, always persist it to the workspace database.
  - Avoid using search engines when you can access using urls. If you need to use search engines, use duckduckgo.com as the default.

Writing database queries:
- Ensure you have collected enough information and fully understand the database structure before composing the task query.
- You may execute intermediate or exploratory queries multiple times; however, the final query displayed to the user must be complete and fully constructed without splitting the logic into multiple dependent queries.
- For complex queries with multiple CTEs, build incrementally: execute and verify each CTE's output before adding the next. Do NOT jump straight to the full assembled query.
- Format the query for readability and avoid long one-line queries.

Visualization:
- Call `render_chart` with a Vega-Lite JSON spec if the result lends itself to a chart (e.g. counts by category, trends over time, distributions).
- `render_chart` accepts an optional `record_id`. Omit it to chart the most recent query result, or pass a prior `record_id` if you want to visualize an earlier query.
- Do NOT render charts for single-row results, heterogeneous tables, or when the user only asks for a specific value.
- Supported marks: bar, line, point, rect. Only simple specs with x/y encoding are supported.
- Prefer bar for categorical comparisons, line for time series, point for correlations.
</tool_calling>

<examples>
Example: Cross-source semantic join

User question: "Which employees work at offices that were flagged for safety violations?"
Available databases:
  - `hr`: table `employees` with columns (emp_id, name, office_code)  — office_code values like "SF-HQ", "NYC-3", "CHI-W"
  - `compliance`: table `violations` with columns (facility_name, violation_date, status) — facility_name values like "San Francisco Headquarters", "New York City Office 3", "Chicago West Campus"

There is no shared key between office_code and facility_name. The mapping requires world knowledge.

Steps:
1. Transfer both tables into `workspace`.
2. Add a resolved/normalized column to one (or both) tables.
3. Use `run_subagent_for_each_row` to populate the new column by matching values across tables.
   - (preferred when the lookup space is large) approach (a): Add a foreign-key column to one table and have the subagent resolve the match against the other table at runtime — set `enable_run_query_tool=True`. Do not embed a large vocabulary in the task instruction.
   - approach (b): Add a normalized column to both tables and have the subagent normalize each side to a canonical form (e.g., "normalize to IATA airport code") independently. No `run_query` access needed.
4. Join on the resolved column with a standard SQL query.
</examples>
""".strip()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Toolset:
    """Typed bundle of agent tools."""

    run_query: RegistryRunQueryTool
    get_db_document: RegistryGetDBDocumentTool
    get_column_json_schema: RegistryGetColumnJsonSchemaTool
    get_table_schema: RegistryGetTableSchemaTool
    transfer_record: RegistryTransferRecordTool
    run_subagent_for_each_row: RegistryRunSubagentForEachRowTool
    extract_rows_from_documents: RegistryExtractRowsFromDocumentsTool
    add_canonical_name: AddCanonicalNameTool
    render_chart: RenderPlotextChartTool
    web_browser: WebBrowserTool


@dataclass
class ChatAgent:
    """Streaming agent for interactive database chat."""

    registry: DBRegistry
    model: str
    session_id: str
    trajectory_log_dir: Path
    _message_history: list[ModelMessage] = field(default_factory=list)
    _system_prompt: str = SYSTEM_PROMPT
    _pydantic_ai_agent: Agent[None, str] | None = None
    _query_history: QueryHistory = field(init=False)
    _message_store: MessageStore = field(init=False)
    _main_scope: ScopedMessageStore = field(init=False)
    _tools: Toolset = field(init=False)
    last_usage: Usage | None = None

    def __post_init__(self) -> None:
        from tabulaflow.core.formatters.sql_ddl import SQLDDLSchemaFormatter
        from tabulaflow.modulehub.db_summarizer import DBSummarizer
        from tabulaflow.toolhub import (
            AddCanonicalNameTool,
            QueryHistory,
            RegistryExtractRowsFromDocumentsTool,
            RegistryGetColumnJsonSchemaTool,
            RegistryGetDBDocumentTool,
            RegistryGetTableSchemaTool,
            RegistryRunQueryTool,
            RegistryRunSubagentForEachRowTool,
            RegistryTransferRecordTool,
            RenderPlotextChartTool,
            WebBrowserTool,
        )

        self._query_history = QueryHistory()
        self._message_store = MessageStore()
        self._main_scope = self._message_store.scoped("main")
        self._tools = Toolset(
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
            run_subagent_for_each_row=RegistryRunSubagentForEachRowTool(
                self.registry,
                message_store=self._message_store,
                model_settings=OpenAIChatModelSettings(
                    openai_service_tier="priority",
                    openai_reasoning_effort="medium",
                    openai_reasoning_summary="detailed",
                ),
                store_metadata=True,
                trajectory_log_dir=self.trajectory_log_dir / "subagents",
            ),
            extract_rows_from_documents=RegistryExtractRowsFromDocumentsTool(
                self.registry,
                model_settings=OpenAIChatModelSettings(
                    openai_service_tier="priority",
                    openai_reasoning_effort="medium",
                ),
            ),
            add_canonical_name=AddCanonicalNameTool(
                model_settings=OpenAIChatModelSettings(
                    openai_service_tier="priority",
                    openai_reasoning_effort="medium",
                ),
                trajectory_log_dir=self.trajectory_log_dir / "subagents",
            ),
            render_chart=RenderPlotextChartTool(history=self._query_history),
            web_browser=WebBrowserTool(),
        )
        self._build_agent()

    def set_model(self, model: str) -> None:
        """Update model and rebuild the bound runtime agent."""
        if self.model == model:
            return
        self.model = model
        self._build_agent()

    def set_workspace(self, connector: NL2QDBConnector) -> None:
        """Attach a workspace connector for persisting query-history DataFrames."""
        from tabulaflow.core.db_connector.sql_conn import SQLConnector
        from tabulaflow.toolhub.query_history import QueryHistory

        if not isinstance(connector, SQLConnector):
            return
        self._query_history = QueryHistory(spill_connector=connector)
        self._tools.run_query._history = self._query_history
        self._tools.transfer_record._history = self._query_history
        self._tools.render_chart._history = self._query_history
        self._message_store.attach_connector(connector)
        self._tools.add_canonical_name.attach_connector(connector)

    @staticmethod
    def database_info(connector: NL2QDBConnector) -> str:
        """Build a concise database summary string."""
        from tabulaflow.core.db_connector import Neo4jConnector

        if isinstance(connector, Neo4jConnector):
            n_labels = len(connector.schema.nodes)
            n_patterns = len(connector.schema.relationships)
            return f"cypher, {n_labels} label{'s' if n_labels != 1 else ''}, {n_patterns} rel pattern{'s' if n_patterns != 1 else ''}"

        from tabulaflow.core.types import SQLSchema

        schema = connector.schema
        n_tables = len(schema.tables) if isinstance(schema, SQLSchema) else 0
        dialect = connector.language or "unknown"
        return f"{dialect}, {n_tables} tables"

    def add_database(self, databases: list[tuple[str, NL2QDBConnector]]) -> None:
        """Append a synthetic user message about newly registered databases."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        if not databases:
            return
        lines = [
            "[system: data sources now available — use these aliases in db_alias tool args. "
            "Do NOT expose alias names, dialect, or engine details to the user.]"
        ]
        for alias, connector in databases:
            lines.append(f"- {alias}: {self.database_info(connector)}")
        content = "\n".join(lines)
        self._message_history.append(ModelRequest(parts=[UserPromptPart(content=content)]))

    def _build_agent(self) -> None:
        from tabulaflow.toolhub.run_subagent_for_each_row import ReleaseBrowserBeforeFanout

        self._pydantic_ai_agent = make_agent(
            self.model,
            tools=[
                self._tools.run_query.as_pydantic_ai_tool(),
                self._tools.get_db_document.as_pydantic_ai_tool(),
                self._tools.get_table_schema.as_pydantic_ai_tool(),
                self._tools.get_column_json_schema.as_pydantic_ai_tool(),
                self._tools.transfer_record.as_pydantic_ai_tool(),
                self._tools.run_subagent_for_each_row.as_pydantic_ai_tool(),
                self._tools.extract_rows_from_documents.as_pydantic_ai_tool(),
                self._tools.add_canonical_name.as_pydantic_ai_tool(),
                self._tools.render_chart.as_pydantic_ai_tool(),
                *self._tools.web_browser.as_pydantic_ai_tools(),
            ],
            capabilities=[
                self._tools.web_browser.lifecycle_capability(),
                # Drop the root agent's browser tabs before it fans out, so it
                # holds no page permits while awaiting subagent rows that need
                # them (same deadlock-avoidance as for non-leaf subagents).
                ReleaseBrowserBeforeFanout(browser_tool=self._tools.web_browser),
                MessageStoreCapability(
                    store=self._main_scope,
                    tool_allowlist=BROWSER_TOOL_NAMES,
                ),
            ],
            instructions=self._system_prompt,
            model_settings={
                "openai_service_tier": "priority",
                "openai_reasoning_effort": "medium",
                "openai_reasoning_summary": "detailed",
            },
        )

    async def run_stream(self, question: str) -> AsyncIterator[ChatEvent]:
        """Run the agent on a user question, yielding progress as ``ChatEvent``s.

        The stream ends with exactly one ``Finished`` (carrying the ``ChatResult``)
        on normal completion. Failures propagate as exceptions. To interrupt, cancel
        the task iterating this generator: it raises ``CancelledError`` and the
        agent's message history / ``last_usage`` are left reflecting the partial run.

        A background driver task runs the agent loop and pushes events onto a queue;
        this is what lets fan-out tools' progress callbacks (which fire deep inside
        tool execution, not at a ``yield``) reach the consumer live.
        """
        queue: asyncio.Queue[ChatEvent | None] = asyncio.Queue()

        async def _drive() -> None:
            try:
                await self._drive_run(question, queue.put_nowait)
            finally:
                queue.put_nowait(None)  # sentinel: stream exhausted

        task = asyncio.create_task(_drive())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
            await task  # surface any exception raised by the driver
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    async def _drive_run(self, question: str, emit: Callable[[ChatEvent], None]) -> None:
        """Run the agent loop, emitting events. Body of ``run_stream`` (runs in the
        driver task). Uses ``agent.iter()`` so that on cancellation we can still
        snapshot the partial trajectory and accumulated usage from the live run."""
        from pydantic_ai import CallToolsNode, ModelRequestNode
        from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

        from tabulaflow.core.types import Usage

        self._tools.run_subagent_for_each_row.on_row_complete = lambda c, t: emit(ToolProgress(completed=c, total=t))
        self._tools.extract_rows_from_documents.on_row_complete = lambda c, t: emit(ToolProgress(completed=c, total=t))
        self._tools.add_canonical_name.on_progress = lambda stage, c, t: emit(
            ToolProgress(completed=c, total=t, stage=stage)
        )

        assert self._pydantic_ai_agent is not None

        message_id = await self._main_scope.add(kind="user_prompt", content=question)
        if len(question) > MESSAGE_THRESHOLD_CHARS:
            question = make_snippet(message_id, question)

        answer_text = ""
        final_usage: Usage | None = None
        interrupted = False
        completed_results: dict[str, ToolReturnPart] = {}

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
                                    event, emit, self._query_history, self._tools.get_table_schema
                                )
                                await asyncio.sleep(0)
                        emit(UsageUpdated(usage=Usage.from_pydantic_ai_usage(agent_run.usage(), self.model)))
                except asyncio.CancelledError:
                    interrupted = True
                    raise
                finally:
                    final_usage = Usage.from_pydantic_ai_usage(agent_run.usage(), self.model)
                    partial_messages = list(agent_run.all_messages())
                    if interrupted:
                        self._message_history = _patch_interrupted_messages(partial_messages, completed_results)
                    else:
                        self._message_history = partial_messages
                    self.last_usage = final_usage
                    if agent_run.result is not None:
                        answer_text = agent_run.result.output
        finally:
            self._tools.run_subagent_for_each_row.on_row_complete = None
            self._tools.extract_rows_from_documents.on_row_complete = None
            self._tools.add_canonical_name.on_progress = None
            self._save_trajectory_for_debug()

        # Only reached on normal completion (cancellation re-raised above): emit the
        # authoritative final usage, then the terminal result.
        if final_usage is not None:
            emit(UsageUpdated(usage=final_usage))
        result = await _build_chat_result(answer_text, self._query_history)
        result.usage = final_usage
        emit(Finished(result=result))

    def _save_trajectory_for_debug(self) -> None:
        """Persist the latest conversation trajectory for debugging."""
        if not self._message_history:
            return
        try:
            from tabulaflow.core.types import Trajectory

            trajectory = Trajectory.from_pydantic_ai_messages(self._message_history, id="TRJY-CLI")
            self.trajectory_log_dir.mkdir(parents=True, exist_ok=True)
            path = self.trajectory_log_dir / "trajectory.md"
            path.write_text(trajectory.to_markdown(), encoding="utf-8")
        except Exception:
            logger.exception("Failed to persist CLI trajectory debug file")


async def _build_chat_result(
    answer_text: str,
    query_history: QueryHistory,
) -> ChatResult:
    display_text, refs = _extract_result_refs(answer_text)
    records = await _records_from_refs(refs, query_history)
    primary_record_index: int | None = 0 if records else None
    return ChatResult(text=display_text, records=records, primary_record_index=primary_record_index)


def _patch_interrupted_messages(
    messages: list[ModelMessage],
    completed_results: dict[str, ToolReturnPart],
) -> list[ModelMessage]:
    """Make ``messages`` valid as ``message_history`` for the next agent run.

    Pydantic-ai's ``CallToolsNode`` only appends the aggregated tool-return
    ``ModelRequest`` once all tools finish, so a mid-run interrupt always
    leaves the trailing ``ModelResponse`` with unanswered ``ToolCallPart``s.
    For each: substitute the real ``ToolReturnPart`` if its result event
    reached us before cancellation, otherwise a synthetic placeholder noting
    the result is unknown.
    """
    from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart, UserPromptPart

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
                            "[system: interrupted by user before result was captured. "
                            "The tool may have completed before cancellation — any side effects "
                            "(e.g. writes) may or may not have taken effect.]"
                        ),
                    )
                    for p in pending
                ]
            )
        )
    out.append(ModelRequest(parts=[UserPromptPart(content="[system: the user interrupted the previous run.]")]))
    return out


_SEPARATOR = "---"


def _extract_result_refs(answer_text: str) -> tuple[str, list[tuple[str, str | None]]]:
    # Split on the --- separator; refs are before it, display text after.
    if _SEPARATOR in answer_text:
        prefix, display_text = answer_text.split(_SEPARATOR, 1)
    else:
        # No explicit separator means the full output is user-facing text.
        prefix, display_text = "", answer_text

    refs: list[tuple[str, str | None]] = []
    for match in _QUERY_REF_RE.finditer(prefix):
        record_id = match.group(1)
        raw_label = match.group(2)
        label = raw_label.strip() if raw_label is not None else None
        refs.append((record_id, label or None))

    # Fallback: also scan display_text for refs (in case agent doesn't follow format)
    if not refs:
        for match in _QUERY_REF_RE.finditer(display_text):
            record_id = match.group(1)
            raw_label = match.group(2)
            label = raw_label.strip() if raw_label is not None else None
            refs.append((record_id, label or None))
        display_text = _QUERY_REF_RE.sub("", display_text)

    return display_text.strip(), refs


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
) -> None:
    """Map one pydantic-ai stream event to ``ChatEvent``s and emit them.

    Events carry structured data only: ``ToolStarted.args`` is the raw call args
    (a frontend renders them); ``ToolFinished.outcome`` is the structured
    ``ToolOutcome`` (built here because it needs the agent's query history). Answer
    text streams via ``PartDeltaEvent`` (unchanged from before); reasoning also
    honors the initial ``PartStartEvent`` chunk (some providers put it there).
    """
    from pydantic_ai.messages import (
        FunctionToolCallEvent,
        FunctionToolResultEvent,
        PartDeltaEvent,
        PartStartEvent,
        TextPartDelta,
        ThinkingPart,
        ThinkingPartDelta,
    )

    if isinstance(event, FunctionToolCallEvent):
        emit(ToolStarted(tool_call_id=event.tool_call_id, name=event.part.tool_name, args=_coerce_args(event.part.args)))

    elif isinstance(event, FunctionToolResultEvent):
        tool_name = event.result.tool_name or ""
        outcome = await _build_outcome(tool_name, query_history, get_table_schema_tool)
        emit(ToolFinished(tool_call_id=event.tool_call_id, name=tool_name, outcome=outcome))

    elif isinstance(event, PartStartEvent):
        part = event.part
        if isinstance(part, ThinkingPart) and part.content:
            emit(ThinkingDelta(content=part.content))

    elif isinstance(event, PartDeltaEvent):
        delta = event.delta
        if isinstance(delta, ThinkingPartDelta) and delta.content_delta:
            emit(ThinkingDelta(content=delta.content_delta))
        elif isinstance(delta, TextPartDelta) and delta.content_delta:
            emit(TextDelta(content=delta.content_delta))


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


