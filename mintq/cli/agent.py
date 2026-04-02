"""CLI chat agent for interactive query chat."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    import pandas as pd
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelMessage

    from mintq.db_connector.base import NL2QDBConnector
    from mintq.db_connector.db_registry import DBRegistry
    from mintq.toolhub.registry_get_column_json_schema import RegistryGetColumnJsonSchemaTool
    from mintq.toolhub.registry_run_query import QueryHistory
    from mintq.toolhub.render_chart import RenderPlotextChartTool
    from mintq.toolhub.registry_run_query import RegistryRunQueryTool
    from mintq.toolhub.registry_get_table_schema import RegistryGetTableSchemaTool

logger = logging.getLogger(__name__)

_QUERY_REF_RE = re.compile(r"\[\[result:(Q\d+)\]\]")

SYSTEM_PROMPT = """\
You are the mintq agent, a helpful database assistant that answers the user's question by querying the database.
You are an agent - please keep going until the task is solved.

<goal>
- If the question is ambiguous, pick the most natural interpretation and proceed. Only ask for clarifications if you are truly blocked.
- All database tools require a `db_alias` parameter to specify which database to target.
- Your final response should be a clear concise natural language answer summarizing the results.
- Do not put the query in the final response unless explicitly asked to.
- Do not include the query execution results in the final response. The execution results will be rendered in a separate view to the user.
- IMPORTANT: In your final response, include [[result:Q<id>]] to reference the query whose results answer the user's question. Use the record_id shown in each tool response (e.g. [[result:Q3]]). This tells the system which query and data to display alongside your answer.
</goal>

<tool_calling>
Gathering information:
- For graph databases, the schema is provided in <db_document>. Read it before writing Cypher.
- You may use `run_query` to run exploratory Cypher queries when that helps clarify the graph.
- For SQL databases, always use `get_table_schema` to get the schema of relevant tables before constructing the query.
- You may use `get_column_json_schema` to inspect the internal structure of semi-structured columns (e.g. VARIANT, OBJECT, ARRAY, JSON, JSONB).
- You may use `run_query` to inspect some sample values to determine the data format if necessary.

Writing the task query:
- Ensure you have collected enough information and fully understand the database structure before composing the task query.
- You may execute intermediate or exploratory queries multiple times; however, the final query (the last one executed) must be complete and fully constructed. In the final query, do not split the logic into multiple dependent queries (for example, first retrieving an ID and then using that ID in a subsequent query—this is not allowed).
- For complex queries with multiple CTEs, build incrementally: execute and verify each CTE's output before adding the next. Do NOT jump straight to the full assembled query.
- Be THOROUGH when constructing the final query. Make sure you have the FULL picture before finishing. Use additional tool calls as needed.

