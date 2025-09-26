import os
import contextlib
from langfuse import get_client
from phoenix.otel import register
from mintq.agenthub import agent_registry
from mintq.datahub import dataset_registry
from mintq.metrics import metric_registry


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
        print("Langfuse client is authenticated and ready!")
    else:
        print("Authentication failed. Please check your credentials and host.")

__all__ = [
    "agent_registry",
    "dataset_registry",
    "metric_registry",
]
