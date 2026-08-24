import sys
from types import ModuleType
from unittest.mock import Mock

import pytest
from opentelemetry.sdk.trace.sampling import Decision
from pydantic_ai import Agent

import tabulaflow.agents.observability as agent_observability
import tabulaflow.research.observability as research_observability


def test_instrument_agents_is_available_from_agents_package() -> None:
    from tabulaflow.agents import instrument_agents

    assert instrument_agents is agent_observability.instrument_agents


def test_agent_instrumentation_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    instrument_all = Mock()
    monkeypatch.setattr(Agent, "instrument_all", instrument_all)
    monkeypatch.setattr(agent_observability, "_instrumented", False)

    agent_observability.instrument_agents()
    agent_observability.instrument_agents()

    instrument_all.assert_called_once_with()


def test_research_sampler_drops_bigquery_spans() -> None:
    result = research_observability._ResearchSampler().should_sample(
        None,
        1,
        "BigQuery.query",
        attributes={"db.system": "BigQuery"},
    )

    assert result.decision is Decision.DROP


def test_research_sampler_keeps_other_spans() -> None:
    result = research_observability._ResearchSampler().should_sample(
        None,
        1,
        "qid=1",
        attributes={"db.system": "PostgreSQL"},
    )

    assert result.decision is Decision.RECORD_AND_SAMPLE


def test_research_observability_is_explicit_and_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    instrument_agents = Mock()
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setattr(research_observability, "instrument_agents", instrument_agents)
    monkeypatch.setattr(research_observability, "_configured", False)

    research_observability.configure_research_observability()
    research_observability.configure_research_observability()

    instrument_agents.assert_called_once_with()


def test_research_observability_filters_phoenix_bigquery_spans(monkeypatch: pytest.MonkeyPatch) -> None:
    register = Mock()
    phoenix_otel = ModuleType("phoenix.otel")
    setattr(phoenix_otel, "register", register)
    monkeypatch.setitem(sys.modules, "phoenix.otel", phoenix_otel)
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006")
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setattr(research_observability, "instrument_agents", Mock())
    monkeypatch.setattr(research_observability, "_configured", False)

    research_observability.configure_research_observability()

    sampler = register.call_args.kwargs["sampler"]
    result = sampler.should_sample(None, 1, "BigQuery.query", attributes={"db.system": "BigQuery"})
    assert result.decision is Decision.DROP


def test_research_observability_blocks_bigquery_scope_in_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Mock()
    client.auth_check.return_value = True
    langfuse = Mock(return_value=client)
    langfuse_module = ModuleType("langfuse")
    setattr(langfuse_module, "Langfuse", langfuse)
    monkeypatch.setitem(sys.modules, "langfuse", langfuse_module)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3000")
    monkeypatch.setattr(research_observability, "instrument_agents", Mock())
    monkeypatch.setattr(research_observability, "_configured", False)

    research_observability.configure_research_observability()

    langfuse.assert_called_once_with(blocked_instrumentation_scopes=["google.cloud.bigquery.opentelemetry_tracing"])
