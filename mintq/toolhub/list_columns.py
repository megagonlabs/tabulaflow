from dataclasses import dataclass, field
from pydantic_ai import Tool
from pydantic import BaseModel
from typing import ClassVar
from mintq.schema import SQLSchema
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.toolhub.utils import equals_ci


class ListColumnsToolMetrics(BaseModel):
    error_table_not_found: int = 0


@dataclass
class ListColumnsTool:
    name: ClassVar[str] = "list_columns"
    schema: SQLSchema
    formatter: BaseSQLSchemaFormatter
    metrics_: ListColumnsToolMetrics = field(default_factory=ListColumnsToolMetrics)

    async def __call__(self, schema_name: str | None, table_name: str) -> str:
        """
        List the columns of a table.

        Args:
            schema_name: The name of the schema to which the table belongs, or None if schema is not applicable.
            table_name: The name of the table to list the columns of.
        """
        # If there is only a single schema, use it regardless of what the agent specified
        all_schema_names = [t.schema_name for t in self.schema.tables]
        if len(set(all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        for table in self.schema.tables:
            if equals_ci(table.schema_name, schema_name) and table.name.lower() == table_name.lower():
                return self.formatter.format_table(table)
        self.metrics_.error_table_not_found += 1
        return f"(table {table_name} in schema {schema_name} not found)"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
