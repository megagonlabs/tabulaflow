__all__ = [
    "SchemaCompressor",
    "ColumnProfiler",
    "ForeignKeyPredictor",
]


def __getattr__(name: str) -> object:
    """Lazy-load component classes to avoid circular imports."""
    _lazy = {
        "SchemaCompressor": "mintq.preprocessors.components.schema_compressor",
        "ColumnProfiler": "mintq.preprocessors.components.column_profiler",
        "ForeignKeyPredictor": "mintq.preprocessors.components.fk_predictor",
    }
    if name in _lazy:
        import importlib

        mod = importlib.import_module(_lazy[name])
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module 'mintq.preprocessors.components' has no attribute {name!r}")
