"""Observability policy for TabulaFlow research pipelines."""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Mapping, Sequence

from opentelemetry.context import Context
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, Decision, ParentBased, Sampler, SamplingResult
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import AttributeValue

from tabulaflow.agents.observability import instrument_agents

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


__all__ = ["configure_research_observability"]
