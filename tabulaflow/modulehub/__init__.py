"""LLM-powered schema-analysis modules.

Each module takes a database connector and produces derived schema knowledge
(summaries, ER diagrams, predicted foreign keys, column profiles) that agents
consume. Depends on ``core`` and on ``toolhub`` (for ``run_query``); sits below
the agents (``chat`` / ``research``).
"""

from tabulaflow.modulehub.base import (
    BaseDBPreprocessor,
    BaseDatasetPreprocessor,
    CachedPreprocessorMixin,
    preprocessor_registry,
)
from tabulaflow.modulehub.column_profiler import ColumnProfiler
from tabulaflow.modulehub.db_summarizer import DBSummarizer
from tabulaflow.modulehub.er_diagram import ERDiagramSynthesizer
from tabulaflow.modulehub.schema_preprocessor import SchemaPreprocessor

__all__ = [
    "BaseDBPreprocessor",
    "BaseDatasetPreprocessor",
    "CachedPreprocessorMixin",
    "preprocessor_registry",
    "ColumnProfiler",
    "DBSummarizer",
    "ERDiagramSynthesizer",
    "SchemaPreprocessor",
]
