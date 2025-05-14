from dataclasses import dataclass
import copy
import jinja2
import sqlalchemy
from sqlalchemy import select, distinct
from pydantic_core import to_jsonable_python
from pydantic_ai import Agent, RunContext
from pydantic_ai.tools import Tool
from mintq.db_connector import BaseDBConnector
from mintq.schema_formatter import BaseSchemaFormatter, get_schema_formatter
from mintq.schema import SingleOutputNL2QTask, SQLTableSchema
from mintq.modelhub import BaseNL2QModel
from mintq.modelhub.utils import get_pydantic_ai_llm
from mintq.utils import parse_query


@dataclass
class Dependencies:
    task: SingleOutputNL2QTask
    db_connector: BaseDBConnector
    formatter: BaseSchemaFormatter
    table_id_to_schema: dict[str, SQLTableSchema]


SYSTEM_PROMPT = """
You are a database expert responsible for translating natural language questions into {{language}} queries.

- The query must follow the given database schema.
- You must follow the hints if provided.
- The final output should not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, the final query should not fetch the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, the final query should not fetch the score.
  - If the question asks for the list of objects (e.g. students), fetch the IDs of the objects.
- The final output should only include the SQL query, without explanation.
- Before returning the final output, always execute the query and check if the results match the question.
{% if language == "SnowflakeSQL" %}
- For Snowflake SQL, the column names must be quoted with double quotes (e.g. SELECT ORDER."product_id").
{% endif %}
""".strip()


TASK_PROMPT = """
=== START OF DATABASE SCHEMA ===

{{schema}}

=== END OF DATABASE SCHEMA ===

=== START OF HINTS ===

{{hints}}

=== END OF HINTS ===

Question to translate: {{question}}

Now, translate the above question into a {{language}} query.
""".strip()


def get_system_prompt(ctx: RunContext[Dependencies]) -> str:
    return jinja2.Template(SYSTEM_PROMPT).render(language=ctx.deps.task.language)


def truncate(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[: max_chars // 2] + "\n...content truncated...\n" + s[-max_chars // 2 :]


def run_query(ctx: RunContext[Dependencies], query: str) -> str:
    """
    Execute a SQL query and return the results.

    Args:
        query: The SQL query to execute.
    """
    db_connector = ctx.deps.db_connector
    try:
        exec_results = db_connector.run_query(query)
    except Exception as e:
        return f"(query failed: {e})"
    if not exec_results:
        return "(query executed successfully, but results are empty)"
    exec_results = "\n".join([str(row) for row in exec_results])
    exec_results = truncate(exec_results, 500)
    return exec_results


def list_columns(ctx: RunContext[Dependencies], table: str) -> str:
    """
    List the columns of a table.

    Args:
        table: The name of the table to list the columns of. It should include the schema name if applicable.
    """
    try:
        table_schema = ctx.deps.table_id_to_schema[table]
    except KeyError:
        return f"(table {table} not found)"
    if not table_schema.columns:
        return f"(table {table} has no columns)"
    return "\n".join([ctx.deps.formatter.format_column(table_schema, col) for col in table_schema.columns])


def search_keywords(ctx: RunContext[Dependencies], table: str, column: str, keywords: list[str]) -> str:
    """
    Search for values in a column of a table that match any of the keywords.

    Args:
        table: The name of the table to search in. It should be identical to the ones in the schema (include schema name if applicable).
        column: The name of the column to search in.
        keywords: A list of keywords to search for. A value is considered a match if it contains any of the keywords.
    """
    db_connector = ctx.deps.db_connector

    # Remove the quote characters from the column name if they exist
    for quote_char in '"`':
        if column.startswith(quote_char) and column.endswith(quote_char):
            column = column[1:-1]
            break

    matches = []
    for keyword in keywords:
        sql_table = sqlalchemy.Table(table, sqlalchemy.MetaData(), sqlalchemy.Column(column, sqlalchemy.String))
        stmt = select(distinct(sql_table.c[column])).where(sql_table.c[column].like(f"%{keyword}%"))
        with db_connector._engine.connect() as conn:
            result = conn.execute(stmt)
            matches += [row[0] for row in result]
    matches = sorted(list(set(matches)))
    if not matches:
        return "(no matches found)"

    res = f"{len(matches)} matches:\n"
    res += "\n".join(matches[:10])
    if len(matches) > 10:
        res += "\n..."
    return res


class SQLAgentTableNamesOnly(BaseNL2QModel):
    def __init__(
        self, llm: str, schema_formatter: BaseSchemaFormatter, temperature: float = 0.0, num_candidates: int = 1
    ):
        self._llm_name = llm
        self.temperature = temperature
        self.agent = Agent(
            get_pydantic_ai_llm(llm),
            tools=[Tool(run_query), Tool(list_columns), Tool(search_keywords)],
            deps_type=Dependencies,
            instructions=get_system_prompt,
        )
        self.formatter = schema_formatter

    @property
    def llm_name(self) -> str:
        return self._llm_name

    def predict(self, task: SingleOutputNL2QTask, db_connector: BaseDBConnector) -> SingleOutputNL2QTask:
        task = copy.deepcopy(task)

        prompt = jinja2.Template(TASK_PROMPT).render(
            schema=self.formatter.format(db_connector.schema),
            hints=task.evidence,
            question=task.question,
            language=task.language,
        )

        # Construct dependencies
        table_id_to_schema = {self.formatter.format_table_name(table): table for table in db_connector.schema.tables}
        deps = Dependencies(
            task=task,
            db_connector=db_connector,
            formatter=self.formatter,
            table_id_to_schema=table_id_to_schema,
        )

        # Run the agent
        result = self.agent.run_sync(prompt, deps=deps, model_settings={"temperature": self.temperature})

        task.pred_query = parse_query(result.output)
        task.trajectory = to_jsonable_python(result.all_messages())
        return task
