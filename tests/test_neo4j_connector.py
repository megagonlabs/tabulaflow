from pathlib import Path
from typing import Any

import neo4j
import pandas as pd
import pytest

from tabulaflow.data import Neo4jConnector, Neo4jConnectorConfig
from tabulaflow.data.neo4j import (
    _FAST_NODE_PROPERTIES_QUERY,
    _FAST_RELATIONSHIP_PROPERTIES_QUERY,
    _FAST_RELATIONSHIP_TOPOLOGY_QUERY,
    _FULL_SCAN_NODE_PROPERTIES_QUERY,
    _FULL_SCAN_RELATIONSHIPS_QUERY,
    _NODE_LABELS_QUERY,
    _RELATIONSHIP_TYPES_QUERY,
)


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


async def test_fast_schema_introspection_uses_metadata() -> None:
    responses: dict[str, list[dict[str, Any]]] = {
        _NODE_LABELS_QUERY: [{"label": "Person"}, {"label": "Movie"}],
        _RELATIONSHIP_TYPES_QUERY: [{"relationshipType": "ACTED_IN"}],
        _FAST_NODE_PROPERTIES_QUERY: [
            {"nodeType": ":`Person`", "propertyName": "id", "propertyTypes": ["STRING"]},
            {"nodeType": ":`Person`", "propertyName": "id", "propertyTypes": ["INTEGER"]},
        ],
        _FAST_RELATIONSHIP_PROPERTIES_QUERY: [
            {
                "source": None,
                "relType": ":`ACTED_IN`",
                "target": None,
                "propertyName": "role",
                "propertyTypes": ["STRING"],
            }
        ],
        _FAST_RELATIONSHIP_TOPOLOGY_QUERY: [
            {
                "source": "Person",
                "relType": "ACTED_IN",
                "target": "Movie",
                "propertyName": None,
                "propertyTypes": [],
            }
        ],
    }
    timeouts: list[int | None] = []
    connector = object.__new__(Neo4jConnector)
    connector.config = Neo4jConnectorConfig(query_timeout_seconds=9, schema_introspection_mode="fast")
    connector._schema_name = "movies"

    async def run_cypher(query: str, *, timeout: int | None = None) -> list[dict[str, Any]]:
        timeouts.append(timeout)
        return responses[query]

    connector._run_cypher = run_cypher  # type: ignore[assignment]
    schema = await connector._build_schema()

    person = next(node for node in schema.nodes if node.label == "Person")
    acted_in = schema.relationships[0]
    assert person.properties[0].types == ["INTEGER", "STRING"]
    assert acted_in.properties[0].types == ["STRING"]
    assert [(e.source_label, e.target_label) for e in acted_in.endpoints] == [("Person", "Movie")]
    assert timeouts == [9, 9, 9, 9, 9]


async def test_full_scan_schema_introspection_uses_observed_properties_and_topology() -> None:
    responses: dict[str, list[dict[str, Any]]] = {
        _NODE_LABELS_QUERY: [{"label": "Person"}, {"label": "Movie"}],
        _RELATIONSHIP_TYPES_QUERY: [{"relationshipType": "ACTED_IN"}],
        _FULL_SCAN_NODE_PROPERTIES_QUERY: [
            {"nodeType": "Person", "propertyName": "id", "propertyTypes": ["INTEGER", "STRING"]}
        ],
        _FULL_SCAN_RELATIONSHIPS_QUERY: [
            {
                "source": "Person",
                "relType": "ACTED_IN",
                "target": "Movie",
                "propertyName": "role",
                "propertyTypes": ["STRING"],
            },
            {
                "source": "Person",
                "relType": "ACTED_IN",
                "target": "Movie",
                "propertyName": None,
                "propertyTypes": [],
            },
        ],
    }
    connector = object.__new__(Neo4jConnector)
    connector.config = Neo4jConnectorConfig(schema_introspection_mode="full_scan")
    connector._schema_name = "movies"

    async def run_cypher(query: str, *, timeout: int | None = None) -> list[dict[str, Any]]:
        return responses[query]

    connector._run_cypher = run_cypher  # type: ignore[assignment]
    schema = await connector._build_schema()

    person = next(node for node in schema.nodes if node.label == "Person")
    acted_in = schema.relationships[0]
    assert person.properties[0].types == ["INTEGER", "STRING"]
    assert acted_in.properties[0].types == ["STRING"]
    assert [(e.source_label, e.target_label) for e in acted_in.endpoints] == [("Person", "Movie")]


def test_schema_cache_is_scoped_by_introspection_mode(tmp_path: Path) -> None:
    connector = object.__new__(Neo4jConnector)
    connector.global_id = "neo4j+movies"
    connector.config = Neo4jConnectorConfig(cache_dir=tmp_path, schema_introspection_mode="fast")
    fast_path = connector._schema_cache_path()
    connector.config = Neo4jConnectorConfig(cache_dir=tmp_path, schema_introspection_mode="full_scan")

    assert fast_path != connector._schema_cache_path()
