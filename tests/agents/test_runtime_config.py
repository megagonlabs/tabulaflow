from pathlib import Path

import pytest
from pydantic import ValidationError

from tabulaflow.agents import AgentRuntimeConfig
from tabulaflow.data import Neo4jConnectorConfig, SPARQLConnectorConfig, SQLConnectorConfig


def test_sql_config_uses_defaults() -> None:
    config = SQLConnectorConfig()

    assert config.cache_dir == Path.home() / ".tabulaflow" / "cache"
    assert config.max_result_rows == 1_000_000
    assert config.query_timeout_seconds == 300
    assert config.schema_cache_mode == "off"
    assert config.max_query_concurrency == 8
    assert config.sql_column_stats_enabled is False
    assert config.sql_query_cache_mode == "off"


def test_neo4j_config_uses_fast_schema_introspection_by_default() -> None:
    config = Neo4jConnectorConfig()

    assert config.max_query_concurrency == 8
    assert config.graph_schema_introspection_mode == "fast"
    assert config.max_graph_result_nodes == 300
    assert config.max_graph_result_edges == 700


def test_sparql_config_has_bounded_http_defaults() -> None:
    config = SPARQLConnectorConfig()

    assert config.max_result_rows == 1_000_000
    assert config.query_timeout_seconds == 300
    assert config.max_query_concurrency == 8
    assert config.max_sparql_response_bytes == 50 * 1024 * 1024
    assert not hasattr(config, "schema_cache_mode")


def test_sql_config_resolves_explicit_over_environment_over_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TABULAFLOW_MAX_RESULT_ROWS", "250")
    monkeypatch.setenv("TABULAFLOW_SCHEMA_CACHE_MODE", "refresh")

    config = SQLConnectorConfig(max_result_rows=50)

    assert config.max_result_rows == 50
    assert config.schema_cache_mode == "refresh"
    assert config.sql_query_cache_mode == "off"


def test_sql_config_reads_column_stats_flag_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_SQL_COLUMN_STATS_ENABLED", "true")

    assert SQLConnectorConfig().sql_column_stats_enabled is True


def test_connector_configs_read_query_concurrency_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_MAX_QUERY_CONCURRENCY", "3")

    assert SQLConnectorConfig().max_query_concurrency == 3
    assert Neo4jConnectorConfig().max_query_concurrency == 3
    assert SPARQLConnectorConfig().max_query_concurrency == 3


def test_sparql_config_reads_response_limit_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_MAX_SPARQL_RESPONSE_BYTES", "1024")

    assert SPARQLConnectorConfig().max_sparql_response_bytes == 1024


def test_connector_configs_share_process_wide_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_MAX_RESULT_ROWS", "250")
    monkeypatch.setenv("TABULAFLOW_QUERY_TIMEOUT_SECONDS", "120")
    monkeypatch.setenv("TABULAFLOW_GRAPH_SCHEMA_INTROSPECTION_MODE", "full_scan")
    monkeypatch.setenv("TABULAFLOW_MAX_GRAPH_RESULT_NODES", "500")
    monkeypatch.setenv("TABULAFLOW_MAX_GRAPH_RESULT_EDGES", "none")

    assert SQLConnectorConfig().max_result_rows == 250
    assert Neo4jConnectorConfig().max_result_rows == 250
    assert SQLConnectorConfig().query_timeout_seconds == 120
    assert Neo4jConnectorConfig().query_timeout_seconds == 120
    assert SPARQLConnectorConfig().max_result_rows == 250
    assert SPARQLConnectorConfig().query_timeout_seconds == 120
    assert Neo4jConnectorConfig().graph_schema_introspection_mode == "full_scan"
    assert Neo4jConnectorConfig().max_graph_result_nodes == 500
    assert Neo4jConnectorConfig().max_graph_result_edges is None


def test_none_environment_value_disables_positive_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_MAX_LLM_CONCURRENCY", "none")

    assert AgentRuntimeConfig().max_llm_concurrency is None


@pytest.mark.parametrize("value", [0, -1])
def test_non_positive_limits_are_rejected(value: int) -> None:
    with pytest.raises(ValidationError):
        SQLConnectorConfig(max_result_rows=value)


def test_agent_config_merges_explicit_fields_with_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TABULAFLOW_MAX_LLM_CONCURRENCY", "8")

    config = AgentRuntimeConfig(max_llm_requests_per_minute=50)

    assert config.max_llm_requests_per_minute == 50
    assert config.max_llm_concurrency == 8
    assert config.browser_max_tabs == 20


def test_config_is_an_immutable_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_MAX_LLM_CONCURRENCY", "8")
    config = AgentRuntimeConfig()

    monkeypatch.setenv("TABULAFLOW_MAX_LLM_CONCURRENCY", "4")

    assert config.max_llm_concurrency == 8
    with pytest.raises(ValidationError):
        config.max_llm_concurrency = 2


def test_unknown_explicit_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentRuntimeConfig(unknown_setting=True)  # type: ignore[call-arg]


def test_agent_config_includes_preprocessing_cache_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_PREPROCESSING_CACHE_MODE", "cache_only")
    monkeypatch.setenv("TABULAFLOW_CACHE_DIR", "/tmp/tabulaflow-cache")

    config = AgentRuntimeConfig()

    assert config.preprocessing_cache_mode == "cache_only"
    assert config.cache_dir == Path("/tmp/tabulaflow-cache")

    overridden = AgentRuntimeConfig(preprocessing_cache_mode="off")
    assert overridden.preprocessing_cache_mode == "off"


def test_agent_preprocessing_cache_is_off_by_default() -> None:
    assert AgentRuntimeConfig().preprocessing_cache_mode == "off"
