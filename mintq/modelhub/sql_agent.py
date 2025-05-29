from dataclasses import dataclass
import jinja2
import time
import pandas as pd
import numpy as np
from tabulate import tabulate
import sqlalchemy
from sqlalchemy import select, distinct
import pydantic_ai
from pydantic_ai import Agent, RunContext
from pydantic_ai.tools import Tool
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.schema_formatter import BaseSQLSchemaFormatter
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput, SQLTableSchema
from mintq.modelhub.pydantic_ai_utils import get_pydantic_ai_llm, pydantic_ai_messages_to_trajectory
from mintq.utils import extract_code, get_llm_api_cost


@dataclass
class TaskContext:
    task: SimpleNL2QTask
    db_connector: BaseAsyncSQLDBConnector
    formatter: BaseSQLSchemaFormatter
    table_id_to_schema: dict[str, SQLTableSchema]


SYSTEM_PROMPT = """
You are MintQ agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- Utilize the provided hints to guide query formulation.
- The final output should not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, the final query should not return the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, the final query should not return the score.
  - If the question asks for the list of objects (e.g. students), return only the IDs of the objects.
- The final output should only include the SQL query, without explanation or any other text.
- Before returning the final output, always execute the query and check if the results match the question.
{% if language == "SnowflakeSQL" %}
- For Snowflake SQL, the column names must be quoted with double quotes (e.g. SELECT ORDER."product_id").
{% endif %}
""".strip()


TASK_PROMPT = """
Question: {{question}}
{% if hints %}
=== START OF HINTS ===
{{hints}}
=== END OF HINTS ===
{% endif %}
=== START OF DATABASE SCHEMA ===
{{schema}}
=== END OF DATABASE SCHEMA ===

{{language}} query:
""".strip()


def get_system_prompt(ctx: RunContext[TaskContext]) -> str:
    return jinja2.Template(SYSTEM_PROMPT).render(language=ctx.deps.task.language)


