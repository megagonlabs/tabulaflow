from typing import ClassVar, Literal
from mintq.schema import SQLSchema, Usage
from mintq.db_connector import BaseSQLDBConnector
from mintq.preprocessors.components.column_profiler import ColumnProfiler
from mintq.preprocessors.components.schema_compressor import SchemaCompressor
from mintq.preprocessors.components.fk_predictor import ForeignKeyPredictor
from mintq.preprocessors.base import CachedPreprocessorMixin, preprocessor_registry, CacheableResult


@preprocessor_registry.register
class SchemaPreprocessor(CachedPreprocessorMixin[SQLSchema]):
    name: ClassVar[str] = "schema_preprocessor"
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"
    output_type: ClassVar[type[CacheableResult]] = SQLSchema

    def __init__(
        self,
        column_profiler_llm: str = "openai-responses:gpt-5-mini",
        foreign_key_predictor_llm: str = "openai-responses:gpt-5-mini",
        compress_schema: bool = True,
    ):
        self.column_profiler_llm = column_profiler_llm
        self.foreign_key_predictor_llm = foreign_key_predictor_llm
        self.compressor = SchemaCompressor() if compress_schema else None
        self.column_profiler = ColumnProfiler(column_profiler_llm)
        self.foreign_key_predictor = ForeignKeyPredictor(foreign_key_predictor_llm)
        self._usage = Usage.create(llm=foreign_key_predictor_llm)

    def usage(self) -> Usage:
        return self._usage

    async def _preprocess_impl_async(self, db_connector: BaseSQLDBConnector) -> SQLSchema:
        schema = db_connector.schema
        if self.compressor is not None:
            schema = self.compressor.compress(schema)
        schema = await self.foreign_key_predictor.run_async(db_connector, schema)
        self._usage += self.foreign_key_predictor.usage()
        schema = await self.column_profiler.run_async(db_connector, schema)
        self._usage += self.column_profiler.usage()
        for table in schema.tables:
            table.columns = [col for col in table.columns if not col.not_used]
        schema.tables = [table for table in schema.tables if table.columns]
        return schema
