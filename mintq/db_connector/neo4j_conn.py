import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Mapping

import neo4j
import pandas as pd

from mintq.schema import (
    ErrorInfo,
    ExecResult,
    GraphPropertySchema,
    NodeSchema,
    NonSQLLanguage,
    PropertyGraphSchema,
    RelationshipSchema,
)

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


def _parse_type_label(raw: str) -> str:
    """Parse nodeType/relType from ``db.schema`` procedures (e.g. ``":`Person`"`` -> ``"Person"``)."""
    return raw.strip().lstrip(":").strip("`").strip()


@dataclass
class Neo4jConnector:
    """Property-graph connector for Neo4j databases.

    Uses the official ``neo4j`` async Python driver (Bolt protocol).
    Schema introspection relies on ``db.schema.nodeTypeProperties()``
    and ``db.schema.relTypeProperties()`` procedures (Neo4j 3.4+).
    """

    global_id: str
    schema: PropertyGraphSchema
    language: NonSQLLanguage
    _driver: neo4j.AsyncDriver
    _database: str
    read_only: bool = True

    @classmethod
    async def from_url_async(
        cls,
        global_id: str,
        db_name: str,
        url: str,
        auth: tuple[str, str] | neo4j.Auth | None = None,
        database: str = "neo4j",
        schema: PropertyGraphSchema | None = None,
        read_only: bool = True,
        **driver_kwargs: Any,
    ) -> "Neo4jConnector":
        """Create a connector from a Neo4j Bolt URL.

        Args:
            global_id: Globally unique identifier for this connection.
            db_name: Human-readable name used in ``schema.name``.
            url: Bolt URL (e.g. ``"bolt://localhost:7687"``).
            auth: ``(username, password)`` tuple or ``neo4j.Auth`` object.
            database: Neo4j database name.  Defaults to ``"neo4j"``.
            schema: Pre-loaded schema.  If ``None``, the schema is
                introspected automatically.
            read_only: Block write statements when ``True``.
            **driver_kwargs: Extra keyword arguments for
                ``neo4j.AsyncGraphDatabase.driver``.
        """
        driver = neo4j.AsyncGraphDatabase.driver(
            url,
            auth=auth,
            **driver_kwargs,
        )
        await driver.verify_connectivity()

        connector = cls(
            global_id=global_id,
            schema=schema or PropertyGraphSchema(name=db_name),
            language="cypher",
            _driver=driver,
            _database=database,
            read_only=read_only,
        )

        if schema is None:
            await connector.refresh_schema_async()

        return connector

    async def _run_cypher(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                neo4j.Query(query, timeout=timeout),
                parameters=dict(parameters) if parameters else {},
            )
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
                    message=(
                        f"Write statement blocked (read_only=True): "
                        f"{match.group('keyword').upper()} ..."
                    ),
                ),
            )

        t0 = time.time()
        try:
            records = await self._run_cypher(query, parameters, timeout)
            latency = time.time() - t0
            df = pd.DataFrame(records) if records else pd.DataFrame()
            return ExecResult(df=df, latency_seconds=latency)
        except Exception as e:
            return ExecResult(
                error=ErrorInfo(exc_type=type(e).__name__, message=str(e)),
                latency_seconds=time.time() - t0,
            )

    async def disconnect_async(self) -> None:
        await self._driver.close()

    async def refresh_schema_async(self) -> PropertyGraphSchema:
        self.schema = await self._build_schema()
        return self.schema

    async def _build_schema(self) -> PropertyGraphSchema:
        nodes: dict[str, NodeSchema] = {}
        rels: dict[tuple[str, str, str], RelationshipSchema] = {}

        for record in await self._run_cypher("CALL db.labels() YIELD label RETURN label"):
            label: str = record["label"]
            if label not in nodes:
                nodes[label] = NodeSchema(label=label)

        for record in await self._run_cypher(_NODE_TYPE_PROPERTIES_QUERY):
            if record["propertyName"] is None:
                continue
            label = _parse_type_label(record["nodeType"])
            prop_name: str = record["propertyName"]
            prop_types: list[str] = record["propertyTypes"] or []
            dtype = prop_types[0] if prop_types else "UNKNOWN"

            if label not in nodes:
                nodes[label] = NodeSchema(label=label)
            nodes[label].properties.append(GraphPropertySchema(name=prop_name, dtype=dtype))

        for record in await self._run_cypher(_REL_PATTERNS_QUERY):
            source: str = record["source"]
            rel_type: str = record["type"]
            target: str = record["target"]
            key = (rel_type, source, target)
            if key not in rels:
                rels[key] = RelationshipSchema(
                    label=rel_type, source_label=source, target_label=target
                )
            for lbl in (source, target):
                if lbl not in nodes:
                    nodes[lbl] = NodeSchema(label=lbl)

        for record in await self._run_cypher(_REL_TYPE_PROPERTIES_QUERY):
            if record["propertyName"] is None:
                continue
            rel_type = _parse_type_label(record["relType"])
            prop_name: str = record["propertyName"]
            prop_types: list[str] = record["propertyTypes"] or []
            dtype = prop_types[0] if prop_types else "UNKNOWN"
            for key, rel in rels.items():
                if key[0] == rel_type:
                    rel.properties.append(GraphPropertySchema(name=prop_name, dtype=dtype))

        sorted_nodes = sorted(nodes.values(), key=lambda n: n.label)
        sorted_rels = sorted(rels.values(), key=lambda r: (r.label, r.source_label, r.target_label))

        return PropertyGraphSchema(
            name=self.schema.name,
            nodes=sorted_nodes,
            relationships=sorted_rels,
        )
