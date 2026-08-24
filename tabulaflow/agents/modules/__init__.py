"""LLM-powered database and schema preprocessing."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tabulaflow.agents.modules.base import (
        BaseDatasetPreprocessor,
        BaseDBPreprocessor,
        CachedPreprocessorMixin,
        preprocessor_registry,
    )
    from tabulaflow.agents.modules.column_profiler import ColumnProfiler
    from tabulaflow.agents.modules.db_summarizer import DBSummarizer
    from tabulaflow.agents.modules.schema_preprocessor import SchemaPreprocessor

_LAZY_EXPORTS = {
    "BaseDatasetPreprocessor": ("tabulaflow.agents.modules.base", "BaseDatasetPreprocessor"),
    "BaseDBPreprocessor": ("tabulaflow.agents.modules.base", "BaseDBPreprocessor"),
    "CachedPreprocessorMixin": ("tabulaflow.agents.modules.base", "CachedPreprocessorMixin"),
    "ColumnProfiler": ("tabulaflow.agents.modules.column_profiler", "ColumnProfiler"),
    "DBSummarizer": ("tabulaflow.agents.modules.db_summarizer", "DBSummarizer"),
    "SchemaPreprocessor": ("tabulaflow.agents.modules.schema_preprocessor", "SchemaPreprocessor"),
    "preprocessor_registry": ("tabulaflow.agents.modules.base", "preprocessor_registry"),
}

__all__ = [
    "BaseDatasetPreprocessor",
    "BaseDBPreprocessor",
    "CachedPreprocessorMixin",
    "ColumnProfiler",
    "DBSummarizer",
    "SchemaPreprocessor",
    "preprocessor_registry",
]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_EXPORTS})
