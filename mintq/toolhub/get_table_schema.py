import re
from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.db_connector.base import BaseSQLDBConnector
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.schema import SQLSchema
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
            this limit, prompting the agent to use offset/limit or
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

    async def __call__(
        self,
        schema_name: str | None,
        table_name: str,
        offset: int = 0,
        limit: int | None = None,
        column_regex_filter: str | None = None,
    ) -> str:
        """Get the full schema of a table, with optional column filtering and pagination for very large tables.

        Args:
            schema_name: The name of the schema to which the table belongs,
                or None if schema is not applicable.
            table_name: The name of the table.
            offset: Number of columns to skip from the beginning. Only provide if the table is too large.
            limit: Maximum number of columns to return. Only provide if the table is too large.
            column_regex_filter: Regex pattern to filter columns by name (case-insensitive).
                Only columns whose names match the pattern are returned.
                Only provide if the table is too large.
        """
        self._metrics.num_calls += 1

        # If there is only a single schema, use it regardless of what the agent specified
        all_schema_names = [t.schema_name for t in self.schema.tables]
        if len(set[str | None](all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        table = None
        for t in self.schema.tables:
            if (schema_name is None or equals_ci(t.schema_name, schema_name)) and (
                t.name.lower() == table_name.lower()
                or any(s.lower() == table_name.lower() for pattern in t.name_patterns for s in pattern.original_names)
            ):
                table = t
                break

        if table is None:
            self._metrics.error_table_not_found += 1
            return f"(table {table_name} in schema {schema_name} not found)"

        total_columns = len(table.columns)

        # Apply column regex filter if requested
        if column_regex_filter is not None:
            try:
                pattern = re.compile(column_regex_filter, re.IGNORECASE)
            except re.error as e:
                self._metrics.error_invalid_column_regex_filter += 1
                return f"(invalid column_regex_filter regex: {e})"
            filtered_columns = [col for col in table.columns if pattern.search(col.name)]
            table = table.model_copy(update={"columns": filtered_columns})

        # Apply column pagination if requested
        needs_pagination = offset > 0 or limit is not None
        if needs_pagination:
            sliced_columns = table.columns[offset:]
            if limit is not None:
                sliced_columns = sliced_columns[:limit]
            table = table.model_copy(update={"columns": sliced_columns})

        # Reject if the result exceeds max_columns
        if self.max_columns is not None and len(table.columns) > self.max_columns:
            self._metrics.max_columns_exceeded += 1
            return (
                f"(table {table_name} has {total_columns} columns which exceeds the limit of"
                f" {self.max_columns}. Use offset/limit or column_regex_filter to narrow down.)"
            )

        res = ""
        if table.name.lower() != table_name.lower():
            res += f"(table {table_name} shares the same schema with {table.name} shown below)\n\n"
        if column_regex_filter is not None or needs_pagination:
            parts = []
            if column_regex_filter is not None:
                parts.append(f"filter={column_regex_filter!r}")
            if needs_pagination:
                end = offset + len(table.columns)
                parts.append(f"range {offset + 1}-{end}")
            res += f"(showing {len(table.columns)} of {total_columns} total columns, {', '.join(parts)})\n\n"
        res += self.formatter.format_table(table, add_description=self.add_description)
        return res

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetTableSchemaToolMetrics:
        return self._metrics
