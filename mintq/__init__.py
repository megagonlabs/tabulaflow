from mintq import patches  # noqa: F401
import logging
import os
from importlib.metadata import version

from mintq.agenthub.base import agent_registry
from mintq.datahub.base import dataset_registry
from mintq.metrics.base import metric_registry
from mintq.formatters.base import formatter_registry
from mintq.preprocessors.base import preprocessor_registry

logger = logging.getLogger(__name__)


def configure() -> None:
    """Set up logging, tracing, and instrumentation.

    Call this once from your entry point before running any pipeline.
    Reads configuration from environment variables and ``mintq_config``.
    """
    from mintq.config import mintq_config

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("mintq").setLevel(mintq_config.log_level)

    logger.info("MINTQ Configuration: %s", mintq_config)

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

    if mintq_config.instrument_enabled:
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
