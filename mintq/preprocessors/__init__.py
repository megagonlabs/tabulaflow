from mintq.preprocessors.base import (
    BaseDBPreprocessor,
    BaseDatasetPreprocessor,
    CachedPreprocessorMixin,
    preprocessor_registry,
)

__all__ = [
    "BaseDBPreprocessor",
    "BaseDatasetPreprocessor",
    "CachedPreprocessorMixin",
    "preprocessor_registry",
    "SchemaCompressor",
    "ColumnProfiler",
    "DBSummarizer",
    "SchemaPreprocessor",
    "ERDiagramSynthesizer",
    "QuestionEmbedder",
]


def __getattr__(name: str) -> object:
    """Lazy-load preprocessor classes to avoid circular imports."""
    _lazy = {
        "DBSummarizer": "mintq.preprocessors.db_summarizer",
        "SchemaPreprocessor": "mintq.preprocessors.schema_preprocessor",
        "ERDiagramSynthesizer": "mintq.preprocessors.er_diagram",
        "QuestionEmbedder": "mintq.preprocessors.question_embedder",
        "SchemaCompressor": "mintq.preprocessors.components.schema_compressor",
        "ColumnProfiler": "mintq.preprocessors.components.column_profiler",
    }
    if name in _lazy:
        import importlib

        mod = importlib.import_module(_lazy[name])
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module 'mintq.preprocessors' has no attribute {name!r}")
