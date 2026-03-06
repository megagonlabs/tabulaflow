from typing import ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

from mintq.formatters.utils import format_json_schema
from mintq.schema import SQLSchema
from mintq.toolhub.utils import equals_ci


class GetColumnJsonSchemaToolMetrics(BaseModel):
    num_calls: int = 0
    error_table_not_found: int = 0
    error_column_not_found: int = 0
    error_no_json_schema: int = 0


class GetColumnJsonSchemaTool:
    """Tool that retrieves the JSON schema of a specific column.

    Looks up a column by schema name, table name, and column name, then
    returns its full JSON schema if available. This is useful for exploring
    the internal structure of JSON/VARIANT columns that contain nested
    objects, arrays, etc.

    Attributes:
        schema: The SQL schema containing all available tables. Can be a
            compressed schema produced by SchemaCompressor.
    """

    name: ClassVar = "get_column_json_schema"

    def __init__(self, schema: SQLSchema):
        self.schema = schema
        self._metrics = GetColumnJsonSchemaToolMetrics()

    async def __call__(self, schema_name: str | None, table_name: str, column_name: str) -> str:
        """
        Get the JSON schema of a column, describing its internal structure (nested objects, arrays, etc.).
        Useful for semi-structured column types such as VARIANT, OBJECT, ARRAY,
        JSON, and JSONB that store nested or complex data.

        Args:
            schema_name: The name of the schema, or None if schema is not applicable.
            table_name: The name of the table.
            column_name: The name of the column.
        """
        self._metrics.num_calls += 1

        # If there is only a single schema, use it regardless of what the agent specified
        all_schema_names = [t.schema_name for t in self.schema.tables]
        if len(set(all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        # Remove the quote characters from the column name if they exist
        for quote_char in '"`':
            if column_name.startswith(quote_char) and column_name.endswith(quote_char):
                column_name = column_name[1:-1]
                break

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

        column = None
        for c in table.columns:
            if c.name.lower() == column_name.lower():
                column = c
                break

        if column is None:
            self._metrics.error_column_not_found += 1
            return f"(column {column_name} not found in table {table_name} in schema {schema_name})"

        if column.json_schema:
            return format_json_schema(column.json_schema, max_depth=None, max_fields=None)
        else:
            self._metrics.error_no_json_schema += 1
            return f"(column {column_name} in table {table_name} in schema {schema_name} has no JSON schema)"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetColumnJsonSchemaToolMetrics:
        return self._metrics
