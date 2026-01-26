from typing import ClassVar
from mintq.schema import SQLSchema, Usage
from mintq.db_connector import BaseSQLDBConnector
from mintq.preprocessors.components.column_profiler import ColumnProfiler
from mintq.preprocessors.components.schema_compressor import SchemaCompressor
from mintq.preprocessors.base import CachedPreprocessorMixin, preprocessor_registry


@preprocessor_registry.register
class SchemaPreprocessor(CachedPreprocessorMixin):
    name: ClassVar[str] = "schema_preprocessor"
    output_type: ClassVar = SQLSchema

    def __init__(self, llm: str = "openai-responses:gpt-5-mini", compress_schema: bool = True):
        self.llm = llm
        self.compressor = SchemaCompressor() if compress_schema else None
        self.column_profiler = ColumnProfiler(llm)
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    async def _preprocess_impl_async(self, db_connector: BaseSQLDBConnector) -> SQLSchema:
        schema = db_connector.schema
        if self.compressor is not None:
            schema = self.compressor.compress(schema)
        schema = await self.column_profiler.run_async(db_connector, schema)
        self._usage += self.column_profiler.usage()
        return schema
