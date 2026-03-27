from mintq.agenthub.base import (
    BaseAgentConfig,
    BaseSimpleSQLAgent,
    BaseAmbigSQLAgent,
    BaseDbtAgent,
    NL2QAgent,
    agent_registry,
)

__all__ = [
    "BaseSimpleSQLAgent",
    "BaseAmbigSQLAgent",
    "BaseDbtAgent",
    "NL2QAgent",
    "BaseAgentConfig",
    "BasicAgentConfig",
    "SimpleZeroShotNL2Q",
    "SimpleZeroShotNL2QConfig",
    "DirectPrompting",
    "MiniAgent",
    "SQLAgent",
    "MintqAgent",
    "AmbigSimpleSQLAgent",
    "AmbigFlatSQLAgent",
    "AmbigStructuredSQLAgent",
    "DbtAgent",
    "agent_registry",
]


def __getattr__(name: str) -> object:
    """Lazy-load agent classes to avoid circular imports."""
    _lazy = {
        "SimpleZeroShotNL2Q": "mintq.agenthub.simple_zero_shot",
        "SimpleZeroShotNL2QConfig": "mintq.agenthub.simple_zero_shot",
        "DirectPrompting": "mintq.agenthub.direct_prompting",
        "MiniAgent": "mintq.agenthub.mini_agent",
        "SQLAgent": "mintq.agenthub.sql_agent",
        "MintqAgent": "mintq.agenthub.mintq_agent",
        "AmbigSimpleSQLAgent": "mintq.agenthub.ambig_simple",
        "AmbigFlatSQLAgent": "mintq.agenthub.ambig_flat",
        "AmbigStructuredSQLAgent": "mintq.agenthub.ambig_structured",
        "DbtAgent": "mintq.agenthub.dbt_agent",
        "BasicAgentConfig": "mintq.agenthub.utils",
    }
    if name in _lazy:
        import importlib

        mod = importlib.import_module(_lazy[name])
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module 'mintq.agenthub' has no attribute {name!r}")
