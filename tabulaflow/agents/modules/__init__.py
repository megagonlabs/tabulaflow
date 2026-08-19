"""LLM-powered schema-analysis modules.

Each module takes a database connector and produces derived schema knowledge
(summaries, ER diagrams, predicted foreign keys, column profiles) that agents
consume. These modules share the agents layer with the model-facing tools they
use and depend on the lower platform layers.
"""

from tabulaflow.agents.modules.base import (
    BaseDBPreprocessor,
    BaseDatasetPreprocessor,
    CachedPreprocessorMixin,
    preprocessor_registry,
)
from tabulaflow.agents.modules.column_profiler import ColumnProfiler
from tabulaflow.agents.modules.db_summarizer import DBSummarizer
from tabulaflow.agents.modules.schema_preprocessor import SchemaPreprocessor

__all__ = [
    "BaseDBPreprocessor",
    "BaseDatasetPreprocessor",
    "CachedPreprocessorMixin",
    "preprocessor_registry",
    "ColumnProfiler",
    "DBSummarizer",
    "SchemaPreprocessor",
]
