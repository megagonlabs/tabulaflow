import os
import contextlib
from phoenix.otel import register


with open(os.devnull, "w") as fnull, contextlib.redirect_stdout(fnull):
    if os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"):
        tracer_provider = register(
            project_name="default",
            auto_instrument=True,
        )
