from mintq import patches  # noqa: F401
import os
import contextlib
from pydantic_ai import Agent
from langfuse import get_client
from phoenix.otel import register
from importlib.metadata import version
from mintq.agenthub.base import agent_registry
from mintq.datahub.base import dataset_registry
from mintq.metrics.base import metric_registry
from mintq.formatters.base import formatter_registry
from mintq.config import config
import logging


logger = logging.getLogger(__name__)


logger.info("MINTQ Configuration: %s", config)

if os.getenv("PHOENIX_COLLECTOR_ENDPOINT"):
    with open(os.devnull, "w") as fnull, contextlib.redirect_stdout(fnull):
        tracer_provider = register(
            project_name="default",
            auto_instrument=True,
        )


if os.getenv("LANGFUSE_HOST"):
    langfuse = get_client()

    # Verify connection
    if langfuse.auth_check():
        logger.info("Langfuse client is authenticated and ready!")
    else:
        logger.error("Langfuse authentication failed. Please check your credentials and host.")


if config.instrument_enabled:
    Agent.instrument_all()

__all__ = [
    "agent_registry",
    "dataset_registry",
    "metric_registry",
    "formatter_registry",
]


__version__ = version("mintq")
