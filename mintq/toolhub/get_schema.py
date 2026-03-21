from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.db_connector.base import BaseSQLDBConnector
from mintq.preprocessors.components.schema_compressor import SchemaCompressor
from mintq.schema import SQLSchema, SQLTableSchema, TableRef
from mintq.toolhub.utils import equals_ci


class GetSchemaToolMetrics(BaseModel):
    num_calls: int = 0


class GetSchemaTool:
    """Tool that retrieves the full database schema.

    Formats and returns the complete schema using the configured formatter.

    Attributes:
        schema: The SQL schema containing all available tables. Can be a
            compressed schema produced by SchemaCompressor.
        formatter: The formatter used to render the schema as text.
    """

    name: ClassVar = "get_schema"

    def __init__(self, schema: SQLSchema, formatter: BaseSQLSchemaFormatter):
        self.schema = schema
        self.formatter = formatter
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
        return self.formatter.format(self.schema)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetSchemaToolMetrics:
        return self._metrics