Visualization:
- After running the final query, call `render_chart` with a Vega-Lite JSON spec if the result lends itself to a chart (e.g. counts by category, trends over time, distributions).
- `render_chart` accepts an optional `record_id`. Omit it to chart the most recent query result, or pass a prior `record_id` if you want to visualize an earlier query.
- Do NOT render charts for single-row results, heterogeneous tables, or when the user only asks for a specific value.
- Supported marks: bar, line, point, rect. Only simple specs with x/y encoding are supported.
- Prefer bar for categorical comparisons, line for time series, point for correlations.
</tool_calling>
""".strip()


@dataclass
class ChatResult:
    """Result of a single chat turn."""

    text: str
    query: str | None = None
    df: pd.DataFrame | None = None
    chart_spec: dict[str, object] | None = None
    chart_df: pd.DataFrame | None = None
    query_lexer: str = "sql"


@dataclass
class Toolset:
    """Typed bundle of agent tools."""

    run_query: RegistryRunQueryTool
    get_column_json_schema: RegistryGetColumnJsonSchemaTool
    get_table_schema: RegistryGetTableSchemaTool
    render_chart: RenderPlotextChartTool


@dataclass
class ChatAgent:
    """Streaming agent for interactive database chat.

    Uses registry-based tools so the agent targets databases by alias.
    """

    registry: DBRegistry
    console_width: int
    model: str
    max_steps: int = 20
    _message_history: list[ModelMessage] = field(default_factory=list)
    _system_prompt: str = SYSTEM_PROMPT
    _pydantic_ai_agent: Agent[None, str] | None = None
    _query_history: QueryHistory = field(init=False)
    _tools: Toolset = field(init=False)

    def __post_init__(self) -> None:
        from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
        from mintq.toolhub.registry_get_column_json_schema import RegistryGetColumnJsonSchemaTool
        from mintq.toolhub.registry_get_table_schema import RegistryGetTableSchemaTool
        from mintq.toolhub.registry_run_query import QueryHistory, RegistryRunQueryTool
        from mintq.toolhub.render_chart import RenderPlotextChartTool

        self._query_history = QueryHistory()
        self._tools = Toolset(
            run_query=RegistryRunQueryTool(self.registry, history=self._query_history),
            get_column_json_schema=RegistryGetColumnJsonSchemaTool(self.registry),
            get_table_schema=RegistryGetTableSchemaTool(self.registry, SQLDDLSchemaFormatter(), compress=True),
            render_chart=RenderPlotextChartTool(history=self._query_history, width=self.console_width),
        )
        self._build_agent()

    def set_model(self, model: str) -> None:
        """Update model and rebuild the bound runtime agent."""
        if self.model == model:
            return
        self.model = model
        self._build_agent()

    @staticmethod
    def database_info(connector: "NL2QDBConnector") -> str:
        """Build a concise database summary string for agent/user display."""
        from mintq.db_connector import Neo4jConnector

        if isinstance(connector, Neo4jConnector):
            n_labels = len(connector.schema.nodes)
            n_patterns = len(connector.schema.relationships)
            return f"cypher, {n_labels} label{'s' if n_labels != 1 else ''}, {n_patterns} rel pattern{'s' if n_patterns != 1 else ''}"

        n_tables = len(connector.schema.tables) if connector.schema else 0
        dialect = connector.language or "unknown"
        return f"{dialect}, {n_tables} tables"

    def add_database(self, databases: list[tuple[str, "NL2QDBConnector"]]) -> None:
        """Append a synthetic user message about newly registered databases."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        if not databases:
            return
        lines = ["Databases registered and now available (use these aliases in db_alias):"]
        for alias, connector in databases:
            lines.append(f"- {alias}: {self.database_info(connector)}")
        content = "\n".join(lines)
        self._message_history.append(ModelRequest(parts=[UserPromptPart(content=content)]))

    def _build_agent(self) -> None:
        """Build the pydantic-ai agent with current model and tools."""
        from pydantic_ai import Agent

        self._pydantic_ai_agent = Agent(
            model=self.model,
            tools=[
                self._tools.run_query.as_pydantic_ai_tool(),
                self._tools.get_table_schema.as_pydantic_ai_tool(),
                self._tools.get_column_json_schema.as_pydantic_ai_tool(),
                self._tools.render_chart.as_pydantic_ai_tool(),
            ],
            instructions=self._system_prompt,
            model_settings={},
        )

    async def run(
        self,
        question: str,
        console: Console,
    ) -> ChatResult:
        """Run the agent on a user question, streaming progress to the console."""
        from pydantic_ai.run import AgentRunResultEvent

        from mintq.cli.display import render_agent_progress

        progress = render_agent_progress(console)
        progress.start()

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

        finally:
            progress.finish()

        return _build_chat_result(
            answer_text,
            self._query_history,
        )


