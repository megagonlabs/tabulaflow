import logging
import numbers
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Literal

import neo4j
import pandas as pd

from tabulaflow.config import tabulaflow_config
from tabulaflow.core import (
    ErrorInfo,
    ExecResult,
    GraphPropertySchema,
    GraphResult,
    GraphResultEdge,
    GraphResultNode,
    NodeSchema,
    NonSQLLanguage,
    PropertyGraphSchema,
    RelationshipEndpoint,
    RelationshipSchema,
)
from tabulaflow.core.serialization import json_ready

logger = logging.getLogger(__name__)

_WRITE_STATEMENT_RE = re.compile(
    r"^\s*"
    r"(?://[^\n]*\n\s*)*"
    r"(?P<keyword>"
    r"CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP"
    r")\b",
    re.IGNORECASE | re.DOTALL,
)

_NODE_TYPE_PROPERTIES_QUERY = """
CALL db.schema.nodeTypeProperties()
YIELD nodeType, propertyName, propertyTypes
RETURN nodeType, propertyName, propertyTypes
""".strip()

_REL_TYPE_PROPERTIES_QUERY = """
CALL db.schema.relTypeProperties()
YIELD relType, propertyName, propertyTypes
RETURN relType, propertyName, propertyTypes
""".strip()

_REL_PATTERNS_QUERY = """
MATCH (n)-[r]->(m)
UNWIND labels(n) AS source
UNWIND labels(m) AS target
RETURN DISTINCT source, type(r) AS type, target
ORDER BY type, source, target
""".strip()

_GRAPH_RESULT_MAX_NODES = 300
_GRAPH_RESULT_MAX_EDGES = 700


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


def _neo4j_node_id(node: object) -> str:
    element_id = getattr(node, "element_id", None)
    if element_id is not None:
        return str(element_id)
    return str(getattr(node, "id", node))


