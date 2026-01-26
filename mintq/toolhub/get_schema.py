from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.db_connector import BaseSQLDBConnector
from mintq.preprocessors import BaseSchemaCompressor


class GetSchemaToolMetrics(BaseModel):
    num_calls: int = 0


class GetSchemaTool:
    name: ClassVar = "get_schema"

    def __init__(
        self, db_connector: BaseSQLDBConnector, formatter: BaseSQLSchemaFormatter, compressor: BaseSchemaCompressor | None = None
    ):
        self.db_connector = db_connector
        self.formatter = formatter
        self.compressor = compressor
        self._metrics = GetSchemaToolMetrics()

    async def __call__(self) -> str:
        """
        Get the schema of the database.

        Example:
        ```python
        get_schema()
        ```
        """
        self._metrics.num_calls += 1
        schema = self.db_connector.schema if self.compressor is None else await self.compressor.preprocess_async(self.db_connector)
        return self.formatter.format(schema)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetSchemaToolMetrics:
        return self._metrics
