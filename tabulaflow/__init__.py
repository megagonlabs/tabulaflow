import logging
import os
from importlib.metadata import version


logger = logging.getLogger(__name__)


def configure(**kwargs: object) -> None:
    """Set up logging, tracing, and instrumentation.

    Call this once from your entry point before running any pipeline.
    Accepts the same keyword arguments as :meth:`TabulaflowConfig.configure`
    to override defaults programmatically.

    Example::

        import tabulaflow

        tabulaflow.configure(
            query_cache_enabled=False,
            instrument_enabled=False,
        )
    """
    from tabulaflow.config import tabulaflow_config

    tabulaflow_config.configure(**kwargs)

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("tabulaflow").setLevel(tabulaflow_config.log_level)

    logger.debug("TABULAFLOW Configuration: %s", tabulaflow_config)

    # Process-global LLM setup (custom prices + BigQuery-tracing suppression) is
    # deferred: it imports litellm (~1s), so it would block startup before the first
    # banner. ``agents.llm.make_agent`` runs it once, lazily, when the first agent is
    # built (in the background session worker for the TUI). See llm.ensure_global_setup.

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
    "configure",
]


__version__ = version("tabulaflow")
