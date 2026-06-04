from typing import ClassVar, Literal
from tabulaflow.core.types import SQLSchema, Usage
from tabulaflow.core.db_connector import BaseSQLDBConnector
from tabulaflow.preprocessors.components.column_profiler import ColumnProfiler
from tabulaflow.preprocessors.components.schema_compressor import SchemaCompressor
from tabulaflow.preprocessors.components.fk_predictor import ForeignKeyPredictor
from tabulaflow.preprocessors.base import (
    CachedPreprocessorMixin,
    preprocessor_registry,
    CacheableResult,
)


@preprocessor_registry.register
class SchemaPreprocessor(CachedPreprocessorMixin[SQLSchema]):
    name: ClassVar[str] = "schema_preprocessor"
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"
    output_type: ClassVar[type[CacheableResult]] = SQLSchema

    def __init__(
        self,
        column_profiler_llm: str | None = None,
        foreign_key_predictor_llm: str | None = None,
        compress_schema: bool = True,
    ):
        self.column_profiler_llm = column_profiler_llm
        self.foreign_key_predictor_llm = foreign_key_predictor_llm
        self.compressor = SchemaCompressor() if compress_schema else None
        self.column_profiler = ColumnProfiler(column_profiler_llm) if column_profiler_llm is not None else None
        self.foreign_key_predictor = (
            ForeignKeyPredictor(foreign_key_predictor_llm) if foreign_key_predictor_llm is not None else None
        )
        self._usage = Usage.create()

    def usage(self) -> Usage:
        return self._usage

    async def _preprocess_impl_async(self, db_connector: BaseSQLDBConnector) -> SQLSchema:
        schema = db_connector.schema
        if self.compressor is not None:
            schema = self.compressor.compress(schema)
        if self.foreign_key_predictor is not None:
            schema = await self.foreign_key_predictor.run_async(db_connector, schema)
            self._usage += self.foreign_key_predictor.usage()
        if self.column_profiler is not None:
            schema = await self.column_profiler.run_async(db_connector, schema)
            self._usage += self.column_profiler.usage()
        for table in schema.tables:
            table.columns = [col for col in table.columns if not col.not_used]
        schema.tables = [table for table in schema.tables if table.columns]
        return schema
