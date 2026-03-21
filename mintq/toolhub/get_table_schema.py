import re
from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.schema import SQLColumnSchema, SQLSchema, SQLTableSchema
from mintq.toolhub.utils import equals_ci


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
        schema: The SQL schema containing all available tables. Can be a
            compressed schema produced by SchemaCompressor.
        formatter: The formatter used to render table schema as text.
        add_description: Whether to include column descriptions in output.
        max_columns: If set, reject requests whose resulting columns exceed
            this limit, prompting the agent to use column_range or
            column_regex_filter to narrow down.
    """

    name: ClassVar = "get_table_schema"

    def __init__(
        self,
        schema: SQLSchema,
        formatter: BaseSQLSchemaFormatter,
        add_description: bool = True,
        max_columns: int | None = 50,
    ):
        self.schema = schema
        self.formatter = formatter
        self.add_description = add_description
        self.max_columns = max_columns
        self._metrics = GetTableSchemaToolMetrics()

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
        column_range: list[int] | None = None,
    ) -> list[SQLColumnSchema]:
        """Apply regex filter and range pagination to *columns*.

        Args:
            columns: The full list of columns.
            column_regex_filter: Case-insensitive regex; only matching columns
                are kept.
            column_range: ``[start, end]`` 1-indexed inclusive range. ``end=-1``
                means the last column.  Applied after regex filtering.
        """
        if column_regex_filter is not None:
            pattern = re.compile(column_regex_filter, re.IGNORECASE)
            columns = [col for col in columns if pattern.search(col.name)]
        if column_range is not None:
            start, end = column_range
            if end == -1:
                end = len(columns)
            columns = columns[max(start - 1, 0) : end]
        return columns

    async def __call__(
        self,
        schema_name: str | None,
        table_name: str,
        column_regex_filter: str | None = None,
        column_range: list[int] | None = None,
    ) -> str:
        """Get the full schema of a table, with optional column filtering and pagination for very large tables.

        Args:
            schema_name: The name of the schema to which the table belongs,
                or None if schema is not applicable.
            table_name: The name of the table.
            column_regex_filter: Regex pattern to filter columns by name (case-insensitive).
                Only columns whose names match the pattern are returned.
                Can be combined with column_range to paginate within filtered results.
                Only provide if the table is too large.
            column_range: Optional [start, end] range (1-indexed, inclusive) to
                select a slice of columns. Use end=-1 for the last column.
                Applied after column_regex_filter. Only provide if the table is
                too large.
        """
        self._metrics.num_calls += 1

        table = self._find_table(schema_name, table_name)
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

        if column_range is not None and len(column_range) != 2:
            return "(column_range must be a list of two integers [start, end].)"

        selected_columns = self._filter_columns(
            table.columns,
            column_regex_filter=column_regex_filter,
            column_range=column_range,
        )

        if self.max_columns is not None and len(selected_columns) > self.max_columns:
            self._metrics.max_columns_exceeded += 1
            return (
                f"({len(selected_columns)} columns exceed the limit of"
                f" {self.max_columns}. Use column_range or column_regex_filter to narrow down.)"
            )

        column_names = [col.name for col in selected_columns]
        trimmed_table = table.trim(column_names, case_insensitive=False, keep_pk=False)

        res = ""
        if table.name.lower() != table_name.lower():
            res += f"(table {table_name} shares the same schema with {table.name} shown below)\n\n"
        if column_regex_filter is not None or column_range is not None:
            parts = []
            if column_regex_filter is not None:
                parts.append(f"filter={column_regex_filter!r}")
            if column_range is not None:
                parts.append(f"range {column_range[0]}-{column_range[1]}")
            res += f"(showing {len(selected_columns)} of {total_columns} total columns, {', '.join(parts)})\n\n"
        self.formatter.set_dialect(self.schema.dialect)
        if trimmed_table is not None:
            res += self.formatter.format_table(trimmed_table, add_description=self.add_description)
        else:
            res += self.formatter.format_table(
                table.model_copy(update={"columns": []}), add_description=self.add_description
            )
        return res

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetTableSchemaToolMetrics:
        return self._metrics
