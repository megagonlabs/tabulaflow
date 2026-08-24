from typing import ClassVar
from pydantic import BaseModel
from pydantic_ai import Tool
from tabulaflow.core import SQLSchema
from tabulaflow.agents.tools._sql import find_column, find_table


class GetColumnDescriptionToolMetrics(BaseModel):
    num_calls: int = 0
    error_table_not_found: int = 0
    error_column_not_found: int = 0


class GetColumnDescriptionTool:
    """Tool that retrieves the description of a specific column in a table.

    Looks up a column by schema name, table name, and column name, then
    returns its description if available.

    Attributes:
        schema: The physical SQL schema containing all available tables.
    """

    name: ClassVar = "get_column_description"

    def __init__(self, schema: SQLSchema):
        self.schema = schema
        self._metrics = GetColumnDescriptionToolMetrics()

    async def __call__(self, schema_name: str | None, table_name: str, column_name: str) -> str:
        """
        Get the description of a column of a table.

        Args:
            schema_name: The name of the schema, or None if schema is not applicable.
            table_name: The name of the table.
            column_name: The name of the column.
        """
        self._metrics.num_calls += 1

        table = find_table(self.schema, schema_name, table_name)
        if table is None:
            self._metrics.error_table_not_found += 1
            return f"(table {table_name} in schema {schema_name} not found)"

        column = find_column(table, column_name)
        if column is None:
            self._metrics.error_column_not_found += 1
            return f"(column {column_name} not found in table {table_name} in schema {schema_name})"

        if column.description:
            return column.description
        else:
            return f"(column {column_name} in table {table_name} in schema {schema_name} has no description)"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetColumnDescriptionToolMetrics:
        return self._metrics
