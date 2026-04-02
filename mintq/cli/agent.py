"""CLI chat agent — streaming pydantic-ai agent for interactive SQL chat."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import jinja2
from rich.console import Console

if TYPE_CHECKING:
    import pandas as pd
    from pydantic_ai.messages import ModelMessage

    from mintq.db_connector.db_registry import DBRegistry
    from mintq.toolhub.registry_run_query import RegistryRunQueryTool
    from mintq.toolhub.registry_get_table_schema import RegistryGetTableSchemaTool

logger = logging.getLogger(__name__)

_QUERY_REF_RE = re.compile(r"\[\[result:(Q\d+)\]\]")

SYSTEM_PROMPT_TEMPLATE = jinja2.Template(
    """\
You are the mintq agent, a helpful database assistant that answers the user's question by querying the database.
You are an agent - please keep going until the task is solved.

<available_databases>
{% for db in databases -%}
- {{ db.alias }} ({{ db.info }})
{% endfor -%}
</available_databases>

<goal>
- If the question is ambiguous, pick the most natural interpretation and proceed. Only ask for clarifications if you are truly blocked.
- All database tools require a `db_alias` parameter to specify which database to target.
{%- if single_alias %}
- The only connected database is "{{ single_alias }}", so always use db_alias="{{ single_alias }}".
{%- endif %}
- Your final response should be a clear concise natural language answer summarizing the results.
- Do not put the query in the final response unless explicitly asked to.
- Do not include the query execution results in the final response. The execution results will be rendered in a separate view to the user.
- IMPORTANT: In your final response, include [[result:Q<id>]] to reference the query whose results answer the user's question. Use the query_id shown in each tool response (e.g. [[result:Q3]]). This tells the system which query and data to display alongside your answer.
</goal>

