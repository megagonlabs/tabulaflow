import asyncio
import logging
import numbers
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar, Literal

import neo4j
import pandas as pd
from neo4j.graph import Graph, Node
from pydantic import ValidationError

from tabulaflow.data.config import Neo4jConnectorConfig
from tabulaflow.core.results import ErrorInfo, ExecResult, GraphResult, GraphResultEdge, GraphResultNode
from tabulaflow.core.schema import (
    GraphPropertySchema,
    NodeSchema,
    GraphQueryLanguage,
    PropertyGraphSchema,
    RelationshipEndpoint,
    RelationshipSchema,
)
from tabulaflow.core.serialization import json_ready
from tabulaflow.data.protocols import ResultTooLargeError, validate_global_id
from tabulaflow.data.connect import _neo4j_global_id
from tabulaflow.data._cache import (
    cache_lock,
    read_cached_model,
    remove_cached_file,
    schema_cache_path,
    write_cached_model,
)

logger = logging.getLogger(__name__)
_UNSET = object()

_NODE_LABELS_QUERY = """
CALL db.labels()
YIELD label
RETURN label
""".strip()

_RELATIONSHIP_TYPES_QUERY = """
CALL db.relationshipTypes()
YIELD relationshipType
RETURN relationshipType
""".strip()

_FAST_NODE_PROPERTIES_QUERY = """
CALL db.schema.nodeTypeProperties()
YIELD nodeType, propertyName, propertyTypes
RETURN nodeType, propertyName, propertyTypes
""".strip()

_FAST_RELATIONSHIP_PROPERTIES_QUERY = """
CALL db.schema.relTypeProperties()
YIELD relType, propertyName, propertyTypes
RETURN null AS source, relType, null AS target, propertyName, propertyTypes
""".strip()

_FAST_RELATIONSHIP_TOPOLOGY_QUERY = """
CALL db.schema.visualization()
YIELD relationships
UNWIND relationships AS r
UNWIND labels(startNode(r)) AS source
UNWIND labels(endNode(r)) AS target
RETURN source, type(r) AS relType, target,
       null AS propertyName, [] AS propertyTypes
""".strip()

_FULL_SCAN_NODE_PROPERTIES_QUERY = """
MATCH (n)
UNWIND labels(n) AS label
UNWIND keys(n) AS propertyName
RETURN label AS nodeType, propertyName,
       collect(DISTINCT valueType(n[propertyName])) AS propertyTypes
ORDER BY nodeType, propertyName
""".strip()

_FULL_SCAN_RELATIONSHIPS_QUERY = """
MATCH (sourceNode)-[r]->(targetNode)
UNWIND labels(sourceNode) AS source
UNWIND labels(targetNode) AS target
UNWIND CASE WHEN size(keys(r)) = 0 THEN [null] ELSE keys(r) END AS propertyName
RETURN source, type(r) AS relType, target, propertyName,
       collect(DISTINCT CASE
           WHEN propertyName IS NULL THEN null
           ELSE valueType(r[propertyName])
       END) AS propertyTypes
ORDER BY relType, source, target, propertyName
""".strip()


def _records_to_df(records: Sequence[neo4j.Record], columns: Sequence[str]) -> pd.DataFrame:
    from neo4j.time import Date, DateTime

    df = pd.DataFrame([record.values() for record in records], columns=columns)
    for column in df.columns:
        values = df[column].dropna()
        if not values.empty and values.map(lambda value: isinstance(value, (Date, DateTime))).all():
            df[column] = df[column].map(lambda value: pd.NaT if value is None else pd.Timestamp(value.to_native()))
    return df


def _safe_scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, bool, numbers.Integral, numbers.Real))


def _graph_property_value(value: object, *, depth: int = 0) -> object:
    if _safe_scalar(value):
        return json_ready(value)
    if depth >= 4:
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _graph_property_value(item, depth=depth + 1) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_graph_property_value(item, depth=depth + 1) for item in value]
    return str(value)


