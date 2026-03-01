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
    name: ClassVar = "get_table_schema"

    def __init__(self, db_connector: BaseSQLDBConnector, formatter: BaseSQLSchemaFormatter):
        self.db_connector = db_connector
        self.formatter = formatter
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
        all_schema_names = [t.schema_name for t in self.db_connector.schema.tables]
        if len(set(all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        table = None
        for t in self.db_connector.schema.tables:
            if equals_ci(t.schema_name, schema_name) and t.name.lower() == table_name.lower():
                table = t
                break

        if table is None:
            self._metrics.error_table_not_found += 1
            return f"(table {table_name} in schema {schema_name} not found)"

        return self.formatter.format_table(table)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetTableSchemaToolMetrics:
        return self._metrics
