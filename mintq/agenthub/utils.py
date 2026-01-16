from typing import Any, Callable, Literal
from functools import partial, wraps
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import build_scope, Scope
from opentelemetry import trace
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from pydantic import BaseModel
from mintq.schema import NL2QTask, SQLSchema
from mintq.config import config
from mintq.db_connector import NL2QDBConnector
from mintq.schema import Usage, Trajectory
from mintq.toolhub import BaseTool


def max_steps_processor(
    ctx: RunContext[Any],
    messages: list[ModelMessage],
    max_steps: int,
) -> list[ModelMessage]:
    if ctx.run_step >= max_steps - 1:
        if ctx.run_step == max_steps - 1:
            content = "You are about to reach the maximum number of steps. You have one more attempt to execute a tool before submitting the final answer."
        else:
            content = "You have reached the maximum number of steps. Please submit the final answer right now."
        msg = ModelRequest(parts=[UserPromptPart(content=content)])
        assert messages == ctx.messages
        ctx.messages.append(msg)
        return ctx.messages
    return messages


def get_max_steps_processor(max_steps: int) -> Any:
    assert max_steps >= 1
    return partial(max_steps_processor, max_steps=max_steps)


def instrument(predict_async_fn: Callable[..., Any]) -> Callable[..., Any]:
    if not config.instrument_enabled:
        return predict_async_fn

    @wraps(predict_async_fn)
    async def wrapper(self: Any, task: NL2QTask, *args: Any, **kwargs: Any) -> Any:
        from mintq import __version__

        tracer_provider = trace.get_tracer_provider()
        tracer = tracer_provider.get_tracer("mintq", __version__)

        current_span = trace.get_current_span()

        if current_span and current_span.get_span_context().is_valid:
            # Already inside a span, do not start a new span
            return await predict_async_fn(self, task, *args, **kwargs)

        span_name = f"qid={task.qid}".strip()
        if config.instrument_prefix:
            span_name = f"{config.instrument_prefix} | {span_name}"
        with tracer.start_as_current_span(span_name):
            return await predict_async_fn(self, task, *args, **kwargs)

    return wrapper


@dataclass
class TaskRunContext:
    task: NL2QTask
    db_connector: NL2QDBConnector
    usage: Usage
    tools: dict[str, BaseTool] = field(default_factory=dict)
    trajectories: list[Trajectory] = field(default_factory=list)


class BasicAgentConfig(BaseModel):
    llm: str
    schema_formatter: str = "sql_default"
    compress_schema: bool = True
    temperature: float = 0.0
    max_steps: int = 10
    openai_reasoning_effort: Literal["none", "minimal", "low", "medium", "high"] | None = None
    openai_reasoning_summary: Literal["detailed", "concise"] | None = None

    def to_model_settings(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        res["temperature"] = self.temperature
        if self.openai_reasoning_effort is not None:
            res["openai_reasoning_effort"] = self.openai_reasoning_effort
        if self.openai_reasoning_summary is not None:
            res["openai_reasoning_summary"] = self.openai_reasoning_summary
        return res


def extract_all_source_columns(
    query: str, schema: SQLSchema | None = None, language: str = "sqlite"
) -> list[tuple[str, str]]:
    """
    Extracts ALL source columns used anywhere in the query (SELECT, WHERE, JOIN, ORDER BY, GROUP BY, etc.).

    Resolves table aliases and traces columns through CTEs and subqueries back to their
    original source tables. Preserves the original case of table and column names as they
    appear in the query.

    Args:
        query: SQL query string to analyze
        schema: Optional SQL schema to use for resolving SELECT *
        dialect: SQL dialect for parsing (e.g., "sqlite", "postgres", "mysql", "snowflake")

    Returns:
        List of (table_name, column_name) tuples for all source columns referenced
        in the query. Returns an empty list if the query cannot be parsed.

    Example:
        >>> query = '''
        ... WITH recent_orders AS (
        ...   SELECT o.user_id, o.total, o.order_dates
        ...   FROM orders o
        ... )
        ... SELECT u.id, ro.total
        ... FROM users u
        ... JOIN recent_orders ro ON u.id = ro.user_id
        ... '''
        >>> extract_all_source_columns(query, schema)
        [('orders', 'user_id'), ('orders', 'total'), ('orders', 'order_dates'), ('users', 'id')]
    """
    # Convert SQLSchema to sqlglot's schema format for qualify (if provided)
    sqlglot_schema: dict[str, dict[str, str]] | None = None
    if schema is not None:
        sqlglot_schema = {}
        for table in schema.tables:
            table_name = table.name
            sqlglot_schema[table_name] = {col.name: col.dtype for col in table.columns}

    try:
        parsed = sqlglot.parse_one(query, dialect=language)

        # Build case mapping before normalization: lowercase -> original case
        # This captures the original case of identifiers before qualify() normalizes them
        col_case_map: dict[str, str] = {}  # lowercase col name -> original col name
        table_case_map: dict[str, str] = {}  # lowercase table name -> original table name

        for col in parsed.find_all(exp.Column):
            original_col_name = col.name
            col_case_map[original_col_name.lower()] = original_col_name

        for table in parsed.find_all(exp.Table):
            original_table_name = table.name
            table_case_map[original_table_name.lower()] = original_table_name

        qualified = qualify(parsed, schema=sqlglot_schema, dialect=language, validate_qualify_columns=False)
        root = build_scope(qualified)
    except Exception:
        return []

    if root is None:
        return []

    def collect_columns(scope: Scope, result: list[tuple[str, str]], seen: set[tuple[str, str]]) -> None:
        """Recursively collect source columns from a scope and all nested scopes."""
        for col in scope.columns:
            table_alias = col.table
            col_name = col.name

            source = scope.sources.get(table_alias)
            if isinstance(source, exp.Table):
                # Direct table reference - resolve alias to actual table name
                table_name = source.name
                # Restore original case using the mapping
                original_table = table_case_map.get(table_name, table_name)
                original_col = col_case_map.get(col_name, col_name)
                key = (original_table, original_col)
                if key not in seen:
                    result.append(key)
                    seen.add(key)

        # Process CTE scopes (WITH clause definitions)
        for cte_scope in scope.cte_scopes:
            collect_columns(cte_scope, result, seen)

        # Process derived table scopes (subqueries in FROM/JOIN)
        for source in scope.sources.values():
            if isinstance(source, Scope):
                collect_columns(source, result, seen)

    result: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    collect_columns(root, result, seen)
    return result
