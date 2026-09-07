"""Unit tests for database connection URL helpers."""

import pytest

from tabulaflow.data.url import (
    is_database_file_path,
    normalize_connection_url,
    strip_url_credentials,
)


class TestNormalizeConnectionUrl:
    def test_db_file_path_to_url(self) -> None:
        assert normalize_connection_url("/data/x.sqlite") == "sqlite+aiosqlite:////data/x.sqlite"
        assert normalize_connection_url("/data/x.duckdb") == "duckdb:////data/x.duckdb"
        assert normalize_connection_url("/data/X.SQLITE") == "sqlite+aiosqlite:////data/X.SQLITE"

    def test_sync_driver_upgraded_to_async(self) -> None:
        assert normalize_connection_url("postgresql://h/db") == "postgresql+asyncpg://h/db"
        assert normalize_connection_url("mysql://h/db") == "mysql+asyncmy://h/db"

    def test_scheme_normalization_is_case_insensitive(self) -> None:
        assert normalize_connection_url("POSTGRESQL://h/db") == "postgresql+asyncpg://h/db"

    def test_already_async_or_other_unchanged(self) -> None:
        assert normalize_connection_url("postgresql+asyncpg://h/db") == "postgresql+asyncpg://h/db"
        assert normalize_connection_url("bigquery://proj/ds") == "bigquery://proj/ds"
        assert normalize_connection_url("neo4j://h:7687") == "neo4j://h:7687"
        assert normalize_connection_url("sparql+https://example.org/query") == "sparql+https://example.org/query"

    @pytest.mark.parametrize(
        "raw",
        ["/data/x.sqlite", "/data/x.duckdb", "postgresql://h/db", "bigquery://proj/ds", "neo4j://h:7687"],
    )
    def test_idempotent(self, raw: str) -> None:
        # A normalized URL must survive a second pass unchanged — a db-file URL still
        # ends in ".sqlite", so the path branch must not re-fire on it.
        once = normalize_connection_url(raw)
        assert normalize_connection_url(once) == once


class TestStripUrlCredentials:
    def test_strips_username_and_password(self) -> None:
        assert strip_url_credentials("postgresql://alice:secret@example.com:5432/app") == (
            "postgresql://example.com:5432/app"
        )

    def test_preserves_url_without_credentials(self) -> None:
        assert strip_url_credentials("duckdb:////data/x.duckdb") == "duckdb:////data/x.duckdb"


class TestSplitUrlCredentials:
    def test_extracts_decoded_credentials(self) -> None:
        from tabulaflow.data.url import _global_id_from_url, _sparql_endpoint_params, _split_url_credentials

        source = "sparql+https://user%40example:p%40ss@example.org/query"
        other_source = "sparql+https://other:password@example.org/query"
        url, auth = _split_url_credentials(source)

        assert url == "sparql+https://example.org/query"
        assert auth == ("user@example", "p@ss")
        assert _sparql_endpoint_params(url)[0] == "https://example.org/query"
        assert _global_id_from_url(source) == _global_id_from_url(other_source)


def test_is_database_file_path_recognizes_common_extensions() -> None:
    assert is_database_file_path("data.sqlite")
    assert is_database_file_path("data.DUCKDB")
    assert not is_database_file_path("data.csv")


class TestNeo4jDriverParams:
    """Neo4j creds come from the URL (the driver takes them separately, not in the URI)."""

    def test_credentials_extracted_and_stripped(self) -> None:
        from tabulaflow.data.url import _neo4j_driver_params

        driver_url, database, auth = _neo4j_driver_params("neo4j://neo4j:cypherbench@localhost:7687")
        assert driver_url == "neo4j://localhost:7687"
        assert auth == ("neo4j", "cypherbench")
        assert database is None

    def test_database_query_param_extracted(self) -> None:
        from tabulaflow.data.url import _neo4j_driver_params

        driver_url, database, auth = _neo4j_driver_params("bolt://host:7687?database=graph")
        assert driver_url == "bolt://host:7687"
        assert database == "graph"
        assert auth is None

    def test_ipv6_host_is_preserved(self) -> None:
        from tabulaflow.data.url import _neo4j_driver_params

        driver_url, _, _ = _neo4j_driver_params("neo4j://[::1]:7687")
        assert driver_url == "neo4j://[::1]:7687"

    def test_percent_encoded_credentials_are_decoded(self) -> None:
        from tabulaflow.data.url import _neo4j_driver_params

        _, _, auth = _neo4j_driver_params("neo4j://user%40example:p%40ss@host:7687")
        assert auth == ("user@example", "p@ss")

    def test_no_credentials(self) -> None:
        from tabulaflow.data.url import _neo4j_driver_params

        driver_url, database, auth = _neo4j_driver_params("neo4j://localhost:7687")
        assert driver_url == "neo4j://localhost:7687"
        assert auth is None


