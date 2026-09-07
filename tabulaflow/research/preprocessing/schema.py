"""Research schema enrichment through LLM profiling and FK prediction."""

from pathlib import Path
from typing import ClassVar, Literal

from pydantic_ai.settings import ModelSettings

from tabulaflow.agents._cache import load_or_compute_model
from tabulaflow.agents.runtime import _get_agent_runtime
from tabulaflow.agents.trace import Usage
from tabulaflow.core._cache import stable_cache_key
from tabulaflow.core.schema import SQLSchema
from tabulaflow.data import SQLConnector
from tabulaflow.research.preprocessing.registry import preprocessor_registry
from tabulaflow.research.preprocessing.column_profiler import ColumnProfiler
from tabulaflow.research.preprocessing.fk_predictor import ForeignKeyPredictor

_SCHEMA_CACHE_VERSION = "v1"


@preprocessor_registry.register
class SchemaPreprocessor:
    name: ClassVar[str] = "schema_preprocessor"
    input_type: ClassVar[Literal["db_connector"]] = "db_connector"

    def __init__(
        self,
        column_profiler_llm: str | None = None,
        foreign_key_predictor_llm: str | None = None,
        column_profiler_model_settings: ModelSettings | None = None,
        foreign_key_predictor_model_settings: ModelSettings | None = None,
    ) -> None:
        self.column_profiler_llm = column_profiler_llm
        self.foreign_key_predictor_llm = foreign_key_predictor_llm
        self.column_profiler_model_settings = column_profiler_model_settings
        self.foreign_key_predictor_model_settings = foreign_key_predictor_model_settings
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

    def _cache_path(self, cache_dir: Path, connector: SQLConnector) -> Path:
        key = stable_cache_key(
            {
                "version": _SCHEMA_CACHE_VERSION,
                "global_id": connector.global_id,
                "schema": connector.schema.model_dump(mode="json"),
                "column_profiler_llm": self.column_profiler_llm,
                "column_profiler_model_settings": self.column_profiler_model_settings,
                "foreign_key_predictor_llm": self.foreign_key_predictor_llm,
                "foreign_key_predictor_model_settings": self.foreign_key_predictor_model_settings,
            }
        )
        return cache_dir / "agent" / "schema_preprocessing" / f"{_SCHEMA_CACHE_VERSION}@{key}.json"

    async def preprocess_async(self, connector: SQLConnector) -> SQLSchema:
        config = _get_agent_runtime().config
        return await load_or_compute_model(
            path=self._cache_path(config.cache_dir, connector),
            mode=config.preprocessing_cache_mode,
            model_type=SQLSchema,
            compute=lambda: self._preprocess(connector),
        )

    async def _preprocess(self, connector: SQLConnector) -> SQLSchema:
        schema = connector.schema
        if self.foreign_key_predictor is not None:
            schema = await self.foreign_key_predictor.run_async(connector, schema)
            self._usage += self.foreign_key_predictor.usage()
        if self.column_profiler is not None:
            schema = await self.column_profiler.run_async(connector, schema)
            self._usage += self.column_profiler.usage()
        return schema
