import logging
import os
from importlib.metadata import version
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabulaflow.research.agenthub.base import agent_registry as agent_registry
    from tabulaflow.research.datahub.base import dataset_registry as dataset_registry
    from tabulaflow.core.formatters.base import formatter_registry as formatter_registry
    from tabulaflow.research.metrics.base import metric_registry as metric_registry
    from tabulaflow.modulehub.base import preprocessor_registry as preprocessor_registry


def __getattr__(name: str) -> object:
    """Lazy-load registries on first access to avoid heavy imports at startup."""
    _lazy = {
        "agent_registry": ("tabulaflow.research.agenthub.base", "agent_registry"),
        "dataset_registry": ("tabulaflow.research.datahub.base", "dataset_registry"),
        "metric_registry": ("tabulaflow.research.metrics.base", "metric_registry"),
        "formatter_registry": ("tabulaflow.core.formatters.base", "formatter_registry"),
        "preprocessor_registry": ("tabulaflow.modulehub.base", "preprocessor_registry"),
    }
    if name in _lazy:
        module_path, attr = _lazy[name]
        import importlib

        mod = importlib.import_module(module_path)
        val = getattr(mod, attr)
        globals()[name] = val
        return val
    raise AttributeError(f"module 'tabulaflow' has no attribute {name!r}")


logger = logging.getLogger(__name__)


def configure(**kwargs: object) -> None:
    """Set up logging, tracing, and instrumentation.

    Call this once from your entry point before running any pipeline.
    Accepts the same keyword arguments as :meth:`TabulaflowConfig.configure`
    to override defaults programmatically.

    Example::

        import tabulaflow

        tabulaflow.configure(
            column_stats_mode="always_skip",
            query_cache_enabled=False,
            instrument_enabled=False,
        )
    """
    from tabulaflow.core import llm
    from tabulaflow.core.config import tabulaflow_config

    tabulaflow_config.configure(**kwargs)

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("tabulaflow").setLevel(tabulaflow_config.log_level)

    logger.debug("TABULAFLOW Configuration: %s", tabulaflow_config)

    # Process-global LLM setup (was patches.setup(); throttling/tool-call parsing
    # now apply per-agent via core.llm.make_agent, not by monkey-patching).
    llm.register_custom_model_prices()
    if tabulaflow_config.disable_bigquery_tracing:
        llm.disable_bigquery_tracing()

    if tabulaflow_config.instrument_enabled:
        if os.getenv("PHOENIX_COLLECTOR_ENDPOINT"):
            from phoenix.otel import register

            register(project_name="default", auto_instrument=True)

        if os.getenv("LANGFUSE_HOST"):
            from langfuse import get_client

            langfuse = get_client()
            if langfuse.auth_check():
                logger.info("Langfuse client authenticated.")
            else:
                logger.error("Langfuse authentication failed. Check credentials and host.")

        from pydantic_ai import Agent

        Agent.instrument_all()


__all__ = [
    "agent_registry",
    "configure",
    "dataset_registry",
    "metric_registry",
    "formatter_registry",
    "preprocessor_registry",
]


__version__ = version("tabulaflow")
