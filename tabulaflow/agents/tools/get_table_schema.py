import re
from dataclasses import dataclass
from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from tabulaflow.data.protocols import SQLConnectorProtocol
from tabulaflow.core.schema import SQLColumnSchema, TableRef
from tabulaflow.output.formatting.schema import SQLSchemaFormatter
from tabulaflow.agents.tools.engines.sql import find_table


class GetTableSchemaToolMetrics(BaseModel):
    num_calls: int = 0
    max_columns_exceeded: int = 0
    error_invalid_column_regex_filter: int = 0
    error_table_not_found: int = 0


@dataclass(frozen=True)
class TableSchemaExecution:
    """Result of one get-table-schema invocation."""

    output: str
    n_columns: int | None


class GetTableSchemaTool:
    """Tool that retrieves the full schema definition for a specified table.

    Looks up a table by schema name and table name, then formats the table
    schema using the configured formatter.

    Attributes:
        db_connector: Database connector providing live schema access and refresh.
        formatter: The formatter used to render table schema as text.
        include_descriptions: Whether to include column descriptions in output.
        max_columns: If set, reject requests whose resulting columns exceed
            this limit, prompting the agent to use column_offset/column_limit or
            column_regex_filter to narrow down.
        release_connections_on_finish: If True, release pooled connections after each call to free
            file locks (e.g. DuckDB). Useful when an external process like
            ``dbt run`` needs exclusive access to the database file.
        enable_refresh: If True, expose and honour the ``refresh`` parameter
            in the tool schema sent to the LLM.  When False (default), the
            parameter is hidden from the LLM entirely.
    """

    name: ClassVar = "get_table_schema"

    def __init__(
        self,
        db_connector: SQLConnectorProtocol,
        formatter: SQLSchemaFormatter,
        *,
        include_descriptions: bool = True,
        max_columns: int | None = 50,
        release_connections_on_finish: bool = False,
        enable_refresh: bool = False,
    ):
        self.db_connector = db_connector
        self.formatter = formatter
        self.include_descriptions = include_descriptions
        self.max_columns = max_columns
        self._release_connections_on_finish = release_connections_on_finish
        self._enable_refresh = enable_refresh
        self._metrics = GetTableSchemaToolMetrics()

    @staticmethod
    def _filter_columns(
        columns: list[SQLColumnSchema],
        *,
        column_regex_filter: str | None = None,
        column_offset: int = 0,
        column_limit: int | None = None,
    ) -> list[SQLColumnSchema]:
        """Apply regex filter and offset/limit pagination to *columns*."""
        if column_regex_filter is not None:
            pattern = re.compile(column_regex_filter, re.IGNORECASE)
            columns = [col for col in columns if pattern.search(col.name)]
        if column_offset > 0 or column_limit is not None:
            columns = columns[column_offset:]
            if column_limit is not None:
                columns = columns[:column_limit]
        return columns

    async def _with_refresh(
        self,
        schema_name: str | None,
        table_name: str,
        refresh: bool = False,
        column_offset: int = 0,
        column_limit: int | None = None,
        column_regex_filter: str | None = None,
    ) -> str:
        """Get the full schema of a table, with optional column filtering and pagination for very large tables.

        Args:
            schema_name: The name of the schema to which the table belongs,
                or None if schema is not applicable.
            table_name: The name of the table.
            refresh: If True, re-introspect this table from the live database
                before returning. Use when a table was newly created or
                altered by DDL or dbt run.
            column_offset: Number of columns to skip from the beginning. Only provide if the table is too large.
            column_limit: Maximum number of columns to return. Only provide if the table is too large.
            column_regex_filter: Regex pattern to filter columns by name (case-insensitive).
                Only columns whose names match the pattern are returned.
                Can be combined with column_offset/column_limit to paginate within filtered results.
                Only provide if the table is too large.
        """
        return (
            await self.execute(
                schema_name,
                table_name,
                refresh=refresh,
                column_regex_filter=column_regex_filter,
                column_offset=column_offset,
                column_limit=column_limit,
            )
        ).output

    async def _no_refresh(
        self,
        schema_name: str | None,
        table_name: str,
        column_offset: int = 0,
        column_limit: int | None = None,
        column_regex_filter: str | None = None,
    ) -> str:
        """Get the full schema of a table, with optional column filtering and pagination for very large tables.

        Args:
            schema_name: The name of the schema to which the table belongs,
                or None if schema is not applicable.
            table_name: The name of the table.
            column_offset: Number of columns to skip from the beginning. Only provide if the table is too large.
            column_limit: Maximum number of columns to return. Only provide if the table is too large.
            column_regex_filter: Regex pattern to filter columns by name (case-insensitive).
                Only columns whose names match the pattern are returned.
                Can be combined with column_offset/column_limit to paginate within filtered results.
                Only provide if the table is too large.
        """
        return (
            await self.execute(
                schema_name,
                table_name,
                column_regex_filter=column_regex_filter,
                column_offset=column_offset,
                column_limit=column_limit,
            )
        ).output

    async def execute(
        self,
        schema_name: str | None,
        table_name: str,
        *,
        refresh: bool = False,
        column_regex_filter: str | None = None,
        column_offset: int = 0,
        column_limit: int | None = None,
    ) -> TableSchemaExecution:
        """Render the table schema and return output plus the selected-column count."""
        self._metrics.num_calls += 1

        schema = self.db_connector.schema
        table = find_table(schema, schema_name, table_name)
        if refresh:
            table_ref = (
                TableRef(schema_name=table.schema_name, table_name=table.name)
                if table is not None
                else TableRef(schema_name=schema_name, table_name=table_name)
            )
            try:
                await self.db_connector.refresh_schema_async([table_ref])
            except Exception as e:
                return TableSchemaExecution(output=f"(error: {e})", n_columns=None)
            schema = self.db_connector.schema
            table = find_table(schema, schema_name, table_name)
        if table is None:
            self._metrics.error_table_not_found += 1
            return TableSchemaExecution(
                output=f"(error: table {table_name} in schema {schema_name} not found)", n_columns=None
            )

        total_columns = len(table.columns)

        if column_regex_filter is not None:
            try:
                re.compile(column_regex_filter)
            except re.error as e:
                self._metrics.error_invalid_column_regex_filter += 1
                return TableSchemaExecution(output=f"(error: invalid column_regex_filter regex: {e})", n_columns=None)

        selected_columns = self._filter_columns(
            table.columns,
            column_regex_filter=column_regex_filter,
            column_offset=column_offset,
            column_limit=column_limit,
        )

        if self.max_columns is not None and len(selected_columns) > self.max_columns:
            self._metrics.max_columns_exceeded += 1
            return TableSchemaExecution(
                output=(
                    f"(error: {len(selected_columns)} columns exceed the limit of"
                    f" {self.max_columns}. Use column_offset/column_limit or column_regex_filter to narrow down.)"
                ),
                n_columns=None,
            )

        column_names = [col.name for col in selected_columns]
        selected_table = table.select_columns(
            column_names,
            case_insensitive=False,
            include_primary_key=False,
        )

        res = ""
        needs_pagination = column_offset > 0 or column_limit is not None
        if column_regex_filter is not None or needs_pagination:
            parts = []
            if column_regex_filter is not None:
                parts.append(f"filter={column_regex_filter!r}")
            if needs_pagination:
                end = column_offset + len(selected_columns)
                parts.append(f"range {column_offset + 1}-{end}")
            res += f"(showing {len(selected_columns)} of {total_columns} total columns, {', '.join(parts)})\n\n"
        res += self.formatter.format_table(
            selected_table,
            dialect=schema.dialect,
            include_descriptions=self.include_descriptions,
        )

        if self._release_connections_on_finish:
            await self.db_connector.release_connections_async()

        return TableSchemaExecution(output=res, n_columns=len(selected_columns))

    async def __call__(
        self,
        schema_name: str | None,
        table_name: str,
        refresh: bool = False,
        column_offset: int = 0,
        column_limit: int | None = None,
        column_regex_filter: str | None = None,
    ) -> str:
        execution = await self.execute(
            schema_name,
            table_name,
            refresh=refresh if self._enable_refresh else False,
            column_regex_filter=column_regex_filter,
            column_offset=column_offset,
            column_limit=column_limit,
        )
        return execution.output

    def as_pydantic_ai_tool(self) -> Tool:
        fn = self._with_refresh if self._enable_refresh else self._no_refresh
        return Tool(fn, name=self.name)

    def metrics(self) -> GetTableSchemaToolMetrics:
        return self._metrics
