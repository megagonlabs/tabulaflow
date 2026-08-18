from pathlib import Path
from typing import Any

import neo4j
import pandas as pd
import pytest

from tabulaflow.data import Neo4jConnector, Neo4jConnectorConfig


class _Result:
    async def to_df(self, *, expand: bool, parse_dates: bool) -> pd.DataFrame:
        return pd.DataFrame({"value": [1]})


class _Session:
    def __init__(self) -> None:
        self.query: neo4j.Query | None = None

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *_args: object) -> None:
        pass

    async def run(self, query: neo4j.Query, parameters: dict[str, Any]) -> _Result:
        self.query = query
        return _Result()


class _Driver:
    def __init__(self, *, verification_error: Exception | None = None) -> None:
        self.verification_error = verification_error
        self.closed = False
        self.access_modes: list[str] = []

    async def verify_connectivity(self) -> None:
        if self.verification_error is not None:
            raise self.verification_error

    def session(self, *, database: str | None, default_access_mode: str) -> _Session:
        self.access_modes.append(default_access_mode)
        return _Session()

    async def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    ("read_only", "expected_mode"),
    [(True, neo4j.READ_ACCESS), (False, neo4j.WRITE_ACCESS)],
)
async def test_query_session_uses_server_enforced_access_mode(read_only: bool, expected_mode: str) -> None:
    driver = _Driver()
    connector = object.__new__(Neo4jConnector)
    connector._driver = driver  # type: ignore[assignment]
    connector._database = None
    connector.read_only = read_only

    await connector._run_cypher("MATCH (n) DELETE n", return_df=True)

    assert driver.access_modes == [expected_mode]


async def test_failed_connectivity_verification_closes_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = _Driver(verification_error=RuntimeError("unavailable"))
    monkeypatch.setattr(neo4j.AsyncGraphDatabase, "driver", lambda *_args, **_kwargs: driver)

    with pytest.raises(RuntimeError, match="unavailable"):
        await Neo4jConnector.from_url_async(
            global_id="neo4j+test",
            url="neo4j://localhost:7687",
            db_name="test",
        )

    assert driver.closed


async def test_schema_initialization_failure_closes_driver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = _Driver()
    monkeypatch.setattr(neo4j.AsyncGraphDatabase, "driver", lambda *_args, **_kwargs: driver)

    with pytest.raises(FileNotFoundError, match="Schema cache required"):
        await Neo4jConnector.from_url_async(
            global_id="neo4j+test",
            url="neo4j://localhost:7687",
            db_name="test",
            config=Neo4jConnectorConfig(
                cache_dir=tmp_path,
                schema_cache_mode="cache_only",
            ),
        )

    assert driver.closed
