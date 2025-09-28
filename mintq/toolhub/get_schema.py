from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.db_connector import BaseSQLDBConnector
from mintq.formatters import BaseSQLSchemaFormatter


class GetSchemaToolMetrics(BaseModel):
    pass


class GetSchemaTool:
    name: ClassVar = "get_schema"

    def __init__(self, db_connector: BaseSQLDBConnector, formatter: BaseSQLSchemaFormatter):
        self.db_connector = db_connector
        self.formatter = formatter
        self._metrics = GetSchemaToolMetrics()

    async def __call__(self) -> str:
        """
        Get the schema of the database.
        """
        return self.formatter.format(self.db_connector.schema)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def get_metrics(self) -> GetSchemaToolMetrics:
        return self._metrics
