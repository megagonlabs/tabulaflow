from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.schema import SQLSchema


class GetSchemaToolMetrics(BaseModel):
    pass


class GetSchemaTool:
    name: ClassVar = "get_schema"

    def __init__(self, schema: SQLSchema, formatter: BaseSQLSchemaFormatter):
        self.schema = schema
        self.formatter = formatter
        self._metrics = GetSchemaToolMetrics()

    async def __call__(self) -> str:
        """
        Get the schema of the database.
        """
        return self.formatter.format(self.schema)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetSchemaToolMetrics:
        return self._metrics
