"""CLI chat agent — streaming pydantic-ai agent for interactive SQL chat."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import jinja2
from rich.console import Console

if TYPE_CHECKING:
    import pandas as pd
    from pydantic_ai.messages import ModelMessage

    from mintq.db_connector.base import BaseSQLDBConnector

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are the mintq agent, a helpful database assistant that answers the user's question by querying the database.
You are an agent - please keep going until the task is solved.

<goal>
- If the question is ambiguous, pick the most natural interpretation and proceed. Only ask for clarifications if you are truly blocked.
- Write {{ language }} queries.
- Your final response should be a clear concise natural language answer summarizing the results.
- Do not put the SQL query in the final response unless explicitly asked to.
</goal>

<tool_calling>
Gathering information:
- Always use the `get_table_schema` tool to get the schema of the relevant tables before constructing the query.
- You may use the `get_column_json_schema` tool to inspect the internal structure of semi-structured columns (e.g. VARIANT, OBJECT, ARRAY, JSON, JSONB).
- You may use `run_query` to inspect some sample values to determine the data format if necessary.

Writing the task query:
- Ensure you have collected enough information and fully understand the database structure before composing the task query.
- You may execute intermediate or exploratory queries multiple times; however, the final query (the last one executed) must be complete and fully constructed. In the final query, do not split the logic into multiple dependent queries (for example, first retrieving an ID and then using that ID in a subsequent query—this is not allowed).
- For complex queries with multiple CTEs, build incrementally: execute and verify each CTE's output before adding the next. Do NOT jump straight to the full assembled query.
- Be THOROUGH when constructing the final query. Make sure you have the FULL picture before finishing. Use additional tool calls as needed.

Visualization:
- After running the final query, call `render_chart` with a Vega-Lite JSON spec if the result lends itself to a chart (e.g. counts by category, trends over time, distributions).
- Do NOT render charts for single-row results, heterogeneous tables, or when the user only asks for a specific value.
- Supported marks: bar, line, point, rect. Only simple specs with x/y encoding are supported.
- Prefer bar for categorical comparisons, line for time series, point for correlations.
</tool_calling>

{%- if db_document %}

<db_document>
{{ db_document }}
</db_document>
{%- endif %}
""".strip()


@dataclass
class ChatResult:
    """Result of a single chat turn."""

    text: str
    sql: str | None = None
    df: pd.DataFrame | None = None
    chart_spec: dict | None = None
    chart_df: pd.DataFrame | None = None


@dataclass
class ChatAgent:
    """Streaming agent for interactive SQL chat.

    Manages DB summarization (cached per connector) and runs a pydantic-ai
    agent with get_table_schema + run_query tools, streaming events to the
    console.
    """

    model: str
    summarizer_model: str = "openai-responses:gpt-5-mini"
    max_steps: int = 20
    _db_summaries: dict[str, str] = field(default_factory=dict)
    _message_history: dict[str, list[ModelMessage]] = field(default_factory=dict)

    _SUMMARIZE_MIN_TABLES = 20

    async def _get_db_document(
        self,
        connector: BaseSQLDBConnector,
        progress: AgentProgressDisplay,
    ) -> str:
        """Build a database document for the system prompt.

        For small databases (< _SUMMARIZE_MIN_TABLES tables), formats the
        compressed schema directly using SQLDDLSchemaFormatter.  For larger
        databases, runs the LLM-based DBSummarizer.
        """
        cache_key = connector.global_id
        if cache_key in self._db_summaries:
            return self._db_summaries[cache_key]

        from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
        from mintq.preprocessors.components.schema_compressor import SchemaCompressor
        from mintq.preprocessors.db_summarizer import DBSummarizer

        schema = connector.schema
        if len(schema.tables) < self._SUMMARIZE_MIN_TABLES:
            compressor = SchemaCompressor()
            compressed = compressor.compress(schema)
            formatter = SQLDDLSchemaFormatter()
            doc = formatter.format(compressed, add_description=True)
        else:
            progress.set_status("Summarizing database...")
            summarizer = DBSummarizer(llm=self.summarizer_model)
            summary = await summarizer.preprocess_async(connector)
            doc = summary.db_summary_markdown

        self._db_summaries[cache_key] = doc
        return doc

    def _history_key(self, connector: BaseSQLDBConnector) -> str:
        return connector.global_id

    async def run(
        self,
        question: str,
        connector: BaseSQLDBConnector,
        console: Console,
    ) -> ChatResult:
        """Run the agent on a user question, streaming progress to the console."""
        from pydantic_ai import Agent
        from pydantic_ai.run import AgentRunResultEvent

        from mintq.cli.display import render_agent_progress
        from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
        from mintq.toolhub.get_column_json_schema import GetColumnJsonSchemaTool
        from mintq.toolhub.get_table_schema import GetTableSchemaTool
        from mintq.toolhub.render_chart import RenderPlotextChartTool
        from mintq.toolhub.run_query import RunQueryTool

        progress = render_agent_progress(console)
        progress.start()

        try:
            db_document = await self._get_db_document(connector, progress)

            system_prompt = jinja2.Template(SYSTEM_PROMPT).render(
                language=connector.language or "SQL",
                db_document=db_document,
            )

            formatter = SQLDDLSchemaFormatter()
            run_query_tool = RunQueryTool(connector)
            get_table_schema_tool = GetTableSchemaTool(connector, formatter, compress=True)
            get_column_json_schema_tool = GetColumnJsonSchemaTool(connector.schema)
            render_chart_tool = RenderPlotextChartTool(run_query_tool, width=console.width)

            agent: Agent[None, str] = Agent(
                model=self.model,
                tools=[
                    get_table_schema_tool.as_pydantic_ai_tool(),
                    get_column_json_schema_tool.as_pydantic_ai_tool(),
                    run_query_tool.as_pydantic_ai_tool(),
                    render_chart_tool.as_pydantic_ai_tool(),
                ],
                instructions=system_prompt,
                model_settings={},
            )

            history_key = self._history_key(connector)
            message_history = self._message_history.get(history_key)

            answer_text = ""
            last_sql: str | None = None
            async for event in agent.run_stream_events(
                question,
                message_history=message_history,
            ):
                if isinstance(event, AgentRunResultEvent):
                    self._message_history[history_key] = list(event.result.all_messages())
                    answer_text = event.result.output
                    break

                _handle_stream_event(event, progress, run_query_tool, get_table_schema_tool)

        finally:
            progress.finish()

        try:
            pred = run_query_tool.last_pred_query()
            last_sql = pred.query
            last_df = pred.exec_result.df if pred.exec_result else None
        except ValueError:
            last_df = None

        return ChatResult(
            text=answer_text,
            sql=last_sql,
            df=last_df,
            chart_spec=render_chart_tool.last_vegalite_spec,
            chart_df=render_chart_tool.last_chart_df,
        )


