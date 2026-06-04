__all__ = [
    "SchemaCompressor",
    "ColumnProfiler",
    "ForeignKeyPredictor",
    "TextSummarizer",
]


def __getattr__(name: str) -> object:
    """Lazy-load component classes to avoid circular imports."""
    _lazy = {
        "SchemaCompressor": "tabulaflow.preprocessors.components.schema_compressor",
        "ColumnProfiler": "tabulaflow.preprocessors.components.column_profiler",
        "ForeignKeyPredictor": "tabulaflow.preprocessors.components.fk_predictor",
        "TextSummarizer": "tabulaflow.preprocessors.components.text_summarizer",
    }
    if name in _lazy:
        import importlib

        mod = importlib.import_module(_lazy[name])
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module 'tabulaflow.preprocessors.components' has no attribute {name!r}")
