"""Tracing policy and instrumentation for TabulaFlow research runs."""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable, Mapping, Sequence
from functools import wraps
from typing import Any

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, Decision, ParentBased, Sampler, SamplingResult
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import AttributeValue

from tabulaflow.agents import instrument_agents
from tabulaflow.research.types import NL2QTask

logger = logging.getLogger(__name__)

_BIGQUERY_SCOPE = "google.cloud.bigquery.opentelemetry_tracing"
_configured = False
_configure_lock = threading.Lock()


class _ResearchSampler(Sampler):
    """Drop noisy BigQuery spans before Phoenix records or exports them."""

    def __init__(self) -> None:
        self._default = ParentBased(ALWAYS_ON)

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Mapping[str, AttributeValue] | None = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        if attributes is not None and attributes.get("db.system") == "BigQuery":
            return SamplingResult(Decision.DROP)
        return self._default.should_sample(parent_context, trace_id, name, kind, attributes, links, trace_state)

    def get_description(self) -> str:
        return "ResearchSampler"


def trace_prediction(predict_async_fn: Callable[..., Any]) -> Callable[..., Any]:
    """Trace a top-level research prediction without nesting duplicate spans."""

    @wraps(predict_async_fn)
    async def wrapper(self: Any, task: NL2QTask, *args: Any, **kwargs: Any) -> Any:
        from tabulaflow import __version__

        tracer = trace.get_tracer_provider().get_tracer("tabulaflow", __version__)
        current_span = trace.get_current_span()
        if current_span.get_span_context().is_valid:
            return await predict_async_fn(self, task, *args, **kwargs)
        with tracer.start_as_current_span(f"qid={task.qid}"):
            return await predict_async_fn(self, task, *args, **kwargs)

    return wrapper


def configure_research_observability() -> None:
    """Configure research tracing and enable agent instrumentation once."""
    global _configured
    if _configured:
        return
    with _configure_lock:
        if _configured:
            return

        if os.getenv("PHOENIX_COLLECTOR_ENDPOINT"):
            from phoenix.otel import register

            register(project_name="default", sampler=_ResearchSampler())

        if os.getenv("LANGFUSE_HOST"):
            from langfuse import Langfuse

            langfuse = Langfuse(blocked_instrumentation_scopes=[_BIGQUERY_SCOPE])
            if langfuse.auth_check():
                logger.info("Langfuse client authenticated.")
            else:
                logger.error("Langfuse authentication failed. Check credentials and host.")

        instrument_agents()
        _configured = True


__all__ = ["configure_research_observability", "trace_prediction"]