class TestNeo4jGlobalId:
    def test_db_and_database_params_share_cache_key(self) -> None:
        from tabulaflow.data.url import _neo4j_driver_params, _neo4j_global_id

        driver_url_a, database_a, _ = _neo4j_driver_params("neo4j+s://u:p@demo.neo4jlabs.com?db=companies")
        driver_url_b, database_b, _ = _neo4j_driver_params(
            "neo4j+s://other:secret@demo.neo4jlabs.com?database=companies"
        )

        global_id = _neo4j_global_id(driver_url_a, database_a)
        assert global_id == _neo4j_global_id(driver_url_b, database_b)
        assert global_id.startswith("url+")
        assert "demo.neo4jlabs.com" not in global_id

    def test_distinct_urls_do_not_collapse_to_same_id(self) -> None:
        from tabulaflow.data.url import _global_id_from_url

        assert _global_id_from_url("postgresql://host-a/db") != _global_id_from_url("postgresql://host_a/db")

    def test_query_order_does_not_change_id(self) -> None:
        from tabulaflow.data.url import _global_id_from_url

        assert _global_id_from_url("postgresql://host/db?a=1&b=2") == _global_id_from_url(
            "postgresql://host/db?b=2&a=1"
        )


async def test_connect_url_rejects_unsupported_bare_source() -> None:
    from tabulaflow.data.url import connect_url

    with pytest.raises(ValueError, match="expected a connector URL or SQLite/DuckDB file path"):
        await connect_url("not-a-database", display_name="test")


async def test_connect_url_rejects_ambiguous_http_url() -> None:
    from tabulaflow.data.url import connect_url

    with pytest.raises(ValueError, match=r"use sparql\+http"):
        await connect_url("https://example.org/query", display_name="test")


async def test_connect_url_rejects_unsupported_sparql_transport() -> None:
    from tabulaflow.data.url import connect_url

    with pytest.raises(ValueError, match=r"must use sparql\+http"):
        await connect_url("sparql+ftp://example.org/query", display_name="test")


async def test_connect_url_dispatches_explicit_sparql_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from tabulaflow.data import SPARQLConnector, SPARQLConnectorConfig
    from tabulaflow.data.url import connect_url

    captured: dict[str, object] = {}
    sentinel = object()

    async def connect(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(SPARQLConnector, "from_url_async", connect)
    config = SPARQLConnectorConfig(max_response_bytes=1024)

    result = await connect_url(
        "sparql+https://alice:p%40ss@example.org/query?default-graph-uri=urn%3Agraph",
        display_name="example",
        global_id="example-sparql",
        config=config,
    )

    assert result is sentinel
    assert captured == {
        "url": "https://example.org/query?default-graph-uri=urn%3Agraph",
        "display_name": "example",
        "global_id": "example-sparql",
        "read_only": True,
        "auth": ("alice", "p@ss"),
        "config": config,
    }


async def test_connect_url_rejects_wrong_config_for_sparql() -> None:
    from tabulaflow.data import SQLConnectorConfig
    from tabulaflow.data.url import connect_url

    with pytest.raises(TypeError, match="SPARQLConnectorConfig"):
        await connect_url(
            "sparql+https://example.org/query",
            display_name="example",
            config=SQLConnectorConfig(),
        )


async def test_connect_url_leaves_bigquery_configuration_to_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    from tabulaflow.data.sql import SQLConnector
    from tabulaflow.data.url import connect_url

    captured: dict[str, object] = {}

    async def connect(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCP_BILLING_PROJECT", raising=False)
    monkeypatch.setattr(SQLConnector, "from_url_async", connect)

    await connect_url("bigquery://project/dataset", display_name="dataset")

    assert "billing_project_id" not in captured
    assert "credentials_path" not in captured
