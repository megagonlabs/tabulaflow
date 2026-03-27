from mintq.formatters.base import BaseSQLSchemaFormatter, NL2QFormatter, formatter_registry

__all__ = [
    "BaseSQLSchemaFormatter",
    "NL2QFormatter",
    "SQLBasicSchemaFormatter",
    "SQLDDLSchemaFormatter",
    "ERDiagramMermaidFormatter",
    "formatter_registry",
]


def __getattr__(name: str) -> object:
    """Lazy-load formatter classes to avoid circular imports."""
    _lazy = {
        "SQLBasicSchemaFormatter": "mintq.formatters.sql_basic",
        "SQLDDLSchemaFormatter": "mintq.formatters.sql_ddl",
        "ERDiagramMermaidFormatter": "mintq.formatters.er_diagram",
    }
    if name in _lazy:
        import importlib

        mod = importlib.import_module(_lazy[name])
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module 'mintq.formatters' has no attribute {name!r}")
