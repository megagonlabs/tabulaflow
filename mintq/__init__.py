import os
from phoenix.otel import register

if os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"):
    tracer_provider = register(
        project_name="default",
        auto_instrument=True,
    )
