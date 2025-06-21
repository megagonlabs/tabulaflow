from dataclasses import dataclass, field
from pydantic_ai import Tool
from typing import ClassVar
from mintq.schema import SQLSchema
from mintq.formatters import BaseSQLSchemaFormatter


@dataclass
class ListColumnsTool:
    name: ClassVar[str] = "list_columns"
    schema: SQLSchema
    formatter: BaseSQLSchemaFormatter
    metrics_: dict = field(default_factory=dict)

    async def __call__(self, table: str) -> str:
        """
        List the columns of a table.

        Args:
            table: The name of the table to list the columns of.
        """
        for table_schema in self.schema.tables:
            table_id = self.formatter.format_table_name(table_schema)
            if table_id == table:
                return self.formatter.format_table(table_schema)
        self.metrics_["list_columns_table_not_found"] += 1
        return f"(table {table} not found)"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
