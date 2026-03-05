from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.db_connector.base import BaseSQLDBConnector
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.schema import SQLSchema
from mintq.toolhub.utils import equals_ci


class GetTableSchemaToolMetrics(BaseModel):
    num_calls: int = 0
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
    """

    name: ClassVar = "get_table_schema"

    def __init__(self, schema: SQLSchema, formatter: BaseSQLSchemaFormatter, add_description: bool = True):
        self.schema = schema
        self.formatter = formatter
        self.add_description = add_description
        self._metrics = GetTableSchemaToolMetrics()

    async def __call__(self, schema_name: str | None, table_name: str) -> str:
        """
        Get the full schema of a table.

        Args:
            schema_name: The name of the schema to which the table belongs, or None if schema is not applicable.
            table_name: The name of the table.
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

        res = ""
        if table.name.lower() != table_name.lower():
            res += f"(table {table_name} shares the same schema with {table.name} shown below)\n\n"
        res += self.formatter.format_table(table, add_description=self.add_description)
        return res

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetTableSchemaToolMetrics:
        return self._metrics
