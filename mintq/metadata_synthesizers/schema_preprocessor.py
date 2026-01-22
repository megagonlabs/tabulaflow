from typing import ClassVar
import os
import asyncio
import collections
from mintq.config import config
from mintq.metadata_synthesizers.column_profiler import ColumnProfiler
from mintq.metadata_synthesizers.schema_compressor import SchemaCompressor
from mintq.schema import SQLSchema, Usage
from mintq.db_connector import BaseSQLDBConnector


_db_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)


class SchemaPreprocessor:
    name: ClassVar[str] = "schema_preprocessor"

    def __init__(self, llm: str = "openai-responses:gpt-5-mini", compress_schema: bool = True):
        self.llm = llm
        self.compressor = SchemaCompressor() if compress_schema else None
        self.column_profiler = ColumnProfiler(llm)
        self._usage = Usage.create(llm=llm)

    def usage(self) -> Usage:
        return self._usage

    async def run_async(self, db_connector: BaseSQLDBConnector) -> SQLSchema:
        schema_cache_dir = os.path.join(config.cache_dir, "schema_preprocessor")
        os.makedirs(schema_cache_dir, exist_ok=True)
        cache_path = os.path.join(schema_cache_dir, f"{db_connector.global_id}.json")

        lock = _db_locks[db_connector.global_id]
        async with lock:
            if config.cache_enabled and os.path.exists(cache_path):
                if config.cache_refresh:
                    os.remove(cache_path)
                else:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return SQLSchema.model_validate_json(f.read())

            schema = db_connector.schema
            if self.compressor is not None:
                schema = await self.compressor.run_async(schema)
            schema = await self.column_profiler.run_async(db_connector, schema)

            if config.cache_enabled:
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(schema.model_dump_json(indent=2))
            return schema
