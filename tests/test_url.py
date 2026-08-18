"""Unit tests for database connection URL helpers."""

import pytest

from tabulaflow.data.url import (
    is_database_file_path,
    normalize_connection_url,
    strip_url_credentials,
    url_has_username_without_password,
)


class TestNormalizeConnectionUrl:
    def test_db_file_path_to_url(self) -> None:
        assert normalize_connection_url("/data/x.sqlite") == "sqlite+aiosqlite:////data/x.sqlite"
        assert normalize_connection_url("/data/x.duckdb") == "duckdb:////data/x.duckdb"
        assert normalize_connection_url("/data/X.SQLITE") == "sqlite+aiosqlite:////data/X.SQLITE"

    def test_sync_driver_upgraded_to_async(self) -> None:
        assert normalize_connection_url("postgresql://h/db") == "postgresql+asyncpg://h/db"
        assert normalize_connection_url("mysql://h/db") == "mysql+asyncmy://h/db"

    def test_already_async_or_other_unchanged(self) -> None:
        assert normalize_connection_url("postgresql+asyncpg://h/db") == "postgresql+asyncpg://h/db"
        assert normalize_connection_url("bigquery://proj/ds") == "bigquery://proj/ds"
        assert normalize_connection_url("neo4j://h:7687") == "neo4j://h:7687"

    @pytest.mark.parametrize(
        "raw",
        ["/data/x.sqlite", "/data/x.duckdb", "postgresql://h/db", "bigquery://proj/ds", "neo4j://h:7687"],
    )
    def test_idempotent(self, raw: str) -> None:
        # A normalized URL must survive a second pass unchanged — a db-file URL still
        # ends in ".sqlite", so the path branch must not re-fire on it.
        once = normalize_connection_url(raw)
        assert normalize_connection_url(once) == once


class TestUrlHasUsernameWithoutPassword:
    def test_username_without_password(self) -> None:
        assert url_has_username_without_password("postgresql://alice@host:5432/db") is True

    def test_username_with_password(self) -> None:
        assert url_has_username_without_password("postgresql://alice:secret@host/db") is False

    def test_no_username(self) -> None:
        assert url_has_username_without_password("postgresql://host/db") is False
        assert url_has_username_without_password("sqlite+aiosqlite:////data/x.sqlite") is False


class TestStripUrlCredentials:
    def test_strips_username_and_password(self) -> None:
        assert strip_url_credentials("postgresql://alice:secret@example.com:5432/app") == (
            "postgresql://example.com:5432/app"
        )

    def test_preserves_url_without_credentials(self) -> None:
        assert strip_url_credentials("duckdb:////data/x.duckdb") == "duckdb:////data/x.duckdb"


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

        assert _neo4j_global_id(driver_url_a, database_a) == _neo4j_global_id(driver_url_b, database_b)
        assert _neo4j_global_id(driver_url_a, database_a) == "cli+neo4j_s___demo_neo4jlabs_com_database_companies"
