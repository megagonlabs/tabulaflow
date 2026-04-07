"""Run a row-wise subagent over a table in a single database."""

from __future__ import annotations

import asyncio
import json
from typing import ClassVar

import jinja2
from pydantic import BaseModel
from pydantic_ai import Agent, Tool

from mintq.db_connector.base import BaseSQLDBConnector
from mintq.formatters.sql_ddl import SQLDDLSchemaFormatter
from mintq.toolhub.get_column_json_schema import GetColumnJsonSchemaTool
from mintq.toolhub.get_table_schema import GetTableSchemaTool
from mintq.toolhub.run_query import RunQueryTool


_SUBAGENT_SYSTEM_PROMPT = """\
You are a row-level database update subagent.

- You are given one target row payload and its identity columns.
- After gathering all the information you need, you should update the target row via `run_query`.
- Use the given columns in the WHERE clause to target that row.
  - If a row-identity value is null, use `IS NULL` in SQL instead of `= NULL`.
- After executing the update query, return structured output with:
  - success: true if update succeeded, false otherwise.
  - message: concise status or error detail.""".strip()

_SUBAGENT_ROW_PROMPT_TEMPLATE = """\
Task instruction:
{{ task_instruction }}

Row location:
- Table: {{ table_name }}
- Use the columns below to identify this row:
{{ row_payload_json }}
{% if output_columns_json %}
- Update only these columns:
{{ output_columns_json }}
{% endif %}""".strip()


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
    ) -> None:
        """Initialize the tool.

        Args:
            db_connector: SQL database connector.
            subagent_llm: LLM identifier used by per-row subagent runs.
        """
        self.db_connector = db_connector
        self.subagent_llm = subagent_llm
        self._run_query_tool = RunQueryTool(db_connector)
        self._get_table_schema_tool = GetTableSchemaTool(db_connector, SQLDDLSchemaFormatter(), compress=True)
        self._get_column_json_schema_tool = GetColumnJsonSchemaTool(db_connector.schema)
        self._row_prompt_template = jinja2.Template(_SUBAGENT_ROW_PROMPT_TEMPLATE)

    async def __call__(
        self,
        table_name: str,
        task_instruction: str,
        input_columns: list[str] | None = None,
        output_columns: list[str] | None = None,
    ) -> str:
        """Use subagents to process each row of a table and write updates back.

        All target output columns must already exist in the table.

        Args:
            table_name: Target table name. Can be qualified (for example schema.table).
            task_instruction: Concise task instructions for processing each row.
                Use clear unambiguous instructions. Mention the output columns, their
                data types and format requirements.
            input_columns: Optional columns to include in row identity/prompt payload.
                If omitted, all table columns are included.
            output_columns: Optional columns the subagent should update.
                If provided, all output columns must already exist in the target table.
        """
        select_result = await self.db_connector.run_query_async(f"SELECT * FROM {table_name}")
        if select_result.error is not None or select_result.df is None:
            detail = select_result.error.message if select_result.error is not None else "no dataframe returned"
            return f"(error: failed to load rows from {table_name}: {detail})"

        df = select_result.df
        all_columns = [str(c) for c in df.columns]
        if not all_columns:
            return f"(error: table {table_name!r} has no columns)"

        row_identity_columns = input_columns or all_columns
        missing = [c for c in row_identity_columns if c not in all_columns]
        if missing:
            return f"(error: input_columns not found in table {table_name!r}: {missing})"
        missing_output_columns = [c for c in (output_columns or []) if c not in all_columns]
        if missing_output_columns:
            return f"(error: output_columns not found in table {table_name!r}: {missing_output_columns})"

        async def _process_one_row(row_idx: int, row: dict[str, object]) -> str | None:
            subagent = Agent(
                model=self.subagent_llm,
                tools=[
                    self._run_query_tool.as_pydantic_ai_tool(),
                    self._get_table_schema_tool.as_pydantic_ai_tool(),
                    self._get_column_json_schema_tool.as_pydantic_ai_tool(),
                ],
                instructions=_SUBAGENT_SYSTEM_PROMPT,
                output_type=SubagentRowResult,
            )
            identity_payload = {col: row.get(col) for col in row_identity_columns}
            prompt = self._row_prompt_template.render(
                task_instruction=task_instruction,
                table_name=table_name,
                row_payload_json=json.dumps(identity_payload, ensure_ascii=True, default=str),
                output_columns_json=json.dumps(output_columns, ensure_ascii=True) if output_columns else None,
            )
            try:
                result = await subagent.run(prompt)
                output = result.output
                if not output.success:
                    return f"row {row_idx}: {output.message}"
            except Exception as e:
                return f"row {row_idx}: {type(e).__name__}: {e}"
            return None

        rows = df.to_dict(orient="records")
        processed = len(rows)
        errors = await asyncio.gather(*(_process_one_row(row_idx, row) for row_idx, row in enumerate(rows, start=1)))
        error_messages = [e for e in errors if e is not None]
        failed = len(error_messages)
        updated = processed - failed
        summary = (
            f"Processed {processed} rows from {table_name}; "
            f"subagent updates succeeded for {updated} rows, failed for {failed} rows."
        )
        if error_messages:
            summary += "\nSample errors:\n" + "\n".join(f"- {e}" for e in error_messages[:5])
        return summary

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
