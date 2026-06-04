import re
from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from tabulaflow.db_connector.base import BaseSQLDBConnector
from tabulaflow.formatters import BaseSQLSchemaFormatter
from tabulaflow.preprocessors.components.schema_compressor import SchemaCompressor
from tabulaflow.schema import SQLColumnSchema, SQLSchema, SQLTableSchema, TableRef
from tabulaflow.toolhub.utils import equals_ci


class GetTableSchemaToolMetrics(BaseModel):
    num_calls: int = 0
    max_columns_exceeded: int = 0
    error_invalid_column_regex_filter: int = 0
    error_table_not_found: int = 0


class GetTableSchemaTool:
    """Tool that retrieves the full schema definition for a specified table.

    Looks up a table by schema name and table name, then formats the table
    schema using the configured formatter.

    Attributes:
        db_connector: Database connector providing live schema access and refresh.
        formatter: The formatter used to render table schema as text.
        compress: Whether to compress the schema (merge structurally identical tables).
        add_description: Whether to include column descriptions in output.
        max_columns: If set, reject requests whose resulting columns exceed
            this limit, prompting the agent to use column_offset/column_limit or
            column_regex_filter to narrow down.
        disconnect_on_finish: If True, disconnect after each call to release
            file locks (e.g. DuckDB). Useful when an external process like
            ``dbt run`` needs exclusive access to the database file.
        enable_refresh: If True, expose and honour the ``refresh`` parameter
            in the tool schema sent to the LLM.  When False (default), the
            parameter is hidden from the LLM entirely.
    """

    name: ClassVar = "get_table_schema"

    def __init__(
        self,
        db_connector: BaseSQLDBConnector,
        formatter: BaseSQLSchemaFormatter,
        *,
        compress: bool = True,
        add_description: bool = True,
        max_columns: int | None = 50,
        disconnect_on_finish: bool = False,
        enable_refresh: bool = False,
    ):
        self.db_connector = db_connector
        self.formatter = formatter
        self._compressor = SchemaCompressor() if compress else None
        self._compressed_schema: SQLSchema | None = None
        self.add_description = add_description
        self.max_columns = max_columns
        self._disconnect_on_finish = disconnect_on_finish
        self._enable_refresh = enable_refresh
        self._metrics = GetTableSchemaToolMetrics()
        self.last_columns_returned: int | None = None

    def _invalidate_schema(self) -> None:
        self._compressed_schema = None

    @property
    def schema(self) -> SQLSchema:
        """Return the (optionally compressed) schema, building it lazily."""
        if self._compressed_schema is None:
            schema = self.db_connector.schema
            self._compressed_schema = self._compressor.compress(schema) if self._compressor else schema
        return self._compressed_schema

    def _find_table(self, schema_name: str | None, table_name: str) -> SQLTableSchema | None:
        """Find a table by schema name and table name (case-insensitive).

        If the schema contains only a single schema name, that schema is used
        regardless of *schema_name*.
        """
        all_schema_names = [t.schema_name for t in self.schema.tables]
        if len(set[str | None](all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        for t in self.schema.tables:
            if (schema_name is None or equals_ci(t.schema_name, schema_name)) and (
                t.name.lower() == table_name.lower()
                or any(s.lower() == table_name.lower() for pattern in t.name_patterns for s in pattern.original_names)
            ):
                return t
        return None

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
        return await self._execute(schema_name, table_name, refresh, column_regex_filter, column_offset, column_limit)

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
        return await self._execute(schema_name, table_name, False, column_regex_filter, column_offset, column_limit)

    async def _execute(
        self,
        schema_name: str | None,
        table_name: str,
        refresh: bool,
        column_regex_filter: str | None,
        column_offset: int,
        column_limit: int | None,
    ) -> str:
        self._metrics.num_calls += 1

        table = self._find_table(schema_name, table_name)
        if refresh:
            try:
                await self.db_connector.refresh_schema_async([TableRef(schema_name=schema_name, table_name=table_name)])
                self._invalidate_schema()
                table = self._find_table(schema_name, table_name)
            except Exception as e:
                if table is None:
                    self._metrics.error_table_not_found += 1
                    return f"(error: {e})"
        if table is None:
            self._metrics.error_table_not_found += 1
            return f"(table {table_name} in schema {schema_name} not found)"

        total_columns = len(table.columns)

        if column_regex_filter is not None:
            try:
                re.compile(column_regex_filter)
            except re.error as e:
                self._metrics.error_invalid_column_regex_filter += 1
                return f"(invalid column_regex_filter regex: {e})"

        selected_columns = self._filter_columns(
            table.columns,
            column_regex_filter=column_regex_filter,
            column_offset=column_offset,
            column_limit=column_limit,
        )

        if self.max_columns is not None and len(selected_columns) > self.max_columns:
            self._metrics.max_columns_exceeded += 1
            return (
                f"({len(selected_columns)} columns exceed the limit of"
                f" {self.max_columns}. Use column_offset/column_limit or column_regex_filter to narrow down.)"
            )

        column_names = [col.name for col in selected_columns]
        trimmed_table = table.trim(column_names, case_insensitive=False, keep_pk=False)

        res = ""
        if table.name.lower() != table_name.lower():
            res += f"(table {table_name} shares the same schema with {table.name} shown below)\n\n"
        needs_pagination = column_offset > 0 or column_limit is not None
        if column_regex_filter is not None or needs_pagination:
            parts = []
            if column_regex_filter is not None:
                parts.append(f"filter={column_regex_filter!r}")
            if needs_pagination:
                end = column_offset + len(selected_columns)
                parts.append(f"range {column_offset + 1}-{end}")
            res += f"(showing {len(selected_columns)} of {total_columns} total columns, {', '.join(parts)})\n\n"
        self.formatter.set_dialect(self.schema.dialect)
        if trimmed_table is not None:
            res += self.formatter.format_table(trimmed_table, add_description=self.add_description)
        else:
            res += self.formatter.format_table(
                table.model_copy(update={"columns": []}), add_description=self.add_description
            )

        self.last_columns_returned = len(selected_columns)

        if self._disconnect_on_finish:
            await self.db_connector.disconnect_async()

        return res

    async def __call__(
        self,
        schema_name: str | None,
        table_name: str,
        refresh: bool = False,
        column_offset: int = 0,
        column_limit: int | None = None,
        column_regex_filter: str | None = None,
    ) -> str:
        return await self._execute(
            schema_name,
            table_name,
            refresh if self._enable_refresh else False,
            column_regex_filter,
            column_offset,
            column_limit,
        )

    def as_pydantic_ai_tool(self) -> Tool:
        fn = self._with_refresh if self._enable_refresh else self._no_refresh
        return Tool(fn, name=self.name)

    def metrics(self) -> GetTableSchemaToolMetrics:
        return self._metrics
