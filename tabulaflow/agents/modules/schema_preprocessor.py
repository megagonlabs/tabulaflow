from typing import ClassVar, Literal
from pydantic_ai.settings import ModelSettings
from tabulaflow.core import SQLSchema
from tabulaflow.agents.trace import Usage
from tabulaflow.data import SQLConnectorProtocol
from tabulaflow.agents.modules.column_profiler import ColumnProfiler
from tabulaflow.data.schema_compressor import SchemaCompressor
from tabulaflow.agents.modules.fk_predictor import ForeignKeyPredictor
from tabulaflow.agents.modules.base import (
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
        column_profiler_model_settings: ModelSettings | None = None,
        foreign_key_predictor_model_settings: ModelSettings | None = None,
        compress_schema: bool = True,
    ):
        self.column_profiler_llm = column_profiler_llm
        self.foreign_key_predictor_llm = foreign_key_predictor_llm
        self.column_profiler_model_settings = column_profiler_model_settings
        self.foreign_key_predictor_model_settings = foreign_key_predictor_model_settings
        self.compressor = SchemaCompressor() if compress_schema else None
        self.column_profiler = (
            ColumnProfiler(column_profiler_llm, model_settings=column_profiler_model_settings)
            if column_profiler_llm is not None
            else None
        )
        self.foreign_key_predictor = (
            ForeignKeyPredictor(foreign_key_predictor_llm, model_settings=foreign_key_predictor_model_settings)
            if foreign_key_predictor_llm is not None
            else None
        )
        self._usage = Usage.create()

    def usage(self) -> Usage:
        return self._usage

    async def _preprocess_impl_async(self, db_connector: SQLConnectorProtocol) -> SQLSchema:
        schema = db_connector.schema
        if self.compressor is not None:
            schema = self.compressor.compress(schema)
        if self.foreign_key_predictor is not None:
            schema = await self.foreign_key_predictor.run_async(db_connector, schema)
            self._usage += self.foreign_key_predictor.usage()
        if self.column_profiler is not None:
            schema = await self.column_profiler.run_async(db_connector, schema)
            self._usage += self.column_profiler.usage()
        return schema
