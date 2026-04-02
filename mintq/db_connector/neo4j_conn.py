import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

import neo4j
import pandas as pd

from mintq.config import mintq_config
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

    connector_type: ClassVar = "property_graph"
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
            latency = time.time() - t0
            return ExecResult(df=df, latency_seconds=latency)
        except Exception as e:
            return ExecResult(
                error=ErrorInfo(exc_type=type(e).__name__, message=str(e)),
                latency_seconds=time.time() - t0,
            )

    async def disconnect_async(self) -> None:
        await self._driver.close()

    def _schema_cache_path(self) -> str:
        cache_dir = os.path.join(mintq_config.cache_dir, "schemas")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{self.global_id}.json")

    async def _load_schema_async(self) -> PropertyGraphSchema:
        """Load schema from cache or introspect, respecting cache config."""
        cache_path = self._schema_cache_path()

        if (
            self.enable_schema_caching
            and mintq_config.schema_cache_enabled
            and not mintq_config.schema_cache_overwrite
            and os.path.exists(cache_path)
        ):
            with open(cache_path, "r", encoding="utf-8") as f:
                self.schema = PropertyGraphSchema.model_validate_json(f.read())
                return self.schema

        if self.enable_schema_caching and mintq_config.schema_cache_required:
            raise FileNotFoundError(f"Schema cache required but not found at {cache_path}")

        self.schema = await self._build_schema()

        if self.enable_schema_caching and mintq_config.schema_cache_enabled:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(self.schema.model_dump_json(indent=2))

        return self.schema

    async def refresh_schema_async(self) -> PropertyGraphSchema:
        """Re-introspect the live database, bypassing cache on read."""
        self.schema = await self._build_schema()

        if self.enable_schema_caching and mintq_config.schema_cache_enabled:
            cache_path = self._schema_cache_path()
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(self.schema.model_dump_json(indent=2))

        return self.schema

    async def _build_schema(self) -> PropertyGraphSchema:
        nodes: dict[str, NodeSchema] = {}
        rels: dict[tuple[str, str, str], RelationshipSchema] = {}

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
            key = (rel_type, source, target)
            if key not in rels:
                rels[key] = RelationshipSchema(label=rel_type, source_label=source, target_label=target)
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
                for key, rel in rels.items():
                    if key[0] == rel_type:
                        rel.properties.append(GraphPropertySchema(name=prop_name, dtype=dtype))

        sorted_nodes = sorted(nodes.values(), key=lambda n: n.label)
        sorted_rels = sorted(rels.values(), key=lambda r: (r.label, r.source_label, r.target_label))

        return PropertyGraphSchema(
            name=self._schema_name,
            nodes=sorted_nodes,
            relationships=sorted_rels,
        )
