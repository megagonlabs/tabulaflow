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
        self._agentic_system_prompt_template = jinja2.Template(_AGENTIC_SYSTEM_PROMPT_TEMPLATE)

    async def __call__(
        self,
        table_name: str,
        task_instruction: str,
        key_columns: list[str],
        output_columns: list[str] | None = None,
        sql_filter: str | None = None,
        mode: Literal["agentic", "direct"] = "agentic",
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

        In ``agentic`` mode (default), each subagent has ``run_query`` access and
        writes updates itself. In ``direct`` mode, the subagent receives no tools
        and only produces text output; this tool writes the output to the
        ``output_columns`` automatically. Only use ``direct`` mode when you need
        to strictly control the subagent's context (e.g. when running inference
        on a dataset).

        Args:
            table_name: Target table name. Can be qualified (e.g. schema.table).
            task_instruction: A Jinja2 template rendered per-row as the subagent
                prompt. Use ``{{ column_name }}`` to interpolate column values.
                Example: ``"Classify the sentiment of: {{ review_text }}"``.
            key_columns: Columns the subagent uses in the WHERE clause to
                locate each row.
            output_columns: Columns the subagent should update. In ``direct``
                mode, must be exactly one column. If provided, all must
                already exist in the target table.
            sql_filter: A ``SELECT *`` query to select which rows to process.
                Must be a SELECT * query against table_name (e.g.
                ``SELECT * FROM reviews WHERE sentiment IS NULL LIMIT 10``).
                If omitted, all rows are processed.
            mode: Execution mode. ``agentic`` (default) gives the subagent
                tools to query and update the database. ``direct`` gives no
                tools — the subagent produces text output and this tool writes
                it to ``output_columns``.
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
            task_template = jinja2.Template(task_instruction)
        except jinja2.TemplateSyntaxError as e:
            return f"(error: invalid Jinja2 syntax in task_instruction: {e})"

        # Ensure _subagent_* columns exist on the target table.
        dialect = self.db_connector.language
        trajectory_dtype = _JSON_TYPE_FOR_DIALECT.get(dialect, "TEXT")
        trajectory_param_expr = _JSON_PARAM_EXPR.get(dialect, _DEFAULT_JSON_PARAM_EXPR)
        if self.store_metadata:
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

        async def _write_row_output(
            key_payload: dict[str, object],
            output_values: dict[str, object],
        ) -> None:
            """Write direct-mode output values to the target row."""
            where_clause, params = _build_key_where(key_columns, key_payload)
            set_parts: list[str] = []
            for col, val in output_values.items():
                param_name = f"_o_{col}"
                set_parts.append(f"{col} = :{param_name}")
                params[param_name] = val
            stmt = sqlalchemy.text(
                f"UPDATE {table_name} SET {', '.join(set_parts)} WHERE {where_clause}"
            )
            await self.db_connector.run_query_async(stmt, params)

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

        errors = await asyncio.gather(
            *(_throttled(row_idx, row) for row_idx, row in enumerate(rows, start=1))
        )
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
                    f"\nQuery {_COL_SUCCESS}, {_COL_MESSAGE}, {_COL_TRAJECTORY} "
                    f"columns in {table_name} for full details."
                )
        return summary

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