def _handle_stream_event(
    event: object,
    progress: AgentProgressDisplay,
    run_query_tool: object,
    get_table_schema_tool: object,
) -> None:
    """Dispatch a single stream event to the progress display."""
    from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent, PartDeltaEvent, TextPartDelta

    if isinstance(event, FunctionToolCallEvent):
        tool_name = event.part.tool_name
        args = event.part.args
        args_summary = _summarize_args(tool_name, args)
        progress.tool_start(tool_name, args_summary)

    elif isinstance(event, FunctionToolResultEvent):
        tool_name = event.result.tool_name
        result_summary = _summarize_result(tool_name, run_query_tool, get_table_schema_tool)
        progress.tool_end(tool_name, result_summary)

    elif isinstance(event, PartDeltaEvent):
        if isinstance(event.delta, TextPartDelta):
            progress.text_delta(event.delta.content_delta)


def _summarize_args(tool_name: str, args: str | dict | None) -> str:
    if args is None:
        return ""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, TypeError):
            return str(args)[:80]
    if not isinstance(args, dict):
        return str(args)[:80]

    if tool_name == "run_query":
        query = " ".join(args.get("query", "").split())
        if len(query) > 40:
            query = query[:37] + "..."
        return query
    if tool_name == "get_table_schema":
        parts = []
        if args.get("schema_name"):
            parts.append(str(args["schema_name"]))
        parts.append(str(args.get("table_name", "")))
        return ".".join(parts)
    if tool_name == "get_column_json_schema":
        parts = []
        if args.get("schema_name"):
            parts.append(str(args["schema_name"]))
        parts.append(str(args.get("table_name", "")))
        parts.append(str(args.get("column_name", "")))
        label = ".".join(parts)
        if args.get("path"):
            label += f", path={args['path']}"
        return label
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
    run_query_tool: object,
    get_table_schema_tool: object,
) -> str:
    if tool_name == "run_query":
        try:
            pred = run_query_tool.last_pred_query()
            if pred.exec_result and pred.exec_result.df is not None:
                return f"{len(pred.exec_result.df)} rows"
            if pred.exec_result and pred.exec_result.error:
                return "error"
        except ValueError:
            pass
    if tool_name == "get_table_schema":
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
        self._update()

    def text_delta(self, delta: str) -> None:
        self._streaming_text += delta
        self._update()

    def _update(self) -> None:
        from rich.console import Group
        from rich.spinner import Spinner
        from rich.text import Text

        parts: list[object] = []

        if self._status_text and not self._steps:
            parts.append(Spinner("dots", text=Text(self._status_text, style="dim"), style="cyan"))

        for status, _name, label in self._steps:
            if status == "running":
                parts.append(Spinner("dots", text=Text(label, style="dim"), style="dim"))
            else:
                line = Text()
                line.append("✓ ", style="dim")
                line.append(label, style="dim")
                parts.append(line)

        if self._streaming_text:
            display = self._streaming_text
            if len(display) > 500:
                display = "..." + display[-497:]
            parts.append(Text())
            parts.append(Text(display, style="dim"))

        self._live.update(Group(*parts) if parts else Text())
