from dataclasses import dataclass
import jinja2
import time
import pandas as pd
import numpy as np
import json
from tabulate import tabulate
import sqlalchemy
from sqlalchemy.sql import quoted_name
from sqlalchemy import select, distinct
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.usage import Usage
from pydantic_ai.tools import Tool
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput, SQLTableSchema, PredQuery, Usage
from mintq.pydantic_ai_utils import get_pydantic_ai_llm, pydantic_ai_messages_to_trajectory
from mintq.utils import extract_code


@dataclass
class TaskContext:
    task: SimpleNL2QTask
    db_connector: BaseAsyncSQLDBConnector
    formatter: BaseSQLSchemaFormatter
    table_id_to_schema: dict[str, SQLTableSchema]
    max_steps: int


SYSTEM_PROMPT = """
You are MintQ agent, a helpful AI database expert that can translate natural language questions into {{language}} queries by leveraging the given tools.

- Ensure the query accurately reflects the original question without adding or omitting any conditions. Do not infer any conditions that are not explicitly stated in the question.
- Adhere strictly to the given database schema when constructing queries.
- Utilize the provided hints to guide query formulation.
- The final query should not return additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, the final query should not return the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, the final query should not return the score.
- For non-digit text columns, always use the `search_keywords` tool to search for the keyword and ensure it exists in the database.
  - Try to search over all possible relevant columns across the database. Try to be very comprehensive.
  - Similarly, include potential synonyms in the keyword list.
- To connect multiple tables, you must use JOIN on one of the Foreign keys in the database schema.
  -  Keep in mind that the records in the tables may not perfectly align: the some entities in one table might not be covered by another table.
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


def add_max_steps_reached(ctx: RunContext[TaskContext], res: str) -> str:
    if ctx.usage.requests == ctx.deps.max_steps:
        res += "\n(Warning: You have reached the maximum number of steps. You have one more attempt to execute the `run_query` tool with the final query and then the `finish` tool)"
    return res


async def run_query(ctx: RunContext[TaskContext], query: str) -> str:
    """
    Execute a SQL query and return the results.

    Args:
        query: The SQL query to execute.
    """
    db_connector = ctx.deps.db_connector
    try:
        exec_result = await db_connector.run_query_async(query)
        df = exec_result.df
    except TimeoutError:
        return "(query timed out after 30 seconds)"
    except Exception as e:
        return f"(query failed: {e})"

    if df.empty:
        return "(Warning: query executed successfully, but results are empty, the query might be incorrect)"

    res = format_df(df, max_visible_rows=5)

    if df.isnull().all().any():
        res += "\n(Warning: a column is entirely null, the query might be incorrect)"
    return add_max_steps_reached(ctx, res)


async def search_keywords(ctx: RunContext[TaskContext], table: str, column: str, keywords: list[str]) -> str:
    """
    Search for values in a column of a table that match any of the keywords.

    Args:
        table: The name of the table to search in.
        column: The name of the column to search in. The datatype of the column must be text-like.
        keywords: A list of keywords to search for. A value is considered a match if it contains any of the keywords.
    """
    db_connector = ctx.deps.db_connector

    # Remove the quote characters from the column name if they exist
    for quote_char in '"`':
        if column.startswith(quote_char) and column.endswith(quote_char):
            column = column[1:-1]
            break

    if table not in ctx.deps.table_id_to_schema:
        ctx.usage.incr(Usage(details={"search_keywords_table_not_found": 1}))
        return f"(table {table} not found)"

    column_dtypes = {col.name: col.dtype for col in ctx.deps.table_id_to_schema[table].columns}
    if column not in column_dtypes:
        ctx.usage.incr(Usage(details={"search_keywords_column_not_found": 1}))
        return f"(column {column} not found in table {table})"
    if column_dtypes[column] not in ("VARCHAR", "TEXT", "STRING"):
        ctx.usage.incr(Usage(details={"search_keywords_column_not_string": 1}))
        return f"(column {column} is not a string)"

    if "." in table:
        schema_name, table_name = table.split(".")
    else:
        schema_name, table_name = None, table
    column_name = quoted_name(column, quote=True)

    matches = []
    for keyword in keywords:
        sql_table = sqlalchemy.Table(
            table_name, sqlalchemy.MetaData(), sqlalchemy.Column(column_name, sqlalchemy.String), schema=schema_name
        )
        stmt = select(distinct(sql_table.c[column_name])).where(sql_table.c[column_name].like(f"%{keyword}%"))
        result = await db_connector.run_query_async(stmt, timeout=None)
        matches += [row[0] for row in result]
    matches = sorted(list(set(matches)))
    if not matches:
        return "(no matches found)"

    res = f"{len(matches)} matches:\n"
    res += "\n".join(matches[:10])
    if len(matches) > 10:
        res += "\n..."
    return add_max_steps_reached(ctx, res)


def finish(ctx: RunContext[TaskContext]) -> str:
    """
    Finish the task and return the last executed query as final answer.
    """
    for msg in ctx.messages[::-1]:
        if msg.kind == "response":
            for part in msg.parts[::-1]:
                if part.part_kind == "tool-call" and part.tool_name == "run_query":
                    if isinstance(part.args, str):
                        return json.loads(part.args)["query"]  # type: ignore
                    elif isinstance(part.args, dict):
                        return part.args["query"]  # type: ignore
                    else:
                        raise ValueError(f"Unexpected tool call argument type: {type(part.args)}")
    ctx.usage.incr(Usage(details={"finish_no_query_executed": 1}))
    raise ModelRetry("No query has been executed, you cannot finish yet")


class SQLAgentV1:
    name = "sql_agent_v1"

    def __init__(
        self,
        llm: str,
        schema_formatter: BaseSQLSchemaFormatter,
        temperature: float = 0.0,
        num_candidates: int = 1,
        max_steps: int = 20,
    ):
        self.llm = llm
        self.temperature = temperature
        self.num_candidates = num_candidates
        self.max_steps = max_steps

        self.agent = Agent[TaskContext, str](  # type: ignore
            get_pydantic_ai_llm(llm),
            tools=[Tool(search_keywords), Tool(run_query)],
            deps_type=TaskContext,
            output_type=finish,
            result_tool_name="finish",
            result_tool_description="Finish the task and return the last executed query as final answer.",
            instructions=get_system_prompt,
        )
        self.agent.instrument_all()
        self.agent_no_tools = Agent[TaskContext, str](
            get_pydantic_ai_llm(llm),
            tools=[],
            deps_type=TaskContext,
            instructions=get_system_prompt,
        )
        self.agent_no_tools.instrument_all()
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
            schema=self.formatter.format(db_connector.schema, pk_fk_column_only=False),
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
            max_steps=self.max_steps,
        )

        # Run the agent
        fallback = False
        try:
            result = await self.agent.run(prompt, deps=deps, model_settings={"temperature": self.temperature})
            messages = result.all_messages()[:-1]
        except (UsageLimitExceeded, UnexpectedModelBehavior) as e:
            print(e)
            result = await self.agent_no_tools.run(prompt, deps=deps, model_settings={"temperature": self.temperature})
            messages = result.all_messages()
            fallback = True
        pred_query = PredQuery(query=extract_code(result.output))
        trajectory = pydantic_ai_messages_to_trajectory(messages)

        usage = result.usage()
        metrics = {}
        metrics["latency_seconds"] = time.time() - t0
        metrics["api_calls"] = usage.requests
        metrics["input_tokens"] = usage.request_tokens if usage.request_tokens else 0
        metrics["output_tokens"] = usage.response_tokens if usage.response_tokens else 0
        metrics["api_cost_usd"] = Usage.get_llm_api_cost(self.llm, metrics["input_tokens"], metrics["output_tokens"])  # type: ignore
        metrics["steps"] = sum(1 for msg in trajectory.messages if msg.role == "assistant")
        metrics["list_columns_table_not_found"] = usage.details.get("list_columns_table_not_found", 0)
        metrics["list_columns_table_has_no_columns"] = usage.details.get("list_columns_table_has_no_columns", 0)
        metrics["search_keywords_table_not_found"] = usage.details.get("search_keywords_table_not_found", 0)
        metrics["search_keywords_column_not_found"] = usage.details.get("search_keywords_column_not_found", 0)
        metrics["search_keywords_column_not_string"] = usage.details.get("search_keywords_column_not_string", 0)
        metrics["finish_no_query_executed"] = usage.details.get("finish_no_query_executed", 0)
        metrics["fallback"] = 1 if fallback else 0
        metrics["retry_prompt"] = sum(1 for msg in trajectory.messages if msg.role == "tool" and msg.is_retry_prompt)

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=pred_query,
            trajectory=trajectory,
            usages=[Usage.from_pydantic_ai_usage(result.usage(), self.llm)],
            metrics=metrics,
        )
