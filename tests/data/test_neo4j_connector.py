import asyncio
from pathlib import Path
from typing import Any

import neo4j
import pytest

from tabulaflow.core import (
    ExecResult,
    GraphPropertySchema,
    NodeSchema,
    PropertyGraphSchema,
    RelationshipEndpoint,
    RelationshipSchema,
)
from tabulaflow.data import Neo4jConnector, Neo4jConnectorConfig
from tabulaflow.data.neo4j import (
    _FAST_NODE_PROPERTIES_QUERY,
    _FAST_RELATIONSHIP_PROPERTIES_QUERY,
    _FAST_RELATIONSHIP_TOPOLOGY_QUERY,
    _FULL_SCAN_NODE_PROPERTIES_QUERY,
    _FULL_SCAN_RELATIONSHIPS_QUERY,
    _NODE_LABELS_QUERY,
    _RELATIONSHIP_TYPES_QUERY,
    _rows_to_df,
)


class _Result:
    async def data(self) -> list[dict[str, int]]:
        return [{"value": 1}]

    def keys(self) -> list[str]:
        return ["value"]

    async def graph(self) -> neo4j.graph.Graph:
        return neo4j.graph.Graph()


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


def test_native_path_is_materialized_as_tabular_data() -> None:
    graph = neo4j.graph.Graph()
    alice = neo4j.graph.Node(graph, "alice", 1, ["Person"], {"name": "Alice"})
    bob = neo4j.graph.Node(graph, "bob", 2, ["Person"], {"name": "Bob"})
    relationship = graph.relationship_type("KNOWS")(graph, "knows", 3, {})
    relationship._start_node = alice
    relationship._end_node = bob
    record = neo4j.Record([("p", neo4j.graph.Path(alice, relationship))])  # type: ignore[no-untyped-call]

    result = ExecResult(df=_rows_to_df([record.data()], record.keys()))

    assert result.df is not None
    assert result.df.at[0, "p"] == [{"name": "Alice"}, "KNOWS", {"name": "Bob"}]


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
    connector._query_semaphore = asyncio.Semaphore(1)
    connector._closed = False

    await connector._run_cypher("MATCH (n) DELETE n", return_df=True)

    assert driver.access_modes == [expected_mode]


async def test_query_concurrency_configures_semaphore_and_driver_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = _Driver()
    captured: dict[str, object] = {}

    def build_driver(*_args: object, **kwargs: object) -> _Driver:
        captured.update(kwargs)
        return driver

    monkeypatch.setattr(neo4j.AsyncGraphDatabase, "driver", build_driver)
    connector = await Neo4jConnector.from_url_async(
        global_id="neo4j+concurrency",
        url="neo4j://localhost:7687",
        display_name="test",
        schema=PropertyGraphSchema(display_name="test"),
        config=Neo4jConnectorConfig(max_query_concurrency=3),
    )
    try:
        assert captured["max_connection_pool_size"] == 3
        assert connector._query_semaphore._value == 3
        assert connector.backend == "neo4j"
        assert connector.language == "cypher"
    finally:
        await connector.close_async()


async def test_close_is_terminal_and_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = _Driver()
    monkeypatch.setattr(neo4j.AsyncGraphDatabase, "driver", lambda *_args, **_kwargs: driver)
    connector = await Neo4jConnector.from_url_async(
        "neo4j://localhost:7687",
        display_name="test",
        schema=PropertyGraphSchema(display_name="test"),
    )
    assert connector.global_id.startswith("url+")

    await connector.close_async()
    await connector.close_async()

    with pytest.raises(RuntimeError, match="Neo4jConnector is closed"):
        await connector.run_query_async("RETURN 1")
    with pytest.raises(RuntimeError, match="Neo4jConnector is closed"):
        await connector.refresh_schema_async()


async def test_driver_pool_size_override_is_rejected() -> None:
    with pytest.raises(TypeError, match="Neo4jConnectorConfig.max_query_concurrency"):
        await Neo4jConnector.from_url_async(
            global_id="neo4j+concurrency",
            url="neo4j://localhost:7687",
            max_connection_pool_size=4,
        )


