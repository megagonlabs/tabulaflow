import logging
import os
from importlib.metadata import version
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mintq.agenthub.base import agent_registry as agent_registry
    from mintq.datahub.base import dataset_registry as dataset_registry
    from mintq.formatters.base import formatter_registry as formatter_registry
    from mintq.metrics.base import metric_registry as metric_registry
    from mintq.preprocessors.base import preprocessor_registry as preprocessor_registry


def __getattr__(name: str) -> object:
    """Lazy-load registries on first access to avoid heavy imports at startup."""
    _lazy = {
        "agent_registry": ("mintq.agenthub.base", "agent_registry"),
        "dataset_registry": ("mintq.datahub.base", "dataset_registry"),
        "metric_registry": ("mintq.metrics.base", "metric_registry"),
        "formatter_registry": ("mintq.formatters.base", "formatter_registry"),
        "preprocessor_registry": ("mintq.preprocessors.base", "preprocessor_registry"),
    }
    if name in _lazy:
        module_path, attr = _lazy[name]
        import importlib

        mod = importlib.import_module(module_path)
        val = getattr(mod, attr)
        globals()[name] = val
        return val
    raise AttributeError(f"module 'mintq' has no attribute {name!r}")


logger = logging.getLogger(__name__)


def configure(**kwargs: object) -> None:
    """Set up logging, tracing, and instrumentation.

    Call this once from your entry point before running any pipeline.
    Accepts the same keyword arguments as :meth:`MintqConfig.configure`
    to override defaults programmatically.

    Example::

        import mintq

        mintq.configure(
            column_stats_mode="always_skip",
            query_cache_enabled=False,
            instrument_enabled=False,
        )
    """
    import mintq.patches
    from mintq.config import mintq_config

    mintq_config.configure(**kwargs)

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("mintq").setLevel(mintq_config.log_level)

    logger.info("MINTQ Configuration: %s", mintq_config)

    if mintq_config.instrument_enabled:
        mintq.patches.setup()

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


__version__ = version("mintq")
