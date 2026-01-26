from typing import ClassVar
from pydantic_ai import Tool
from pydantic import BaseModel
from mintq.formatters import BaseSQLSchemaFormatter
from mintq.schema import SQLSchema
from mintq.preprocessors.components.schema_compressor import SchemaCompressor


class GetSchemaToolMetrics(BaseModel):
    num_calls: int = 0


class GetSchemaTool:
    name: ClassVar = "get_schema"

    def __init__(
        self, schema: SQLSchema, formatter: BaseSQLSchemaFormatter, compressor: SchemaCompressor | None = None
    ):
        self.schema = schema
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
        schema = self.schema if self.compressor is None else await self.compressor.run_async(self.schema)
        return self.formatter.format(schema)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetSchemaToolMetrics:
        return self._metrics