def _neo4j_node_label(node: object) -> str:
    for key in ("name", "title"):
        if hasattr(node, "get"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return value
    if hasattr(node, "items"):
        for _, value in node.items():
            if isinstance(value, str) and value.strip():
                return value
    return _neo4j_node_id(node)


def _neo4j_node_group(node: object) -> str:
    labels = sorted(str(label) for label in getattr(node, "labels", []) or [])
    return ":".join(labels) if labels else "node"


def _is_neo4j_node(value: object) -> bool:
    return (
        hasattr(value, "labels") and hasattr(value, "items") and (hasattr(value, "element_id") or hasattr(value, "id"))
    )


def _relationship_endpoints(rel: object) -> tuple[object, object] | None:
    start = getattr(rel, "start_node", None)
    end = getattr(rel, "end_node", None)
    if start is not None and end is not None:
        return start, end

    rel_nodes = getattr(rel, "nodes", None)
    if rel_nodes is None:
        return None
    try:
        if len(rel_nodes) < 2:
            return None
        start, end = rel_nodes[0], rel_nodes[1]
    except (TypeError, IndexError, KeyError):
        return None
    if start is None or end is None:
        return None
    return start, end


def _is_neo4j_relationship(value: object) -> bool:
    return (
        _relationship_endpoints(value) is not None
        and hasattr(value, "items")
        and (hasattr(value, "type") or hasattr(value, "element_id") or hasattr(value, "id"))
    )


def _is_neo4j_path(value: object) -> bool:
    return hasattr(value, "nodes") and hasattr(value, "relationships")


def _extract_neo4j_graph_result(df: pd.DataFrame) -> GraphResult | None:
    """Extract a generic graph view from Neo4j node/relationship/path cells."""
    nodes: dict[str, GraphResultNode] = {}
    edges: dict[str, GraphResultEdge] = {}

    def add_node(node: object) -> str:
        node_id = _neo4j_node_id(node)
        if node_id in nodes:
            return node_id
        properties: dict[str, object] = {}
        if hasattr(node, "items"):
            for key, value in node.items():
                properties[str(key)] = _graph_property_value(value)
        nodes[node_id] = GraphResultNode(
            id=node_id,
            label=_neo4j_node_label(node),
            group=_neo4j_node_group(node),
            properties=properties,
        )
        return node_id

    def add_relationship(rel: object) -> None:
        endpoints = _relationship_endpoints(rel)
        if endpoints is None:
            return
        start, end = endpoints
        source_id = add_node(start)
        target_id = add_node(end)
        rel_id = getattr(rel, "element_id", None) or getattr(rel, "id", None)
        edge_id = str(rel_id) if rel_id is not None else f"{source_id}->{target_id}:{len(edges) + 1}"
        if edge_id in edges:
            return
        label = getattr(rel, "type", None) or type(rel).__name__
        properties: dict[str, object] = {}
        if hasattr(rel, "items"):
            for key, value in rel.items():
                properties[str(key)] = _graph_property_value(value)
        edges[edge_id] = GraphResultEdge(
            id=edge_id,
            source=source_id,
            target=target_id,
            label=str(label),
            directed=True,
            properties=properties,
        )

    def walk(value: object) -> None:
        if value is None:
            return
        if _is_neo4j_node(value):
            add_node(value)
            return
        if _is_neo4j_relationship(value):
            add_relationship(value)
            return
        if _is_neo4j_path(value):
            for node in getattr(value, "nodes"):
                add_node(node)
            for rel in getattr(value, "relationships"):
                add_relationship(rel)
            return
        if isinstance(value, Mapping):
            for item in value.values():
                walk(item)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                walk(item)

    for _, row in df.iterrows():
        for value in row:
            walk(value)

    if not nodes:
        return None
    if len(nodes) > _GRAPH_RESULT_MAX_NODES or len(edges) > _GRAPH_RESULT_MAX_EDGES:
        return None
    return GraphResult(
        nodes=sorted(nodes.values(), key=lambda node: node.id),
        edges=sorted(
            edges.values(),
            key=lambda edge: (edge.source, edge.target, edge.label or ""),
        ),
    )


def _parse_type_labels(raw: str) -> list[str]:
    """Parse nodeType/relType from ``db.schema`` procedures into individual labels.

    Handles compound multi-label types like ``":`Resource`:`Noun`"`` by splitting
    on the backtick-colon separator and returning each label individually.
    """
    parts = raw.strip().split(":`")
    return [p.strip().lstrip(":").strip("`").strip() for p in parts if p.strip().strip(":`")]


@dataclass
class Neo4jConnector:
    """Property-graph connector for Neo4j databases.

    Uses the official ``neo4j`` async Python driver (Bolt protocol).
    Schema introspection relies on ``db.schema.nodeTypeProperties()``
    and ``db.schema.relTypeProperties()`` procedures (Neo4j 3.4+).
    """

    connector_type: ClassVar[Literal["property_graph"]] = "property_graph"
    backend: ClassVar[Literal["neo4j"]] = "neo4j"
    global_id: str
    schema: PropertyGraphSchema
    language: NonSQLLanguage
    _driver: neo4j.AsyncDriver
    _database: str | None
    _schema_name: str
    read_only: bool = True
    enable_schema_caching: bool = True

    @staticmethod
    async def _fetch_default_db_name(driver: neo4j.AsyncDriver) -> str | None:
        """Try to get the default database name from the server (Neo4j 4.x+).

        Returns ``None`` on older servers that don't support ``SHOW DEFAULT DATABASE``.
        """
        try:
            async with driver.session(database="system") as session:
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
        global_id: str,
        url: str,
        auth: tuple[str, str] | neo4j.Auth | None = None,
        database: str | None = None,
        db_name: str | None = None,
        schema: PropertyGraphSchema | None = None,
        read_only: bool = True,
        enable_schema_caching: bool = True,
        **driver_kwargs: Any,
    ) -> "Neo4jConnector":
        """Create a connector from a Neo4j Bolt URL.

        Args:
            global_id: Globally unique identifier for this connection, also
                used as the cache key when loading the schema.
            url: Neo4j URL (e.g. ``"neo4j://localhost:7687"``,
                ``"bolt://localhost:7687"``, ``"neo4j+s://host"``).
            auth: ``(username, password)`` tuple or ``neo4j.Auth`` object.
            database: Neo4j database name.  ``None`` uses the server default.
            db_name: Human-readable database name used in ``schema.name``.
                Auto-detected from the server if not provided.
            schema: Pre-loaded schema.  If ``None``, the schema is
                introspected automatically.
            read_only: Block write statements when ``True``.
            enable_schema_caching: If ``False``, skip schema cache
                read/write regardless of global config.
            **driver_kwargs: Extra keyword arguments for
                ``neo4j.AsyncGraphDatabase.driver``.
        """
        driver = neo4j.AsyncGraphDatabase.driver(
            url,
            auth=auth,
            **driver_kwargs,
        )
        await driver.verify_connectivity()

        schema_name = db_name or database or await cls._fetch_default_db_name(driver) or "N/A"

        connector = cls(
            global_id=global_id,
            schema=schema or PropertyGraphSchema(name=schema_name),
            language="cypher",
            _driver=driver,
            _database=database,
            _schema_name=schema_name,
            read_only=read_only,
            enable_schema_caching=enable_schema_caching,
        )

        if schema is None:
            await connector._load_schema_async()

        return connector

    async def _run_cypher(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        *,
        return_df: bool = False,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                neo4j.Query(query, timeout=timeout),
                parameters=dict(parameters) if parameters else {},
            )
            if return_df:
                return await result.to_df(expand=False, parse_dates=True)
            return await result.data()

    async def run_query_async(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: int | None = None,
    ) -> ExecResult:
        query_str = query.strip()
        if self.read_only and _WRITE_STATEMENT_RE.match(query_str):
            match = _WRITE_STATEMENT_RE.match(query_str)
            assert match is not None
            return ExecResult(
                error=ErrorInfo(
                    exc_type="ReadOnlyViolationError",
                    message=(f"Write statement blocked (read_only=True): {match.group('keyword').upper()} ..."),
                ),
            )

        t0 = time.time()
        try:
            df = await self._run_cypher(query_str, parameters, timeout, return_df=True)
            graph = _extract_neo4j_graph_result(df)
            latency = time.time() - t0
            return ExecResult(df=df, graph=graph, latency_seconds=latency)
        except Exception as e:
            return ExecResult(
                error=ErrorInfo(exc_type=type(e).__name__, message=str(e)),
                latency_seconds=time.time() - t0,
            )

    async def disconnect_async(self) -> None:
        await self._driver.close()

    def _schema_cache_path(self) -> str:
        cache_dir = os.path.join(tabulaflow_config.cache_dir, "schemas")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{self.global_id}.json")

    async def _load_schema_async(self) -> PropertyGraphSchema:
        """Load schema from cache or introspect, respecting cache config."""
        cache_path = self._schema_cache_path()

        if (
            self.enable_schema_caching
            and tabulaflow_config.schema_cache_enabled
            and not tabulaflow_config.schema_cache_overwrite
            and os.path.exists(cache_path)
        ):
            with open(cache_path, "r", encoding="utf-8") as f:
                self.schema = PropertyGraphSchema.model_validate_json(f.read())
                return self.schema

        if self.enable_schema_caching and tabulaflow_config.schema_cache_required:
            raise FileNotFoundError(f"Schema cache required but not found at {cache_path}")

        self.schema = await self._build_schema()

        if self.enable_schema_caching and tabulaflow_config.schema_cache_enabled:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(self.schema.model_dump_json(indent=2))

        return self.schema

    async def refresh_schema_async(self) -> PropertyGraphSchema:
        """Re-introspect the live database, bypassing cache on read."""
        self.schema = await self._build_schema()

        if self.enable_schema_caching and tabulaflow_config.schema_cache_enabled:
            cache_path = self._schema_cache_path()
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(self.schema.model_dump_json(indent=2))

        return self.schema

    async def _build_schema(self) -> PropertyGraphSchema:
        nodes: dict[str, NodeSchema] = {}
        rels: dict[str, RelationshipSchema] = {}

        for record in await self._run_cypher("CALL db.labels() YIELD label RETURN label"):
            label: str = record["label"]
            if label not in nodes:
                nodes[label] = NodeSchema(label=label)

        node_prop_seen: dict[str, set[str]] = {}
        for record in await self._run_cypher(_NODE_TYPE_PROPERTIES_QUERY):
            if record["propertyName"] is None:
                continue
            labels = _parse_type_labels(record["nodeType"])
            prop_name: str = record["propertyName"]
            prop_types: list[str] = record["propertyTypes"] or []
            dtype = prop_types[0] if prop_types else "UNKNOWN"

            for label in labels:
                if label not in nodes:
                    nodes[label] = NodeSchema(label=label)
                if label not in node_prop_seen:
                    node_prop_seen[label] = set()
                if prop_name not in node_prop_seen[label]:
                    node_prop_seen[label].add(prop_name)
                    nodes[label].properties.append(GraphPropertySchema(name=prop_name, dtype=dtype))

        for record in await self._run_cypher(_REL_PATTERNS_QUERY):
            source: str = record["source"]
            rel_type: str = record["type"]
            target: str = record["target"]
            rel = rels.setdefault(rel_type, RelationshipSchema(label=rel_type))
            endpoint = RelationshipEndpoint(source_label=source, target_label=target)
            if endpoint not in rel.endpoints:
                rel.endpoints.append(endpoint)
            for lbl in (source, target):
                if lbl not in nodes:
                    nodes[lbl] = NodeSchema(label=lbl)

        rel_prop_seen: dict[str, set[str]] = {}
        for record in await self._run_cypher(_REL_TYPE_PROPERTIES_QUERY):
            if record["propertyName"] is None:
                continue
            rel_types = _parse_type_labels(record["relType"])
            prop_name = record["propertyName"]
            prop_types = record["propertyTypes"] or []
            dtype = prop_types[0] if prop_types else "UNKNOWN"
            for rel_type in rel_types:
                if rel_type not in rel_prop_seen:
                    rel_prop_seen[rel_type] = set()
                if prop_name in rel_prop_seen[rel_type]:
                    continue
                rel_prop_seen[rel_type].add(prop_name)
                rel = rels.setdefault(rel_type, RelationshipSchema(label=rel_type))
                rel.properties.append(GraphPropertySchema(name=prop_name, dtype=dtype))

        sorted_nodes = sorted(nodes.values(), key=lambda n: n.label)
        for rel in rels.values():
            rel.endpoints.sort(key=lambda e: (e.source_label, e.target_label))
        sorted_rels = sorted(rels.values(), key=lambda r: r.label)

        return PropertyGraphSchema(
            name=self._schema_name,
            nodes=sorted_nodes,
            relationships=sorted_rels,
        )