def _build_chat_result(
    answer_text: str,
    query_history: QueryHistory,
) -> ChatResult:
    """Parse ``[[result:Q<id>]]`` from the answer and build a ChatResult."""
    selected_record = None
    query: str | None = None
    df: pd.DataFrame | None = None
    chart_spec: dict[str, object] | None = None
    chart_df: pd.DataFrame | None = None
    query_lexer = "sql"

    match = _QUERY_REF_RE.search(answer_text)
    if match:
        record_id = match.group(1)
        try:
            selected_record = query_history.get(record_id)
        except (KeyError, ValueError):
            pass
        display_text = _QUERY_REF_RE.sub("", answer_text).strip()
    else:
        display_text = answer_text
        try:
            selected_record = query_history.last()
        except ValueError:
            pass

    if selected_record is not None:
        pred = selected_record.pred_query
        query = pred.query
        df = pred.exec_result.df if pred.exec_result else None
        query_lexer = "cypher" if selected_record.connector_type == "property_graph" else "sql"
        chart_spec = selected_record.vegalite_spec
        if chart_spec is not None and pred.exec_result is not None and pred.exec_result.df is not None:
            chart_df = pred.exec_result.df

    return ChatResult(
        text=display_text,
        query=query,
        df=df,
        chart_spec=chart_spec,
        chart_df=chart_df,
        query_lexer=query_lexer,
    )


# ---------------------------------------------------------------------------
# Stream event handlers for progress display
# ---------------------------------------------------------------------------


def _handle_stream_event(
    event: object,
    progress: AgentProgressDisplay,
    query_history: QueryHistory,
    get_table_schema_tool: RegistryGetTableSchemaTool | None,
) -> None:
    """Dispatch a single stream event to the progress display."""
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


class AgentProgressDisplay:
    """Tracks and renders agent execution progress via Rich Live."""

    def __init__(self, console: Console) -> None:
        from rich.live import Live

        self._console = console
        self._steps: list[tuple[str, str, str]] = []
        self._streaming_text = ""
        self._status_text: str | None = "Thinking..."
        self._live = Live(console=console, refresh_per_second=12)

    def start(self) -> None:
        self._live.start()
        self._update()

    def set_status(self, text: str) -> None:
        self._status_text = text
        self._update()

    def finish(self) -> None:
        self._streaming_text = ""
        self._update()
        self._live.stop()

    def tool_start(self, name: str, args_summary: str) -> None:
        if self._status_text and self._status_text != "Thinking...":
            self._steps.append(("done", "__status__", self._status_text))
        label = f"{name}({args_summary})" if args_summary else name
        self._steps.append(("running", name, label))
        self._streaming_text = ""
        self._status_text = None
        self._update()

    def tool_end(self, name: str, result_summary: str) -> None:
        for i in range(len(self._steps) - 1, -1, -1):
            if self._steps[i][1] == name and self._steps[i][0] == "running":
                label = self._steps[i][2]
                self._steps[i] = ("done", name, f"{label} → {result_summary}")
                break
        self._status_text = "Thinking..."
        self._update()

    def text_delta(self, delta: str) -> None:
        self._streaming_text += delta
        self._status_text = None
        self._update()

    def _update(self) -> None:
        from rich.console import Group
        from rich.spinner import Spinner
        from rich.text import Text

        parts: list[object] = []

        from mintq.cli.theme import ACCENT

        has_running = False
        for status, _name, label in self._steps:
            if status == "running":
                has_running = True
                parts.append(Spinner("dots", text=Text(label, style="dim"), style="dim"))
            else:
                line = Text()
                line.append("✓ ", style="dim")
                line.append(label, style="dim")
                parts.append(line)

        if self._status_text and not has_running:
            parts.append(Spinner("dots", text=Text(self._status_text, style="dim"), style=ACCENT))

        if self._streaming_text:
            display = self._streaming_text
            if len(display) > 500:
                display = "..." + display[-497:]
            parts.append(Text())
            parts.append(Text(display, style="dim"))

        self._live.update(Group(*parts) if parts else Text())  # type: ignore[arg-type]
