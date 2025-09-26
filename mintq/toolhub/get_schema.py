from dataclasses import dataclass, field
from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.db_connector import BaseAsyncSQLDBConnector
from mintq.toolhub.utils import format_df
from mintq.formatters import BaseSQLSchemaFormatter


class GetSchemaToolMetrics(BaseModel):
    pass


@dataclass
class GetSchemaTool:
    name: ClassVar[str] = "get_schema"
    db_connector: BaseAsyncSQLDBConnector
    formatter: BaseSQLSchemaFormatter
    metrics_: GetSchemaToolMetrics = field(default_factory=GetSchemaToolMetrics)

    async def __call__(self) -> str:
        """
        Get the schema of the database.
        """
        return self.formatter.format(self.db_connector.schema)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
