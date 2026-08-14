from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from tabulaflow.output.schema_formatters import BaseSQLSchemaFormatter
from tabulaflow.core import SQLSchema


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
