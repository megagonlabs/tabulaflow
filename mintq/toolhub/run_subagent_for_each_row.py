"""Run a row-wise subagent over a table in a single database."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import ClassVar, Literal

import jinja2
import sqlalchemy
from pydantic import BaseModel
from pydantic_ai import Agent, Tool

from mintq.db_connector.base import BaseSQLDBConnector
from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
from mintq.schema import SQLDialect, Trajectory
from mintq.toolhub.get_column_json_schema import GetColumnJsonSchemaTool
from mintq.toolhub.get_table_schema import GetTableSchemaTool
from mintq.toolhub.run_query import RunQueryTool


_AGENTIC_SYSTEM_PROMPT_TEMPLATE = """\
You are a row-level database update subagent.

- Update the target row in table `{{ table_name }}` via `run_query`.
- Key columns for the WHERE clause: {{ key_columns_json }}
  - If a key column value is null, use `IS NULL` in SQL instead of `= NULL`.
{% if output_columns_json %}\
- Update only these columns: {{ output_columns_json }}
{% endif %}\
- After executing the update query, return structured output with:
  - success: true if update succeeded, false otherwise.
  - message: concise status or error detail.""".strip()


_COL_SUCCESS = "_subagent_success"
_COL_MESSAGE = "_subagent_message"
_COL_TRAJECTORY = "_subagent_trajectory"
_INTERNAL_COLUMNS = [_COL_SUCCESS, _COL_MESSAGE, _COL_TRAJECTORY]

# Dialects that support a native JSON column type and the SQL type name to use.
_JSON_TYPE_FOR_DIALECT: dict[SQLDialect, str] = {
    "snowflake": "VARIANT",
    "postgres": "JSONB",
    "mysql": "JSON",
    "duckdb": "JSON",
    "bigquery": "JSON",
    "clickhouse": "String",  # no native JSON; fall back to String (≈TEXT)
}


# Dialects that require PARSE_JSON() to store a JSON string into a native column.
_DIALECTS_WITH_PARSE_JSON: set[SQLDialect] = {"snowflake"}

_JINJA_ENV = jinja2.Environment(undefined=jinja2.Undefined)
_JINJA_ENV.filters["fromjson"] = lambda v: json.loads(v) if isinstance(v, str) else v


def _key_where_clause(key_columns: list[str], key_payload: dict[str, object]) -> sqlalchemy.ColumnElement[bool]:
    """Build a SQLAlchemy WHERE clause from key columns."""
    conditions: list[sqlalchemy.ColumnElement[bool]] = []
    for col_name in key_columns:
        val = key_payload[col_name]
        col: sqlalchemy.ColumnClause[object] = sqlalchemy.column(col_name)
        conditions.append(col.is_(None) if val is None else col == val)
    return sqlalchemy.and_(*conditions)


class SubagentRowResult(BaseModel):
    success: bool
    message: str


class RunSubagentForEachRowTool:
    """Run an LLM subagent for each row of a table and let it write updates.

    The subagent is given access to:
    - ``run_query``
    - ``get_table_schema``
    - ``get_column_json_schema``
    """

    name: ClassVar[str] = "run_subagent_for_each_row"

    def __init__(
        self,
        db_connector: BaseSQLDBConnector,
        *,
        subagent_llm: str = "openai-responses:gpt-5-mini",
        model_settings: dict[str, object] | None = None,
        max_concurrency: int = 200,
        store_metadata: bool = False,
    ) -> None:
        """Initialize the tool.

        Args:
            db_connector: SQL database connector.
            subagent_llm: LLM identifier used by per-row subagent runs.
            model_settings: Optional pydantic-ai model settings passed to
                each subagent run (e.g. ``openai_service_tier``).
            max_concurrency: Maximum number of row subagents to run
                concurrently.
            store_metadata: If True, write ``_subagent_success``,
                ``_subagent_message``, and ``_subagent_trajectory`` columns
                back to the target table after each row.
        """
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        self.db_connector = db_connector
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.max_concurrency = max_concurrency
        self.store_metadata = store_metadata
        self.on_row_complete: Callable[[int, int], None] | None = None
        self._run_query_tool = RunQueryTool(db_connector)
        self._get_table_schema_tool = GetTableSchemaTool(db_connector, SQLDDLSchemaFormatter(), compress=True)
        self._get_column_json_schema_tool = GetColumnJsonSchemaTool(db_connector.schema)
        self._agentic_system_prompt_template = _JINJA_ENV.from_string(_AGENTIC_SYSTEM_PROMPT_TEMPLATE)

    async def __call__(
        self,
        table_name: str,
        task_instruction: str,
        key_columns: list[str],
        output_columns: list[str] | None = None,
        sql_filter: str | None = None,
        mode: Literal["agentic", "direct"] = "direct",
    ) -> str:
        """Run an LLM subagent on each row to perform operations beyond standard SQL.

        This is the execution primitive for semantic operators — tasks where the
        predicate, join condition, or transformation requires natural-language
        understanding rather than exact SQL expressions. Prefer this tool over
        fuzzy regex matching or LIKE-based SQL for these tasks. Common patterns:

        - **Semantic filter**: Classify a free-text column against a natural-language
          predicate (e.g., "is this review positive or negative?").
        - **Semantic extraction**: Extract structured values from unstructured text
          (e.g., extract sentiment, topic, or named entities from a comment).
        - **Semantic join**: Match rows across tables where there is no shared key
          and no syntactic overlap between join columns (e.g., abbreviations to
          full names, or matching product names across different naming conventions).
          Two approaches: (a) (preferred) add a foreign-key column to one table and instruct
          the subagent to look up the other table (via ``run_query``) to resolve the
          match, or (b) add a standardized column to both tables and have the
          subagent normalize each side to a canonical form independently. After
          the tool completes, a standard SQL JOIN on the new column(s) produces
          the final result.

        In ``direct`` mode (default), the subagent receives no tools and only
        produces text output; this tool writes the output to the
        ``output_columns`` automatically. Use ``direct`` mode when you need
        to strictly control the subagent's context (e.g. when running inference
        or labeling data). In ``agentic`` mode, each subagent has ``run_query``
        access and writes updates itself.

        Args:
            table_name: Target table name. Can be qualified (e.g. schema.table).
            task_instruction: A Jinja2 template rendered per-row as the subagent
                prompt. Use ``{{ column_name }}`` to interpolate column values.
                For JSON columns, use ``{{ (col | fromjson).field }}`` to access
                nested fields. Example: ``"Classify the sentiment of: {{ review_text }}"``.
            key_columns: Columns the subagent uses in the WHERE clause to
                locate each row.
            output_columns: Columns the subagent should update. In ``direct``
                mode, must be exactly one column. If provided, all must
                already exist in the target table.
            sql_filter: A ``SELECT *`` query to select which rows to process.
                Must be a SELECT * query against table_name (e.g.
                ``SELECT * FROM reviews WHERE sentiment IS NULL LIMIT 10``).
                If omitted, all rows are processed.
            mode: Execution mode. ``direct`` (default) gives no tools — the
                subagent produces text output and this tool writes it to
                ``output_columns``. ``agentic`` gives the subagent tools to
                query and update the database.
        """
        if mode == "direct":
            if not output_columns or len(output_columns) != 1:
                return "(error: output_columns must be exactly one column in direct mode)"

        query = sql_filter if sql_filter is not None else f"SELECT * FROM {table_name}"
        select_result = await self.db_connector.run_query_async(query)
        if select_result.error is not None or select_result.df is None:
            detail = select_result.error.message if select_result.error is not None else "no dataframe returned"
            return f"(error: failed to load rows from {table_name}: {detail})"

        df = select_result.df
        all_columns = [str(c) for c in df.columns]
        if not all_columns:
            return f"(error: table {table_name!r} has no columns)"

        missing_id = [c for c in key_columns if c not in all_columns]
        if missing_id:
            return f"(error: key_columns not found in table {table_name!r}: {missing_id})"
        missing_output_columns = [c for c in (output_columns or []) if c not in all_columns]
        if missing_output_columns:
            return f"(error: output_columns not found in table {table_name!r}: {missing_output_columns})"

        # Compile the task instruction as a Jinja2 template.
        try:
            task_template = _JINJA_ENV.from_string(task_instruction)
        except jinja2.TemplateSyntaxError as e:
            return f"(error: invalid Jinja2 syntax in task_instruction: {e})"

        # Ensure _subagent_* columns exist on the target table.
        dialect = self.db_connector.language
        trajectory_dtype = _JSON_TYPE_FOR_DIALECT.get(dialect, "TEXT")
        if self.store_metadata:
            for col in _INTERNAL_COLUMNS:
                if col not in all_columns:
                    if col == _COL_SUCCESS:
                        dtype = "BOOLEAN"
                    elif col == _COL_TRAJECTORY:
                        dtype = trajectory_dtype
                    else:
                        dtype = "TEXT"
                    await self.db_connector.run_query_async(f"ALTER TABLE {table_name} ADD COLUMN {col} {dtype}")

        # Resolve the single output column name for direct mode.
        direct_output_col: str | None = None
        if mode == "direct":
            assert output_columns is not None and len(output_columns) == 1
            direct_output_col = output_columns[0]

        # Build the agentic system prompt (static across rows).
        agentic_system_prompt: str | None = None
        if mode == "agentic":
            agentic_system_prompt = self._agentic_system_prompt_template.render(
                table_name=table_name,
                key_columns_json=json.dumps(key_columns, ensure_ascii=True),
                output_columns_json=json.dumps(output_columns, ensure_ascii=True) if output_columns else None,
            )

        completed = 0

        # Build a SQLAlchemy table with all columns referenced in SET clauses.
        sa_col_names: set[str] = set(key_columns)
        if self.store_metadata:
            sa_col_names.update(_INTERNAL_COLUMNS)
        if output_columns:
            sa_col_names.update(output_columns)
        sa_table = sqlalchemy.table(table_name, *[sqlalchemy.column(c) for c in sa_col_names])

        async def _save_row_metadata(
            key_payload: dict[str, object],
            success: bool,
            message: str,
            trajectory: str,
        ) -> None:
            """Write subagent metadata columns for one row."""
            traj_val: object = (
                sqlalchemy.func.parse_json(trajectory) if dialect in _DIALECTS_WITH_PARSE_JSON else trajectory
            )
            stmt = (
                sqlalchemy.update(sa_table)
                .where(_key_where_clause(key_columns, key_payload))
                .values(
                    {
                        sa_table.c[_COL_SUCCESS]: success,
                        sa_table.c[_COL_MESSAGE]: message,
                        sa_table.c[_COL_TRAJECTORY]: traj_val,
                    }
                )
            )
            await self.db_connector.run_query_async(stmt)

        async def _write_row_output(
            key_payload: dict[str, object],
            output_values: dict[str, object],
        ) -> None:
            """Write direct-mode output values to the target row."""
            stmt = (
                sqlalchemy.update(sa_table)
                .where(_key_where_clause(key_columns, key_payload))
                .values({sa_table.c[col]: val for col, val in output_values.items()})
            )
            await self.db_connector.run_query_async(stmt)

        async def _process_one_row_agentic(row_idx: int, row: dict[str, object]) -> str | None:
            nonlocal completed
            assert agentic_system_prompt is not None
            prompt = task_template.render(row)
            subagent = Agent(
                model=self.subagent_llm,
                tools=[
                    self._run_query_tool.as_pydantic_ai_tool(),
                    self._get_table_schema_tool.as_pydantic_ai_tool(),
                    self._get_column_json_schema_tool.as_pydantic_ai_tool(),
                ],
                instructions=agentic_system_prompt,
                output_type=SubagentRowResult,
                model_settings=self.model_settings,
            )
            key_payload = {col: row.get(col) for col in key_columns}
            error_msg: str | None = None
            metadata: tuple[bool, str, str] | None = None
            try:
                result = await subagent.run(prompt)
                output = result.output
                traj = Trajectory.from_pydantic_ai_messages(result.all_messages())
                metadata = (output.success, output.message, traj.model_dump_json())
                if not output.success:
                    error_msg = f"row {row_idx}: {output.message}"
            except Exception as e:
                error_msg = f"row {row_idx}: {type(e).__name__}: {e}"
                metadata = (False, error_msg, "")
            finally:
                if self.store_metadata and metadata is not None:
                    await _save_row_metadata(key_payload, *metadata)
                completed += 1
                if self.on_row_complete is not None:
                    self.on_row_complete(completed, total)
                    await asyncio.sleep(0)
            return error_msg

        async def _process_one_row_direct(row_idx: int, row: dict[str, object]) -> str | None:
            nonlocal completed
            assert direct_output_col is not None
            prompt = task_template.render(row)
            subagent = Agent(
                model=self.subagent_llm,
                tools=[],
                output_type=str,
                model_settings=self.model_settings,
            )
            key_payload = {col: row.get(col) for col in key_columns}
            error_msg: str | None = None
            metadata: tuple[bool, str, str] | None = None
            try:
                result = await subagent.run(prompt)
                output = result.output
                await _write_row_output(key_payload, {direct_output_col: output})
                traj = Trajectory.from_pydantic_ai_messages(result.all_messages())
                metadata = (True, output, traj.model_dump_json())
            except Exception as e:
                error_msg = f"row {row_idx}: {type(e).__name__}: {e}"
                metadata = (False, error_msg, "")
            finally:
                if self.store_metadata and metadata is not None:
                    await _save_row_metadata(key_payload, *metadata)
                completed += 1
                if self.on_row_complete is not None:
                    self.on_row_complete(completed, total)
                    await asyncio.sleep(0)
            return error_msg

        process_fn = _process_one_row_direct if mode == "direct" else _process_one_row_agentic
        rows = df.to_dict(orient="records")
        total = len(rows)
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _throttled(row_idx: int, row: dict[str, object]) -> str | None:
            async with semaphore:
                return await process_fn(row_idx, row)

        errors = await asyncio.gather(*(_throttled(row_idx, row) for row_idx, row in enumerate(rows, start=1)))
        await self.db_connector.refresh_schema_async()

        error_messages = [e for e in errors if e is not None]
        failed = len(error_messages)
        updated = total - failed
        summary = (
            f"Processed {total} rows from {table_name}; "
            f"subagent updates succeeded for {updated} rows, failed for {failed} rows."
        )
        if error_messages:
            summary += "\nSample errors:\n" + "\n".join(f"- {e}" for e in error_messages[:5])
        if self.store_metadata:
            summary += (
                f"\nMetadata stored in columns {_COL_SUCCESS}, {_COL_MESSAGE}, {_COL_TRAJECTORY} of {table_name}."
            )
        return summary

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