<tool_calling>
Gathering information:
{%- if has_graph %}
- For graph databases, the schema is provided in <db_document>. Read it before writing Cypher.
- You may use `run_query` to run exploratory Cypher queries when that helps clarify the graph.
{%- endif %}
{%- if has_sql %}
- For SQL databases, always use `get_table_schema` to get the schema of relevant tables before constructing the query.
- You may use `get_column_json_schema` to inspect the internal structure of semi-structured columns (e.g. VARIANT, OBJECT, ARRAY, JSON, JSONB).
- You may use `run_query` to inspect some sample values to determine the data format if necessary.
{%- endif %}

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
{%- endif %}"""
)


@dataclass
class ChatResult:
    """Result of a single chat turn."""

    text: str
    sql: str | None = None
    df: pd.DataFrame | None = None
    chart_spec: dict[str, object] | None = None
    chart_df: pd.DataFrame | None = None
    query_lexer: str = "sql"


@dataclass
class ChatAgent:
    """Streaming agent for interactive database chat.

    Uses registry-based tools so the agent targets databases by alias.
    """

    model: str
    summarizer_model: str = "openai-responses:gpt-5-mini"
    max_steps: int = 20
    _db_summaries: dict[str, str] = field(default_factory=dict)
    _message_history: list[ModelMessage] = field(default_factory=list)

    _SUMMARIZE_MIN_TABLES = 20

    async def _get_db_document(
        self,
        alias: str,
        connector: object,
        progress: AgentProgressDisplay,
    ) -> str | None:
        """Build a schema document for a single database.

        Returns the formatted schema text, or None if no document should be
        included in the system prompt (e.g. large SQL databases where the agent
        should use tools instead).
        """
        from mintq.db_connector import Neo4jConnector
        from mintq.db_connector.base import BaseSQLDBConnector

        cache_key = getattr(connector, "global_id", alias)
        if cache_key in self._db_summaries:
            return self._db_summaries[cache_key]

        if isinstance(connector, Neo4jConnector):
            from mintq.formatters.cypher import CypherSchemaFormatter

            doc = CypherSchemaFormatter().format(connector.schema)
            self._db_summaries[cache_key] = doc
            return doc

        from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
        from mintq.preprocessors.components.schema_compressor import SchemaCompressor
        from mintq.preprocessors.db_summarizer import DBSummarizer

        sql_conn: BaseSQLDBConnector = connector  # type: ignore[assignment]
        schema = sql_conn.schema
        if len(schema.tables) < self._SUMMARIZE_MIN_TABLES:
            compressor = SchemaCompressor()
            compressed = compressor.compress(schema)
            formatter = SQLDDLSchemaFormatter()
            doc = formatter.format(compressed, add_description=True)
        else:
            progress.set_status(f"Summarizing {alias}...")
            summarizer = DBSummarizer(llm=self.summarizer_model)
            summary = await summarizer.preprocess_async(sql_conn)
            doc = summary.db_summary_markdown

        self._db_summaries[cache_key] = doc
        return doc

    async def run(
        self,
        question: str,
        registry: DBRegistry,
        console: Console,
    ) -> ChatResult:
        """Run the agent on a user question, streaming progress to the console."""
        from pydantic_ai import Agent
        from pydantic_ai.run import AgentRunResultEvent

        from mintq.cli.display import render_agent_progress
        from mintq.db_connector import Neo4jConnector
        from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
        from mintq.toolhub.registry_get_column_json_schema import RegistryGetColumnJsonSchemaTool
        from mintq.toolhub.registry_get_table_schema import RegistryGetTableSchemaTool
        from mintq.toolhub.registry_run_query import RegistryRunQueryTool
        from mintq.toolhub.render_chart import RenderPlotextChartTool

        progress = render_agent_progress(console)
        progress.start()

        try:
            aliases = registry.list_aliases()
            has_sql = False
            has_graph = False
            db_infos: list[dict[str, str]] = []
            db_doc_parts: list[str] = []

            for alias in aliases:
                conn = registry.get(alias)
                if isinstance(conn, Neo4jConnector):
                    has_graph = True
                    n_labels = len(conn.schema.nodes)
                    n_rels = len(conn.schema.relationships)
                    db_infos.append(
                        {
                            "alias": alias,
                            "info": f"cypher, {n_labels} labels, {n_rels} rel patterns",
                        }
                    )
                else:
                    has_sql = True
                    schema = conn.schema
                    dialect = getattr(schema, "dialect", "sql")
                    n_tables = len(schema.tables)
                    db_infos.append(
                        {
                            "alias": alias,
                            "info": f"{dialect}, {n_tables} tables",
                        }
                    )

                doc = await self._get_db_document(alias, conn, progress)
                if doc:
                    header = f"## Database: {alias}"
                    db_doc_parts.append(f"{header}\n\n{doc}")

            db_document = "\n\n".join(db_doc_parts) if db_doc_parts else None
            single_alias = aliases[0] if len(aliases) == 1 else None

            system_prompt = SYSTEM_PROMPT_TEMPLATE.render(
                databases=db_infos,
                single_alias=single_alias,
                has_sql=has_sql,
                has_graph=has_graph,
                db_document=db_document,
            )

            run_query_tool = RegistryRunQueryTool(registry)
            render_chart_tool = RenderPlotextChartTool(run_query_tool, width=console.width)

            tools = [run_query_tool.as_pydantic_ai_tool()]

            get_table_schema_tool: RegistryGetTableSchemaTool | None = None
            if has_sql:
                formatter = SQLDDLSchemaFormatter()
                get_table_schema_tool = RegistryGetTableSchemaTool(
                    registry,
                    formatter,
                    compress=True,
                )
                get_column_json_schema_tool = RegistryGetColumnJsonSchemaTool(registry)
                tools.append(get_table_schema_tool.as_pydantic_ai_tool())
                tools.append(get_column_json_schema_tool.as_pydantic_ai_tool())

            tools.append(render_chart_tool.as_pydantic_ai_tool())

            agent: Agent[None, str] = Agent(
                model=self.model,
                tools=tools,
                instructions=system_prompt,
                model_settings={},
            )

            answer_text = ""
            async for event in agent.run_stream_events(
                question,
                message_history=self._message_history or None,
            ):
                if isinstance(event, AgentRunResultEvent):
                    self._message_history = list(event.result.all_messages())
                    answer_text = event.result.output
                    break

                _handle_stream_event(event, progress, run_query_tool, get_table_schema_tool)

        finally:
            progress.finish()

        return _build_chat_result(
            answer_text,
            run_query_tool,
            render_chart_tool,
            registry,
        )


def _build_chat_result(
    answer_text: str,
    run_query_tool: RegistryRunQueryTool,
    render_chart_tool: object,
    registry: DBRegistry,
) -> ChatResult:
    """Parse ``[[result:Q<id>]]`` from the answer and build a ChatResult."""
    from mintq.toolhub.render_chart import RenderPlotextChartTool

    assert isinstance(render_chart_tool, RenderPlotextChartTool)

    sql: str | None = None
    df: pd.DataFrame | None = None
    query_lexer = "sql"

    match = _QUERY_REF_RE.search(answer_text)
    if match:
        query_id = match.group(1)
        try:
            record = run_query_tool.get_query_record(query_id)
            pred = record.pred_query
            sql = pred.query
            df = pred.exec_result.df if pred.exec_result else None
            connector = registry.get(record.db_alias)
            query_lexer = "cypher" if connector.connector_type == "property_graph" else "sql"
        except (KeyError, ValueError):
            pass
        display_text = _QUERY_REF_RE.sub("", answer_text).strip()
    else:
        display_text = answer_text
        try:
            pred = run_query_tool.last_pred_query()
            sql = pred.query
            df = pred.exec_result.df if pred.exec_result else None
        except ValueError:
            pass

    return ChatResult(
        text=display_text,
        sql=sql,
        df=df,
        chart_spec=render_chart_tool.last_vegalite_spec,
        chart_df=render_chart_tool.last_chart_df,
        query_lexer=query_lexer,
    )


# ---------------------------------------------------------------------------
# Stream event handlers for progress display
# ---------------------------------------------------------------------------


def _handle_stream_event(
    event: object,
    progress: AgentProgressDisplay,
    run_query_tool: RegistryRunQueryTool,
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
        result_summary = _summarize_result(result_tool_name, run_query_tool, get_table_schema_tool)
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
    run_query_tool: RegistryRunQueryTool,
    get_table_schema_tool: RegistryGetTableSchemaTool | None,
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
