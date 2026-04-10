"""CLI chat agent for interactive query chat."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import json
import logging
from pathlib import Path
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import pandas as pd
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelMessage

    from mintq.db_connector.base import NL2QDBConnector
    from mintq.db_connector.db_registry import DBRegistry
    from mintq.toolhub import (
        QueryHistory,
        QueryRecord,
        RegistryGetColumnJsonSchemaTool,
        RegistryGetDBDocumentTool,
        RegistryGetTableSchemaTool,
        RegistryRunQueryTool,
        RegistryRunSubagentForEachRowTool,
        RegistryTransferRecordTool,
        RenderPlotextChartTool,
    )

logger = logging.getLogger(__name__)

_QUERY_REF_RE = re.compile(r"\[\[result:(Q\d+)(?::([^\]]+))?\]\]")
_TRAJECTORY_KEEP_LAST = 20


SYSTEM_PROMPT = """\
You are the mintq agent, built by Megagon Labs.
You are an interactive data assistant in a terminal UI app that answers the user's questions about their data.
You are an agent - please keep going until the task is solved.
Be THOROUGH. Make sure you have the FULL picture before finishing. Use additional tool calls as needed.

<user_facing_communication>
CRITICAL: The user should feel as if they are directly interacting with their original dataset (e.g., "the GLUE dataset", "the IMDB dataset"). NEVER expose internal implementation details in your responses:
- NEVER mention "DuckDB", "SQLite", "database alias", "connector", "workspace", or any internal system concept.
- NEVER mention the `workspace` alias or that data is being stored/queried in any particular database engine.
- Refer to datasets by their original source name (e.g., "the GLUE MNLI dataset from Hugging Face", "your CSV file sales.csv").
- When describing what data is available, talk about the dataset's tables/splits and columns — not about database internals.
- Your final response should be concise, direct, and to the point, while providing complete information and matching the level of detail you provide in your response with the level of complexity of the user's query or the work you have completed. 
- Your response is rendered in a terminal. Do not use markdown bold (**) or other rich formatting — use plain text only.
- You should minimize output tokens while maintaining helpfulness, quality, and accuracy. Only address the specific task at hand, avoiding tangential information unless absolutely critical for completing the request. If you can answer in 1-3 sentences or a short paragraph, please do.
- Do not add additional explanation or summary unless requested by the user.
</user_facing_communication>

<presenting_data>
- Present data in tabular form if it is relevant to the user's question.
- You can present one or multiple tables in the final response using the following format:
  - In your final response, begin with result reference lines, followed by a `---` separator, then your natural language answer.
    The references tell the system which query results to display alongside your answer. The user sees only the text after `---`.
    - Basic form: [[result:Q<id>]] (e.g. [[result:Q3]]).
    - Optional labeled form: [[result:Q<id>:<label>]] (e.g. [[result:Q3:num_players]]).
    - Use labels when returning multiple records in one answer. Keep the labels as concise as possible.
    - Example format:
      [[result:Q3]]
      ---
      There are 42 players in the database.
- Do not reference every query you ran. Select only the most relevant results with minimal overlap.
- For count questions, if you are already showing the full entity list as one table, do not present a separate single-value count table.
- Our data browser handles large tables and long cell values automatically, so there is no need to truncate results.
</presenting_data>

<read_only_questions>
- For read-only questions, your goal is to run database queries to answer the question.
- If the question is ambiguous, choose the most natural interpretation and proceed. Only ask for clarification when you are truly blocked.
- Pay attention to whether the user is asking for one table or multiple tables.
- Do not include the execution results or the query in your final user-facing response as they will be automatically rendered in a separate view for all referenced records.
- For huggingface datasets that exceed 500MB, the dataset is loaded as a view and a materialized sample table is created. Use the sample table unless explicitly requested by the user.
</read_only_questions>

<data_transformation_tasks_internal>
These are internal implementation details — never mention them to the user.
You MUST use the `workspace` alias for data transformation tasks and semantic operations (e.g., LLM-based filtering, joining, or extraction). Never modify the original tables in-place.
- `workspace` is a session-local scratch space for transformation tables. Tables created in `workspace` persist for the entire session.
- First, use `transfer_record` to move data into or out of `workspace`.
  - To transfer a full table, run `SELECT * FROM <table>` without `LIMIT`, then transfer that `record_id`.
- Use `registry_run_subagent_for_each_row` when you need row-wise LLM processing that writes updates back to an existing table. Prefer this over fuzzy regex matching or LIKE-based SQL for semantic operations (e.g., classifying free text, joining on product names with naming variations, extracting sentiment from text).
- When presenting a final table result to the user, run `SELECT *` without `LIMIT` (large table can be handled by our data browser) and reference the result in the final response.
</data_transformation_tasks_internal>

