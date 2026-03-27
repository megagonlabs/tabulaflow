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


def configure(*, log_level: int | None = None) -> None:
    """Set up logging, tracing, and instrumentation.

    Call this once from your entry point before running any pipeline.
    Reads configuration from environment variables and ``mintq_config``.

    Args:
        log_level: Override the mintq logger level. If None, uses the
            level from ``MINTQ_LOG_LEVEL`` env var (default INFO).
    """
    from mintq.config import mintq_config

    _register_custom_model_prices()

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("mintq").setLevel(log_level if log_level is not None else mintq_config.log_level)

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


def _register_custom_model_prices() -> None:
    """Register pricing for models not yet in litellm's bundled data.

    Entries are skipped if litellm already has them, so this is safe
    to leave in place after litellm adds native support.
    """
    import litellm

    custom_prices = {
        "gpt-5.4-mini": {
            "input_cost_per_token": 7.5e-07,
            "output_cost_per_token": 4.5e-06,
            "max_input_tokens": 400000,
            "max_output_tokens": 128000,
            "max_tokens": 128000,
            "litellm_provider": "openai",
            "mode": "chat",
        },
    }
    for model, info in custom_prices.items():
        if model not in litellm.model_cost:
            litellm.model_cost[model] = info


__all__ = [
    "agent_registry",
    "configure",
    "dataset_registry",
    "metric_registry",
    "formatter_registry",
    "preprocessor_registry",
]


__version__ = version("mintq")
