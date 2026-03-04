from typing import ClassVar
from pydantic import BaseModel
from pydantic_ai import Tool
from mintq.db_connector import BaseSQLDBConnector
from mintq.toolhub.utils import equals_ci


class GetColumnDescriptionToolMetrics(BaseModel):
    num_calls: int = 0
    error_table_not_found: int = 0
    error_column_not_found: int = 0


class GetColumnDescriptionTool:
    name: ClassVar = "get_column_description"

    def __init__(self, db_connector: BaseSQLDBConnector):
        self.db_connector = db_connector
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

        # If there is only a single schema, use it regardless of what the agent specified
        all_schema_names = [t.schema_name for t in self.db_connector.schema.tables]
        if len(set(all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        # Remove the quote characters from the column name if they exist
        for quote_char in '"`':
            if column_name.startswith(quote_char) and column_name.endswith(quote_char):
                column_name = column_name[1:-1]
                break

        table = None
        for t in self.db_connector.schema.tables:
            if (schema_name is None or equals_ci(t.schema_name, schema_name)) and t.name.lower() == table_name.lower():
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

        if column.description:
            return column.description
        else:
            return f"(column {column_name} in table {table_name} in schema {schema_name} has no description)"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetColumnDescriptionToolMetrics:
        return self._metrics
