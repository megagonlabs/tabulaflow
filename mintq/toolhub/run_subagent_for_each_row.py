"""Run a row-wise subagent over a table in a single database."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import ClassVar

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


_SUBAGENT_SYSTEM_PROMPT = """\
You are a row-level database update subagent.

- You are given one target row's key columns and optionally additional context.
- After gathering all the information you need, you should update the target row via `run_query`.
- Use the key columns in the WHERE clause to target that row.
  - If a key column value is null, use `IS NULL` in SQL instead of `= NULL`.
- After executing the update query, return structured output with:
  - success: true if update succeeded, false otherwise.
  - message: concise status or error detail.""".strip()

_SUBAGENT_ROW_PROMPT_TEMPLATE = """\
Task instruction:
{{ task_instruction }}

Row location:
- Table: {{ table_name }}
- Identity columns (use in WHERE clause to target this row):
{{ key_payload_json }}
{% if row_context_json %}
- Additional row context:
{{ row_context_json }}
{% endif %}
{% if output_columns_json %}
- Update only these columns:
{{ output_columns_json }}
{% endif %}""".strip()


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

# Snowflake VARIANT requires PARSE_JSON() to cast a string parameter to VARIANT.
_JSON_PARAM_EXPR: dict[SQLDialect, str] = {
    "snowflake": "PARSE_JSON(:_v_trajectory)",
}
_DEFAULT_JSON_PARAM_EXPR = ":_v_trajectory"


def _build_key_where(key_columns: list[str], key_payload: dict[str, object]) -> tuple[str, dict[str, object]]:
    """Build a WHERE clause from key columns using named parameters.

    Returns:
        A ``(clause, params)`` tuple where *clause* is a SQL fragment like
        ``col1 = :_k_col1 AND col2 IS NULL`` and *params* maps parameter
        names to values.
    """
    parts: list[str] = []
    params: dict[str, object] = {}
    for col in key_columns:
        val = key_payload[col]
        if val is None:
            parts.append(f"{col} IS NULL")
        else:
            param_name = f"_k_{col}"
            parts.append(f"{col} = :{param_name}")
            params[param_name] = val
    return " AND ".join(parts), params


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
        self._row_prompt_template = jinja2.Template(_SUBAGENT_ROW_PROMPT_TEMPLATE)

    async def __call__(
        self,
        table_name: str,
        task_instruction: str,
        key_columns: list[str],
        input_columns: list[str] | None = None,
        output_columns: list[str] | None = None,
        sql_filter: str | None = None,
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

        Each subagent has ``run_query`` access, so it can look up other tables as
        needed for join resolution. All target output columns must already exist in
        the table.

        Args:
            table_name: Target table name. Can be qualified (e.g. schema.table).
            task_instruction: Concise task instructions for processing each row.
                Use clear, unambiguous instructions. Mention the output columns,
                their data types, and format requirements.
            key_columns: Columns the subagent uses in the WHERE clause to
                locate each row.
            input_columns: Columns to include in the row payload sent to the
                subagent as context. If omitted, all table columns are included.
            output_columns: Columns the subagent should update. If provided, all
                must already exist in the target table.
            sql_filter: A ``SELECT *`` query to select which rows to process.
                Must be a SELECT * query against table_name (e.g.
                ``SELECT * FROM reviews WHERE sentiment IS NULL LIMIT 10``).
                If omitted, all rows are processed.
        """
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
        _internal = set(_INTERNAL_COLUMNS)
        ctx_cols = input_columns or [c for c in all_columns if c not in _internal]
        missing_ctx = [c for c in ctx_cols if c not in all_columns]
        if missing_ctx:
            return f"(error: input_columns not found in table {table_name!r}: {missing_ctx})"
        missing_output_columns = [c for c in (output_columns or []) if c not in all_columns]
        if missing_output_columns:
            return f"(error: output_columns not found in table {table_name!r}: {missing_output_columns})"
        id_cols_set = set(key_columns)
        extra_ctx_cols = [c for c in ctx_cols if c not in id_cols_set]

        # Ensure _subagent_* columns exist on the target table.
        dialect = self.db_connector.language
        trajectory_dtype = _JSON_TYPE_FOR_DIALECT.get(dialect, "TEXT")
        trajectory_param_expr = _JSON_PARAM_EXPR.get(dialect, _DEFAULT_JSON_PARAM_EXPR)
        if self.store_metadata:
            added_columns = False
            for col in _INTERNAL_COLUMNS:
                if col not in all_columns:
                    if col == _COL_SUCCESS:
                        dtype = "BOOLEAN"
                    elif col == _COL_TRAJECTORY:
                        dtype = trajectory_dtype
                    else:
                        dtype = "TEXT"
                    await self.db_connector.run_query_async(
                        f"ALTER TABLE {table_name} ADD COLUMN {col} {dtype}"
                    )
                    added_columns = True
            if added_columns:
                await self.db_connector.refresh_schema_async()

        completed = 0

        async def _save_row_metadata(
            key_payload: dict[str, object],
            success: bool,
            message: str,
            trajectory: str,
        ) -> None:
            """Write subagent metadata columns for one row."""
            where_clause, params = _build_key_where(key_columns, key_payload)
            params["_v_success"] = success
            params["_v_message"] = message
            params["_v_trajectory"] = trajectory
            stmt = sqlalchemy.text(
                f"UPDATE {table_name} "
                f"SET {_COL_SUCCESS} = :_v_success, "
                f"{_COL_MESSAGE} = :_v_message, "
                f"{_COL_TRAJECTORY} = {trajectory_param_expr} "
                f"WHERE {where_clause}"
            )
            await self.db_connector.run_query_async(stmt, params)

        async def _process_one_row(row_idx: int, row: dict[str, object]) -> str | None:
            nonlocal completed
            subagent = Agent(
                model=self.subagent_llm,
                tools=[
                    self._run_query_tool.as_pydantic_ai_tool(),
                    self._get_table_schema_tool.as_pydantic_ai_tool(),
                    self._get_column_json_schema_tool.as_pydantic_ai_tool(),
                ],
                instructions=_SUBAGENT_SYSTEM_PROMPT,
                output_type=SubagentRowResult,
                model_settings=self.model_settings,
            )
            key_payload = {col: row.get(col) for col in key_columns}
            row_context = {col: row.get(col) for col in extra_ctx_cols} if extra_ctx_cols else None
            prompt = self._row_prompt_template.render(
                task_instruction=task_instruction,
                table_name=table_name,
                key_payload_json=json.dumps(key_payload, ensure_ascii=True, default=str),
                row_context_json=json.dumps(row_context, ensure_ascii=True, default=str) if row_context else None,
                output_columns_json=json.dumps(output_columns, ensure_ascii=True) if output_columns else None,
            )
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
            finally:
                if self.store_metadata and metadata is not None:
                    await _save_row_metadata(key_payload, *metadata)
                completed += 1
                if self.on_row_complete is not None:
                    self.on_row_complete(completed, total)
                    await asyncio.sleep(0)
            return error_msg

        rows = df.to_dict(orient="records")
        total = len(rows)
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _throttled_process_one_row(row_idx: int, row: dict[str, object]) -> str | None:
            async with semaphore:
                return await _process_one_row(row_idx, row)

        errors = await asyncio.gather(
            *(_throttled_process_one_row(row_idx, row) for row_idx, row in enumerate(rows, start=1))
        )
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
                    f"\nQuery {_COL_SUCCESS}, {_COL_MESSAGE}, {_COL_TRAJECTORY} "
                    f"columns in {table_name} for full details."
                )
        return summary

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