def _neo4j_node_label(node: Node) -> str:
    for key in ("name", "title"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value
    for _, value in node.items():
        if isinstance(value, str) and value.strip():
            return value
    return node.element_id


def _neo4j_node_group(node: Node) -> str:
    labels = sorted(node.labels)
    return ":".join(labels) if labels else "node"


def _convert_neo4j_graph_result(
    graph: Graph,
    *,
    max_nodes: int | None,
    max_edges: int | None,
) -> GraphResult | None:
    """Convert a complete driver graph when it fits the configured limits."""
    if not graph.nodes:
        return None
    if max_nodes is not None and len(graph.nodes) > max_nodes:
        return None
    if max_edges is not None and len(graph.relationships) > max_edges:
        return None

    nodes = [
        GraphResultNode(
            id=node.element_id,
            label=_neo4j_node_label(node),
            group=_neo4j_node_group(node),
            properties={str(key): _graph_property_value(value) for key, value in node.items()},
        )
        for node in graph.nodes
    ]
    edges = []
    for relationship in graph.relationships:
        start_node = relationship.start_node
        end_node = relationship.end_node
        if start_node is None or end_node is None:
            raise ValueError(f"Neo4j relationship {relationship.element_id!r} has no endpoints")
        edges.append(
            GraphResultEdge(
                id=relationship.element_id,
                source=start_node.element_id,
                target=end_node.element_id,
                label=relationship.type,
                directed=True,
                properties={str(key): _graph_property_value(value) for key, value in relationship.items()},
            )
        )
    return GraphResult(
        nodes=sorted(nodes, key=lambda node: node.id),
        edges=sorted(edges, key=lambda edge: (edge.source, edge.target, edge.label or "")),
    )


def _parse_type_labels(raw: str) -> list[str]:
    """Parse nodeType/relType from ``db.schema`` procedures into individual labels.

    Handles compound multi-label types like ``":`Resource`:`Noun`"`` by splitting
    on the backtick-colon separator and returning each label individually.
    """
    parts = raw.strip().split(":`")
    return [p.strip().lstrip(":").strip("`").strip() for p in parts if p.strip().strip(":`")]


def _preserve_graph_descriptions(previous: PropertyGraphSchema, refreshed: PropertyGraphSchema) -> None:
    refreshed.description = refreshed.description or previous.description

    previous_nodes = {node.label: node for node in previous.nodes}
    for node in refreshed.nodes:
        previous_node = previous_nodes.get(node.label)
        if previous_node is None:
            continue
        node.description = node.description or previous_node.description
        previous_properties = {prop.name: prop for prop in previous_node.properties}
        for prop in node.properties:
            previous_property = previous_properties.get(prop.name)
            if previous_property is not None:
                prop.description = prop.description or previous_property.description

    previous_relationships = {relationship.label: relationship for relationship in previous.relationships}
    for relationship in refreshed.relationships:
        previous_relationship = previous_relationships.get(relationship.label)
        if previous_relationship is None:
            continue
        relationship.description = relationship.description or previous_relationship.description
        previous_properties = {prop.name: prop for prop in previous_relationship.properties}
        for prop in relationship.properties:
            previous_property = previous_properties.get(prop.name)
            if previous_property is not None:
                prop.description = prop.description or previous_property.description


class Neo4jConnector:
    """Property-graph connector for Neo4j databases.

    Uses the official ``neo4j`` async Python driver (Bolt protocol).
    Fast schema introspection uses Neo4j metadata procedures; full-scan mode
    exhaustively derives observed properties and topology from graph data.

    Attributes:
        global_id: Stable, filename-safe identity used by caches.
        schema: Current introspected property-graph schema.
        backend: Graph database backend name (``neo4j``).
        language: Graph query language (``cypher``).
        config: Resolved immutable connector configuration.
        read_only: Whether sessions use server-enforced read access.
    """

    backend: ClassVar[Literal["neo4j"]] = "neo4j"
    language: ClassVar[GraphQueryLanguage] = "cypher"

    def __init__(
        self,
        global_id: str,
        schema: PropertyGraphSchema,
        _driver: neo4j.AsyncDriver,
        *,
        _database: str | None,
        _display_name: str,
        config: Neo4jConnectorConfig,
        read_only: bool,
    ) -> None:
        self.global_id = global_id
        self.schema = schema
        self._driver = _driver
        self._database = _database
        self._display_name = _display_name
        self.config = config
        self.read_only = read_only
        self._schema_lock = asyncio.Lock()
        self._query_semaphore = asyncio.Semaphore(config.max_query_concurrency)
        self._closed = False

    @staticmethod
    async def _fetch_default_db_name(driver: neo4j.AsyncDriver) -> str | None:
        """Try to get the default database name from the server (Neo4j 4.x+).

        Returns ``None`` on older servers that don't support ``SHOW DEFAULT DATABASE``.
        """
        try:
            async with driver.session(database="system", default_access_mode=neo4j.READ_ACCESS) as session:
                result = await session.run("SHOW DEFAULT DATABASE")
                record = await result.single()
                if record:
                    return str(record["name"])
        except Exception:
            pass
        return None

    @classmethod
    async def from_url_async(
        cls,
        url: str,
        *,
        global_id: str | None = None,
        auth: tuple[str, str] | neo4j.Auth | None = None,
        database: str | None = None,
        display_name: str | None = None,
        schema: PropertyGraphSchema | None = None,
        read_only: bool = True,
        config: Neo4jConnectorConfig | None = None,
        **driver_kwargs: Any,
    ) -> "Neo4jConnector":
        """Create a connector from a Neo4j Bolt URL.

        Args:
            url: Neo4j URL (e.g. ``"neo4j://localhost:7687"``,
                ``"bolt://localhost:7687"``, ``"neo4j+s://host"``).
            global_id: Globally unique, filename-safe identifier for this
                database connection and its caches. Derived from the
                credential-free URL and database when omitted.
            auth: ``(username, password)`` tuple or ``neo4j.Auth`` object.
            database: Neo4j database name.  ``None`` uses the server default.
            display_name: Human-readable name used in
                ``schema.display_name``.
                Auto-detected from the server if not provided.
            schema: Pre-loaded schema.  If ``None``, the schema is
                introspected automatically.
            read_only: Use Neo4j's server-enforced read access mode when
                ``True``.
            config: Immutable connector execution and cache policy. Environment
                values and built-in defaults are used when omitted.
            **driver_kwargs: Extra keyword arguments for
                ``neo4j.AsyncGraphDatabase.driver``.
        """
        global_id = validate_global_id(global_id or _neo4j_global_id(url, database))
        config = Neo4jConnectorConfig() if config is None else config
        if "max_connection_pool_size" in driver_kwargs:
            raise TypeError("Configure Neo4j query concurrency through Neo4jConnectorConfig.max_query_concurrency")
        driver = neo4j.AsyncGraphDatabase.driver(
            url,
            auth=auth,
            max_connection_pool_size=config.max_query_concurrency,
            **driver_kwargs,
        )
        try:
            await driver.verify_connectivity()

            resolved_display_name = (
                display_name
                or (schema.display_name if schema is not None else None)
                or database
                or await cls._fetch_default_db_name(driver)
                or "N/A"
            )
            if schema is not None:
                schema.display_name = resolved_display_name

            connector = cls(
                global_id=global_id,
                schema=schema or PropertyGraphSchema(display_name=resolved_display_name),
                _driver=driver,
                _database=database,
                _display_name=resolved_display_name,
                config=config,
                read_only=read_only,
            )

            if schema is None:
                await connector._load_schema_async()

            return connector
        except BaseException:
            try:
                await driver.close()
            except Exception:
                logger.debug("Neo4j driver close during construction failed", exc_info=True)
            raise

    async def _run_cypher(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        *,
        return_df: bool = False,
        max_rows: int | None = None,
    ) -> list[dict[str, Any]] | tuple[pd.DataFrame, Graph]:
        self._check_open()
        access_mode = neo4j.READ_ACCESS if self.read_only else neo4j.WRITE_ACCESS
        async with self._query_semaphore:
            async with self._driver.session(database=self._database, default_access_mode=access_mode) as session:
                result = await session.run(
                    neo4j.Query(query, timeout=timeout),
                    parameters=dict(parameters) if parameters else {},
                )
                if return_df:
                    if max_rows is None:
                        df = await result.to_df(expand=False, parse_dates=True)
                    else:
                        records = await result.fetch(max_rows + 1)
                        if len(records) > max_rows:
                            raise ResultTooLargeError(max_rows)
                        df = _records_to_df(records, result.keys())
                    return df, await result.graph()
                return await result.data()

    async def run_query_async(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: int | None | object = _UNSET,
    ) -> ExecResult:
        """Execute Cypher and return tabular data with an optional graph.

        Query failures are returned in ``ExecResult.error``. Omitting
        ``timeout`` uses the connector configuration; ``None`` disables it.
        Task cancellation propagates.
        """
        self._check_open()
        effective_timeout = self.config.query_timeout_seconds if timeout is _UNSET else timeout
        assert isinstance(effective_timeout, int) or effective_timeout is None
        query_str = query.strip()

        t0 = time.time()
        try:
            tabular_result = await self._run_cypher(
                query_str,
                parameters,
                effective_timeout,
                return_df=True,
                max_rows=self.config.max_result_rows,
            )
            assert isinstance(tabular_result, tuple)
            df, neo4j_graph = tabular_result
            graph = _convert_neo4j_graph_result(
                neo4j_graph,
                max_nodes=self.config.max_graph_result_nodes,
                max_edges=self.config.max_graph_result_edges,
            )
            latency = time.time() - t0
            return ExecResult(df=df, graph=graph, latency_seconds=latency)
        except Exception as e:
            return ExecResult(
                error=ErrorInfo(exc_type=type(e).__name__, message=str(e)),
                latency_seconds=time.time() - t0,
            )

    async def close_async(self) -> None:
        """Close the Neo4j driver and all pooled connections."""
        if self._closed:
            return
        await self._driver.close()
        self._closed = True

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError("Neo4jConnector is closed")

    def _schema_cache_path(self) -> Path:
        return schema_cache_path(
            self.config.cache_dir,
            self.global_id,
            variant=self.config.schema_introspection_mode,
        )

    async def _load_schema_async(self) -> PropertyGraphSchema:
        """Load schema from cache or introspect, respecting cache config."""
        cache_path = self._schema_cache_path()
        async with cache_lock(cache_path):
            if self.config.schema_cache_mode in ("read_write", "cache_only") and cache_path.exists():
                try:
                    self.schema = await read_cached_model(cache_path, PropertyGraphSchema)
                    self.schema.display_name = self._display_name
                    return self.schema
                except (ValidationError, UnicodeError) as e:
                    if self.config.schema_cache_mode == "cache_only":
                        raise RuntimeError(f"Required schema cache is invalid: {cache_path}") from e
                    logger.warning("Removing invalid schema cache entry: %s", cache_path)
                    await remove_cached_file(cache_path)

            if self.config.schema_cache_mode == "cache_only":
                raise FileNotFoundError(f"Schema cache required but not found at {cache_path}")

            self.schema = await self._build_schema()

            if self.config.schema_cache_mode in ("read_write", "refresh"):
                await write_cached_model(cache_path, self.schema)

            return self.schema

    async def refresh_schema_async(self) -> PropertyGraphSchema:
        """Re-introspect the live database, bypassing cache on read."""
        self._check_open()
        async with self._schema_lock:
            cache_path = self._schema_cache_path()
            async with cache_lock(cache_path):
                refreshed = await self._build_schema()
                _preserve_graph_descriptions(self.schema, refreshed)
                self.schema = refreshed

                if self.config.schema_cache_mode in ("read_write", "refresh"):
                    await write_cached_model(cache_path, self.schema)

                return self.schema

    async def _build_schema(self) -> PropertyGraphSchema:
        timeout = self.config.query_timeout_seconds

        async def query(cypher: str) -> list[dict[str, Any]]:
            result = await self._run_cypher(cypher, timeout=timeout)
            assert isinstance(result, list)
            return result

        node_labels: set[str] = set()
        relationship_types: set[str] = set()
        node_properties: dict[str, dict[str, set[str]]] = {}
        relationship_properties: dict[str, dict[str, set[str]]] = {}
        relationship_endpoints: dict[str, set[tuple[str, str]]] = {}

        def add_property(
            properties: dict[str, dict[str, set[str]]],
            owner: str,
            name: str,
            types: Sequence[str],
        ) -> None:
            properties.setdefault(owner, {}).setdefault(name, set()).update(types or ["UNKNOWN"])

        for record in await query(_NODE_LABELS_QUERY):
            node_labels.add(str(record["label"]))
        for record in await query(_RELATIONSHIP_TYPES_QUERY):
            relationship_types.add(str(record["relationshipType"]))

        if self.config.schema_introspection_mode == "fast":
            node_properties_query = _FAST_NODE_PROPERTIES_QUERY
            relationship_queries: tuple[str, ...] = (
                _FAST_RELATIONSHIP_PROPERTIES_QUERY,
                _FAST_RELATIONSHIP_TOPOLOGY_QUERY,
            )
        else:
            node_properties_query = _FULL_SCAN_NODE_PROPERTIES_QUERY
            relationship_queries = (_FULL_SCAN_RELATIONSHIPS_QUERY,)

        try:
            node_property_records = await query(node_properties_query)
            relationship_records = []
            for relationship_query in relationship_queries:
                relationship_records.extend(await query(relationship_query))
        except neo4j.exceptions.ClientError as e:
            if (
                self.config.schema_introspection_mode == "full_scan"
                and "Unknown function" in str(e)
                and "valueType" in str(e)
            ):
                raise RuntimeError(
                    'schema_introspection_mode="full_scan" requires Neo4j with valueType() support'
                ) from e
            raise

        for record in node_property_records:
            if record["propertyName"] is None:
                continue
            for label in _parse_type_labels(record["nodeType"]):
                node_labels.add(label)
                add_property(
                    node_properties,
                    label,
                    str(record["propertyName"]),
                    record["propertyTypes"] or [],
                )

        for record in relationship_records:
            for rel_type in _parse_type_labels(record["relType"]):
                relationship_types.add(rel_type)
                source = record["source"]
                target = record["target"]
                if source is not None and target is not None:
                    source = str(source)
                    target = str(target)
                    node_labels.update((source, target))
                    relationship_endpoints.setdefault(rel_type, set()).add((source, target))
                if record["propertyName"] is not None:
                    add_property(
                        relationship_properties,
                        rel_type,
                        str(record["propertyName"]),
                        record["propertyTypes"] or [],
                    )

        sorted_nodes = [
            NodeSchema(
                label=label,
                properties=[
                    GraphPropertySchema(name=name, types=sorted(types))
                    for name, types in sorted(node_properties.get(label, {}).items())
                ],
            )
            for label in sorted(node_labels)
        ]
        sorted_rels = [
            RelationshipSchema(
                label=rel_type,
                endpoints=[
                    RelationshipEndpoint(source_label=source, target_label=target)
                    for source, target in sorted(relationship_endpoints.get(rel_type, set()))
                ],
                properties=[
                    GraphPropertySchema(name=name, types=sorted(types))
                    for name, types in sorted(relationship_properties.get(rel_type, {}).items())
                ],
            )
            for rel_type in sorted(relationship_types)
        ]

        return PropertyGraphSchema(
            display_name=self._display_name,
            nodes=sorted_nodes,
            relationships=sorted_rels,
        )