def truncate(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[: max_chars // 2] + "\n...content truncated...\n" + s[-max_chars // 2 :]


def format_df(df: pd.DataFrame, *, max_visible_rows: int = 5, tablefmt: str = "simple") -> str:
    n = len(df)
    if n > max_visible_rows:
        first_n = (max_visible_rows + 1) // 2
        last_n = max_visible_rows - first_n
        head = df.head(first_n)
        tail = df.tail(last_n)
        ellipsis_row = {col: "..." for col in df.columns}
        display_df = pd.concat([head, pd.DataFrame([ellipsis_row]), tail], ignore_index=True)
    else:
        display_df = df

    display_df = display_df.replace({np.nan: "[null]"})

    # showindex=False hides the automatic row numbers
    return tabulate(display_df, headers="keys", tablefmt=tablefmt, showindex=False, floatfmt=".2f", missingval="[null]")


async def run_query(ctx: RunContext[TaskContext], query: str) -> str:
    """
    Execute a SQL query and return the results.

    Args:
        query: The SQL query to execute.
    """
    db_connector = ctx.deps.db_connector
    try:
        df = await db_connector.run_query_async(query, return_df=True)
    except Exception as e:
        return f"(query failed: {e})"

    if df.empty:  # type: ignore
        return "(Warning: query executed successfully, but results are empty, the query might be incorrect)"

    res = format_df(df, max_visible_rows=5)

    if df.isnull().all().any():
        res += "\n(Warning: a column is entirely null, the query might be incorrect)"
    return res


async def list_columns(ctx: RunContext[TaskContext], table: str) -> str:
    """
    List the columns of a table.

    Args:
        table: The name of the table to list the columns of.
    """
    try:
        table_schema = ctx.deps.table_id_to_schema[table]
    except KeyError:
        return f"(table {table} not found)"
    if not table_schema.columns:
        return f"(table {table} has no columns)"
    res = f"[Table] {table}\n"
    res += "\n".join([ctx.deps.formatter.format_column(table_schema, col) for col in table_schema.columns])
    return res


async def search_keywords(ctx: RunContext[TaskContext], table: str, column: str, keywords: list[str]) -> str:
    """
    Search for values in a column of a table that match any of the keywords.

    Args:
        table: The name of the table to search in.
        column: The name of the column to search in. The datatype of the column must be a string.
        keywords: A list of keywords to search for. A value is considered a match if it contains any of the keywords.
    """
    db_connector = ctx.deps.db_connector

    # Remove the quote characters from the column name if they exist
    for quote_char in '"`':
        if column.startswith(quote_char) and column.endswith(quote_char):
            column = column[1:-1]
            break

    if table not in ctx.deps.table_id_to_schema:
        return f"(table {table} not found)"

    column_dtypes = {col.name: col.dtype for col in ctx.deps.table_id_to_schema[table].columns}
    if column not in column_dtypes:
        return f"(column {column} not found in table {table})"
    if column_dtypes[column] not in ("VARCHAR", "TEXT", "STRING"):
        return f"(column {column} is not a string)"

    matches = []
    for keyword in keywords:
        sql_table = sqlalchemy.Table(table, sqlalchemy.MetaData(), sqlalchemy.Column(column, sqlalchemy.String))
        stmt = select(distinct(sql_table.c[column])).where(sql_table.c[column].like(f"%{keyword}%"))
        result = await db_connector.run_query_async(stmt)
        matches += [row[0] for row in result]
    matches = sorted(list(set(matches)))
    if not matches:
        return "(no matches found)"

    res = f"{len(matches)} matches:\n"
    res += "\n".join(matches[:10])
    if len(matches) > 10:
        res += "\n..."
    return res


class SQLAgent:
    name = "sql_agent"

    def __init__(
        self, llm: str, schema_formatter: BaseSQLSchemaFormatter, temperature: float = 0.0, num_candidates: int = 1
    ):
        self.llm = llm
        self.temperature = temperature
        self.num_candidates = num_candidates
        self.agent = Agent(
            get_pydantic_ai_llm(llm),
            tools=[Tool(list_columns), Tool(search_keywords), Tool(run_query)],
            deps_type=TaskContext,
            instructions=get_system_prompt,
        )
        self.agent_no_tools = Agent(
            get_pydantic_ai_llm(llm),
            tools=[],
            deps_type=TaskContext,
            instructions=get_system_prompt,
        )
        self.formatter = schema_formatter

    def get_config(self) -> dict[str, str | int | float | bool]:
        return {
            "llm": self.llm,
            "temperature": self.temperature,
            "schema_formatter": self.formatter.name,
            "num_candidates": self.num_candidates,
        }

    async def predict_async(self, task: SimpleNL2QTask, db_connector: BaseAsyncSQLDBConnector) -> SimpleNL2QTaskOutput:
        t0 = time.time()

        prompt = jinja2.Template(TASK_PROMPT).render(
            schema=self.formatter.format(db_connector.schema, include_table_schemas=False),
            hints=task.evidence,
            question=task.question,
            language=task.language,
        )

        # Construct dependencies
        table_id_to_schema = {self.formatter.format_table_name(table): table for table in db_connector.schema.tables}
        deps = TaskContext(
            task=task,
            db_connector=db_connector,
            formatter=self.formatter,
            table_id_to_schema=table_id_to_schema,
        )

        # Run the agent
        try:
            result = await self.agent.run(prompt, deps=deps, model_settings={"temperature": self.temperature})
        except pydantic_ai.exceptions.UsageLimitExceeded:
            result = await self.agent_no_tools.run(prompt, deps=deps, model_settings={"temperature": self.temperature})

        pred_query = extract_code(result.output)
        trajectory = pydantic_ai_messages_to_trajectory(result.all_messages())

        usage = result.usage()
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["api_calls"] = usage.requests
        metrics["input_tokens"] = usage.request_tokens if usage.request_tokens else 0
        metrics["output_tokens"] = usage.response_tokens if usage.response_tokens else 0
        metrics["api_cost_usd"] = get_llm_api_cost(self.llm, metrics["input_tokens"], metrics["output_tokens"])  # type: ignore
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            metrics=metrics,
        )