<registry_and_alias_internal>
These are internal implementation details — never mention them to the user.
- Data sources are registered under aliases (e.g. `workspace`).
- `db_alias` selects which registered data source a tool call uses.
- Aliases are application-level handles, not SQL catalog/schema names.
- Tables in different aliases cannot be joined directly. To join across data sources, first transfer the relevant tables into `workspace` using `transfer_record`, then join them there.
</registry_and_alias_internal>

<tool_calling>
Gathering information:
- For most databases, call `get_db_document` to understand the database structure.
- For SQL databases, you may use `get_table_schema` to get the schema of relevant tables before constructing the query.
- For SQL databases, you may use `get_column_json_schema` to inspect the internal structure of semi-structured columns (e.g. VARIANT, OBJECT, ARRAY, JSON, JSONB).
- You may use `run_query` to run exploratory queries or inspect some sample values to determine the data format if necessary.

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
3. Use `registry_run_subagent_for_each_row` to populate the new column by matching values across tables.
   - (preferred) approach (a): When resolving values against a column in the other table, instruct the subagent to query it at runtime — do not embed a large vocabulary in the task instruction.
   - approach (b): When normalizing both sides, specify the canonical form (e.g., "normalize to IATA airport code").
4. Join on the resolved column with a standard SQL query.
</examples>
""".strip()


# ---------------------------------------------------------------------------
# Progress sink protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ProgressSink(Protocol):
    """Interface for displaying agent execution progress."""

    def start(self) -> None: ...
    def finish(self) -> None: ...
    def tool_start(self, name: str, args_summary: str) -> None: ...
    def tool_end(self, name: str, result_summary: str) -> None: ...
    def tool_progress(self, completed: int, total: int) -> None: ...
    def text_delta(self, delta: str) -> None: ...
    def set_status(self, text: str) -> None: ...


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ChatResultRecord:
    """Display-ready data for one referenced query record."""

    record_id: str
    label: str | None
    query: str | None
    df: pd.DataFrame | None
    chart_spec: dict[str, object] | None
    query_lexer: str = "sql"


@dataclass
class ChatResult:
    """Display-ready result of a single chat turn."""

    text: str
    records: list[ChatResultRecord] = field(default_factory=list)
    primary_record_index: int | None = 0

    @property
    def primary_record(self) -> ChatResultRecord | None:
        if not self.records:
            return None
        if self.primary_record_index is None:
            return None
        if self.primary_record_index < 0 or self.primary_record_index >= len(self.records):
            return None
        return self.records[self.primary_record_index]


@dataclass
class Toolset:
    """Typed bundle of agent tools."""

    run_query: RegistryRunQueryTool
    get_db_document: RegistryGetDBDocumentTool
    get_column_json_schema: RegistryGetColumnJsonSchemaTool
    get_table_schema: RegistryGetTableSchemaTool
    transfer_record: RegistryTransferRecordTool
    registry_run_subagent_for_each_row: RegistryRunSubagentForEachRowTool
    render_chart: RenderPlotextChartTool


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
    _tools: Toolset = field(init=False)

    def __post_init__(self) -> None:
        from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
        from mintq.toolhub import (
            QueryHistory,
            RegistryGetColumnJsonSchemaTool,
            RegistryGetDBDocumentTool,
            RegistryGetTableSchemaTool,
            RegistryRunQueryTool,
            RegistryRunSubagentForEachRowTool,
            RegistryTransferRecordTool,
            RenderPlotextChartTool,
        )

        self._query_history = QueryHistory()
        self._tools = Toolset(
            run_query=RegistryRunQueryTool(self.registry, history=self._query_history),
            get_db_document=RegistryGetDBDocumentTool(self.registry, model_settings={"openai_service_tier": "priority"}),
            get_column_json_schema=RegistryGetColumnJsonSchemaTool(self.registry),
            get_table_schema=RegistryGetTableSchemaTool(self.registry, SQLDDLSchemaFormatter(), enable_refresh=True),
            transfer_record=RegistryTransferRecordTool(self.registry, self._query_history),
            registry_run_subagent_for_each_row=RegistryRunSubagentForEachRowTool(
                self.registry,
                model_settings={"openai_service_tier": "priority"},
            ),
            render_chart=RenderPlotextChartTool(history=self._query_history),
        )
        self._build_agent()

    def set_model(self, model: str) -> None:
        """Update model and rebuild the bound runtime agent."""
        if self.model == model:
            return
        self.model = model
        self._build_agent()

    @staticmethod
    def database_info(connector: NL2QDBConnector) -> str:
        """Build a concise database summary string."""
        from mintq.db_connector import Neo4jConnector

        if isinstance(connector, Neo4jConnector):
            n_labels = len(connector.schema.nodes)
            n_patterns = len(connector.schema.relationships)
            return f"cypher, {n_labels} label{'s' if n_labels != 1 else ''}, {n_patterns} rel pattern{'s' if n_patterns != 1 else ''}"

        from mintq.schema import SQLSchema

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
            "[internal: data sources now available — use these aliases in db_alias tool args. "
            "Do NOT expose alias names, dialect, or engine details to the user.]"
        ]
        for alias, connector in databases:
            lines.append(f"- {alias}: {self.database_info(connector)}")
        content = "\n".join(lines)
        self._message_history.append(ModelRequest(parts=[UserPromptPart(content=content)]))

    def _build_agent(self) -> None:
        import mintq.patches  # noqa: F401
        from pydantic_ai import Agent

        self._pydantic_ai_agent = Agent(
            model=self.model,  # type: ignore[call-overload]
            tools=[
                self._tools.run_query.as_pydantic_ai_tool(),
                self._tools.get_db_document.as_pydantic_ai_tool(),
                self._tools.get_table_schema.as_pydantic_ai_tool(),
                self._tools.get_column_json_schema.as_pydantic_ai_tool(),
                self._tools.transfer_record.as_pydantic_ai_tool(),
                self._tools.registry_run_subagent_for_each_row.as_pydantic_ai_tool(),
                self._tools.render_chart.as_pydantic_ai_tool(),
            ],
            instructions=self._system_prompt,
            model_settings={
                "openai_service_tier": "priority",
                "openai_reasoning_effort": "medium",
                "openai_reasoning_summary": "detailed",
            },
        )

    async def run(self, question: str, progress: ProgressSink) -> ChatResult:
        """Run the agent on a user question, streaming progress to the sink."""
        from pydantic_ai.run import AgentRunResultEvent

        progress.start()
        self._tools.registry_run_subagent_for_each_row.on_row_complete = (
            lambda c, t: progress.tool_progress(c, t)
        )

        try:
            assert self._pydantic_ai_agent is not None

            answer_text = ""
            async for event in self._pydantic_ai_agent.run_stream_events(
                question,
                message_history=self._message_history or None,
            ):
                if isinstance(event, AgentRunResultEvent):
                    self._message_history = list(event.result.all_messages())
                    answer_text = event.result.output
                    break

                _handle_stream_event(event, progress, self._query_history, self._tools.get_table_schema)
                await asyncio.sleep(0)

        finally:
            self._tools.registry_run_subagent_for_each_row.on_row_complete = None
            progress.finish()

        self._save_trajectory_for_debug()
        return _build_chat_result(answer_text, self._query_history)

    def _save_trajectory_for_debug(self) -> None:
        """Persist the latest conversation trajectory and keep recent history bounded."""
        if not self._message_history:
            return
        try:
            from mintq.schema import Trajectory

            trajectory = Trajectory.from_pydantic_ai_messages(self._message_history, id="TRJY-CLI")
            self.trajectory_log_dir.mkdir(parents=True, exist_ok=True)
            self._rotate_trajectory_files()
            path = self.trajectory_log_dir / "trajectory.md"
            path.write_text(trajectory.to_markdown(), encoding="utf-8")
        except Exception:
            logger.exception("Failed to persist CLI trajectory debug file")

    def _rotate_trajectory_files(self) -> None:
        """Rotate trajectory.md into trajectory.N.md backups."""
        max_backups = max(_TRAJECTORY_KEEP_LAST - 1, 0)
        if max_backups == 0:
            return

        oldest = self.trajectory_log_dir / f"trajectory.{max_backups}.md"
        if oldest.exists():
            try:
                oldest.unlink()
            except OSError:
                logger.warning("Failed to remove old trajectory file: %s", oldest)

        for i in range(max_backups - 1, 0, -1):
            src = self.trajectory_log_dir / f"trajectory.{i}.md"
            dst = self.trajectory_log_dir / f"trajectory.{i + 1}.md"
            if src.exists():
                src.replace(dst)

        current = self.trajectory_log_dir / "trajectory.md"
        first_backup = self.trajectory_log_dir / "trajectory.1.md"
        if current.exists():
            current.replace(first_backup)


def _build_chat_result(
    answer_text: str,
    query_history: QueryHistory,
) -> ChatResult:
    display_text, refs = _extract_result_refs(answer_text)
    records = _records_from_refs(refs, query_history)
    primary_record_index: int | None = 0 if records else None
    return ChatResult(text=display_text, records=records, primary_record_index=primary_record_index)


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


def _records_from_refs(
    refs: Iterable[tuple[str, str | None]],
    query_history: QueryHistory,
) -> list[ChatResultRecord]:
    records: list[ChatResultRecord] = []
    for record_id, label in refs:
        try:
            query_record = query_history.get(record_id)
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


def _handle_stream_event(
    event: object,
    progress: ProgressSink,
    query_history: QueryHistory,
    get_table_schema_tool: RegistryGetTableSchemaTool | None,
) -> None:
    from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent, PartDeltaEvent, TextPartDelta

    if isinstance(event, FunctionToolCallEvent):
        tool_name = event.part.tool_name
        args = event.part.args
        args_summary = _summarize_args(tool_name, args)
        progress.tool_start(tool_name, args_summary)

    elif isinstance(event, FunctionToolResultEvent):
        result_tool_name = event.result.tool_name or ""
        result_summary = _summarize_result(result_tool_name, query_history, get_table_schema_tool)
        progress.tool_end(result_tool_name, result_summary)

    elif isinstance(event, PartDeltaEvent):
        if isinstance(event.delta, TextPartDelta):
            progress.text_delta(event.delta.content_delta)


def _summarize_args(tool_name: str, args: str | dict[str, object] | None) -> str:
    if args is None:
        return ""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, TypeError):
            return str(args)[:80]
    if not isinstance(args, dict):
        return str(args)[:80]

    db_prefix = ""
    if args.get("db_alias"):
        db_prefix = f"[{args['db_alias']}] "

    if tool_name == "run_query":
        query = " ".join(str(args.get("query", "")).split())
        if len(query) > 40:
            query = query[:37] + "..."
        return f"{db_prefix}{query}"
    if tool_name == "get_table_schema":
        parts = []
        if args.get("schema_name"):
            parts.append(str(args["schema_name"]))
        parts.append(str(args.get("table_name", "")))
        return f"{db_prefix}{'.'.join(parts)}"
    if tool_name == "get_db_document":
        refresh = bool(args.get("refresh", False))
        return f"{db_prefix}{'refresh' if refresh else 'cached'}"
    if tool_name == "get_column_json_schema":
        parts = []
        if args.get("schema_name"):
            parts.append(str(args["schema_name"]))
        parts.append(str(args.get("table_name", "")))
        parts.append(str(args.get("column_name", "")))
        label = ".".join(parts)
        if args.get("path"):
            label += f", path={args['path']}"
        return f"{db_prefix}{label}"
    if tool_name == "render_chart":
        spec_str = args.get("vegalite_spec", "")
        try:
            spec = json.loads(spec_str) if isinstance(spec_str, str) else spec_str
            mark = spec.get("mark", "") if isinstance(spec, dict) else ""
            if isinstance(mark, dict):
                mark = mark.get("type", "")
            title = spec.get("title", "") if isinstance(spec, dict) else ""
            return str(title) if title else str(mark)
        except (json.JSONDecodeError, TypeError):
            return "chart"
    if tool_name == "transfer_record":
        record_id = str(args.get("record_id", ""))
        target_alias = str(args.get("target_alias", ""))
        target_schema = str(args.get("target_schema", "")) if args.get("target_schema") else ""
        target_table = str(args.get("target_table", ""))
        mode = str(args.get("mode", "append"))
        target = f"{target_schema}.{target_table}" if target_schema else target_table
        return f"{record_id} -> [{target_alias}] {target} ({mode})"
    if tool_name == "run_subagent_for_each_row":
        table_name = str(args.get("table_name", ""))
        return f"{db_prefix}{table_name}"
    return str(args)[:80]


def _summarize_result(
    tool_name: str,
    query_history: QueryHistory,
    get_table_schema_tool: RegistryGetTableSchemaTool | None,
) -> str:
    if tool_name == "run_query":
        try:
            pred = query_history.last().pred_query
            if pred.exec_result and pred.exec_result.df is not None:
                return f"{len(pred.exec_result.df)} rows"
            if pred.exec_result and pred.exec_result.error:
                return "error"
        except ValueError:
            pass
    if tool_name == "get_table_schema" and get_table_schema_tool is not None:
        n = get_table_schema_tool.last_columns_returned
        if n is not None:
            return f"{n} columns"
    return "done"