async def test_query_semaphore_limits_concurrent_cypher_execution() -> None:
    active = 0
    max_active = 0

    class TrackingSession(_Session):
        async def run(self, query: neo4j.Query, parameters: dict[str, Any]) -> _Result:
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1
            return await super().run(query, parameters)

    class TrackingDriver(_Driver):
        def session(self, *, database: str | None, default_access_mode: str) -> _Session:
            self.access_modes.append(default_access_mode)
            return TrackingSession()

    connector = object.__new__(Neo4jConnector)
    connector._driver = TrackingDriver()  # type: ignore[assignment]
    connector._database = None
    connector.read_only = True
    connector._query_semaphore = asyncio.Semaphore(2)
    connector._closed = False

    await asyncio.gather(*(connector._run_cypher("RETURN 1", return_df=True) for _ in range(5)))

    assert max_active == 2


async def test_failed_connectivity_verification_closes_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = _Driver(verification_error=RuntimeError("unavailable"))
    monkeypatch.setattr(neo4j.AsyncGraphDatabase, "driver", lambda *_args, **_kwargs: driver)

    with pytest.raises(RuntimeError, match="unavailable"):
        await Neo4jConnector.from_url_async(
            global_id="neo4j+test",
            url="neo4j://localhost:7687",
            display_name="test",
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
            display_name="test",
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
    connector._display_name = "movies"

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
            {"nodeType": "Person", "propertyName": "id", "propertyTypes": ["STRING", "INTEGER", "STRING"]}
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
    connector._display_name = "movies"

    async def run_cypher(query: str, *, timeout: int | None = None) -> list[dict[str, Any]]:
        return responses[query]

    connector._run_cypher = run_cypher  # type: ignore[assignment]
    schema = await connector._build_schema()

    person = next(node for node in schema.nodes if node.label == "Person")
    acted_in = schema.relationships[0]
    assert [node.label for node in schema.nodes] == ["Movie", "Person"]
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


async def test_schema_refresh_preserves_descriptions_and_replaces_structure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = PropertyGraphSchema(
        display_name="movies",
        description="database description",
        nodes=[
            NodeSchema(
                label="Person",
                description="node description",
                properties=[GraphPropertySchema(name="id", types=["STRING"], description="property description")],
            )
        ],
        relationships=[
            RelationshipSchema(
                label="KNOWS",
                endpoints=[RelationshipEndpoint(source_label="Person", target_label="Person")],
                description="relationship description",
                properties=[GraphPropertySchema(name="since", types=["INTEGER"], description="since description")],
            )
        ],
    )
    refreshed = PropertyGraphSchema(
        display_name="movies",
        nodes=[NodeSchema(label="Person", properties=[GraphPropertySchema(name="id", types=["INTEGER"])])],
        relationships=[
            RelationshipSchema(
                label="KNOWS",
                endpoints=[RelationshipEndpoint(source_label="Person", target_label="Company")],
                properties=[GraphPropertySchema(name="since", types=["FLOAT"])],
            )
        ],
    )
    connector = object.__new__(Neo4jConnector)
    connector.global_id = "neo4j+descriptions"
    connector.schema = previous
    connector.config = Neo4jConnectorConfig(cache_dir=tmp_path, schema_cache_mode="off")
    connector._schema_lock = asyncio.Lock()
    connector._closed = False

    async def build_schema() -> PropertyGraphSchema:
        return refreshed

    monkeypatch.setattr(connector, "_build_schema", build_schema)
    result = await connector.refresh_schema_async()

    assert result.description == "database description"
    assert result.nodes[0].description == "node description"
    assert result.nodes[0].properties[0].description == "property description"
    assert result.nodes[0].properties[0].types == ["INTEGER"]
    assert result.relationships[0].description == "relationship description"
    assert result.relationships[0].properties[0].description == "since description"
    assert result.relationships[0].properties[0].types == ["FLOAT"]
    assert result.relationships[0].endpoints[0].target_label == "Company"
