"""Session-level query history with LRU spill to a workspace DuckDB."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from tabulaflow.core.types import GraphView, PredQuery

if TYPE_CHECKING:
    import pandas as pd

    from tabulaflow.core.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)

_QH_SCHEMA = "_query_history"


@dataclass
class QueryRecord:
    """Metadata for a query executed through the registry tool."""

    record_id: str
    connector_type: Literal["sql", "property_graph"]
    db_alias: str
    pred_query: PredQuery


@dataclass
class QueryFamily:
    """A family of query results rendered from one template over dimension choices."""

    family_id: str
    db_alias: str
    connector_type: Literal["sql", "property_graph"]
    dimensions: dict[str, list[str]]
    query_template: str
    record_ids_by_selection: dict[str, str]


@dataclass
class ChartArtifact:
    """A chart drawn from a single query result.

    A standalone artifact whose Vega-Lite ``chart_spec`` renders the DataFrame
    of the ``record_id`` it was created from — see ``toolhub.render_chart``.
    """

    chart_id: str
    record_id: str
    chart_spec: dict[str, Any]


@dataclass
class MapArtifact:
    """A map assembled from one or more query results.

    A standalone artifact (not attached to any single ``QueryRecord``) whose
    normalized ``map_spec`` layers each carry the ``source`` record id they read
    from — see ``toolhub.render_map``.
    """

    map_id: str
    map_spec: dict[str, Any]


@dataclass
class GraphArtifact:
    """A materialized node-link graph assembled from one or more query results."""

    graph_id: str
    graph: GraphView
    layout: Literal["force", "layered", "tree"] = "force"


class QueryHistory:
    """Query history with write-through spill to a workspace DuckDB.

    Every successful result DataFrame is persisted to the workspace
    connector (when set).  The most recent ``max_in_memory`` DFs are also
    kept in RAM; older ones are evicted and transparently reloaded from the
    workspace on access via ``get()``.

    Args:
        max_in_memory: Number of result DataFrames to keep in RAM.
    """

    def __init__(
        self,
        *,
        max_in_memory: int = 5,
        spill_connector: SQLConnector | None = None,
    ) -> None:
        if max_in_memory < 1:
            raise ValueError("max_in_memory must be >= 1")
        self._records: dict[str, QueryRecord] = {}
        self._families: dict[str, QueryFamily] = {}
        self._charts: dict[str, ChartArtifact] = {}
        self._maps: dict[str, MapArtifact] = {}
        self._graphs: dict[str, GraphArtifact] = {}
        self._next_query_id = 1
        self._next_family_id = 1
        self._next_chart_id = 1
        self._next_map_id = 1
        self._next_graph_id = 1
        self._max_in_memory = max_in_memory
        self._in_memory: deque[str] = deque()
        self._spilled: set[str] = set()
        self._spill_connector = spill_connector
        self._schema_created = False

    async def add(
        self, db_alias: str, connector_type: Literal["sql", "property_graph"], pred_query: PredQuery
    ) -> QueryRecord:
        """Store a query and assign it the next opaque record ID."""
        record_id = f"Q{self._next_query_id}"
        self._next_query_id += 1
        return await self._store(record_id, db_alias, connector_type, pred_query)

    async def add_family(
        self,
        db_alias: str,
        connector_type: Literal["sql", "property_graph"],
        dimensions: dict[str, list[str]],
        query_template: str,
        pred_queries_by_selection: dict[str, PredQuery],
    ) -> QueryFamily:
        """Store a query family and its per-selection records under a ``QS*`` id.

        Selections whose query text is identical share a single record.  Variant
        record ids stay out of the citable ``Q*`` namespace.
        """
        family_id = f"QS{self._next_family_id}"
        self._next_family_id += 1
        record_ids_by_query: dict[str, str] = {}
        record_ids_by_selection: dict[str, str] = {}
        for selection_key, pred_query in pred_queries_by_selection.items():
            record_id = record_ids_by_query.get(pred_query.query)
            if record_id is None:
                record_id = f"{family_id}_v{len(record_ids_by_query)}"
                record_ids_by_query[pred_query.query] = record_id
                await self._store(record_id, db_alias, connector_type, pred_query)
            record_ids_by_selection[selection_key] = record_id
        family = QueryFamily(
            family_id=family_id,
            db_alias=db_alias,
            connector_type=connector_type,
            dimensions=dimensions,
            query_template=query_template,
            record_ids_by_selection=record_ids_by_selection,
        )
        self._families[family_id] = family
        return family

    async def _store(
        self,
        record_id: str,
        db_alias: str,
        connector_type: Literal["sql", "property_graph"],
        pred_query: PredQuery,
    ) -> QueryRecord:
        """Register one record under ``record_id``, spilling its DataFrame when possible."""
        record = QueryRecord(
            record_id=record_id, connector_type=connector_type, db_alias=db_alias, pred_query=pred_query
        )
        pred_query.id = record_id
        self._records[record_id] = record
        if pred_query.exec_result is not None and pred_query.exec_result.df is not None:
            if self._spill_connector is None or await self._persist(record_id, pred_query.exec_result.df):
                self._in_memory.append(record_id)
                self._evict()
        return record

    def get_family(self, family_id: str) -> QueryFamily:
        """Return a previously stored query family."""
        try:
            return self._families[family_id]
        except KeyError:
            raise KeyError(f"No query family with id {family_id}") from None

    async def get(self, record_id: str) -> QueryRecord:
        """Return a previously stored query record, hydrating spilled DFs."""
        try:
            record = self._records[record_id]
        except KeyError:
            raise KeyError(f"No query with id {record_id}") from None
        if record_id in self._spilled:
            await self._hydrate(record_id, record)
        return record

    def add_chart(self, record_id: str, chart_spec: dict[str, Any]) -> str:
        """Store a chart artifact for an existing query record and return its opaque ``CHART*`` id."""
        if record_id not in self._records:
            raise KeyError(f"No query with id {record_id}")
        chart_id = f"CHART{self._next_chart_id}"
        self._charts[chart_id] = ChartArtifact(chart_id=chart_id, record_id=record_id, chart_spec=chart_spec)
        self._next_chart_id += 1
        return chart_id

    def get_chart(self, chart_id: str) -> ChartArtifact:
        """Return a previously stored chart artifact."""
        try:
            return self._charts[chart_id]
        except KeyError:
            raise KeyError(f"No chart with id {chart_id}") from None

    def add_map(self, map_spec: dict[str, Any]) -> str:
        """Store a standalone map artifact and return its opaque ``MAP*`` id."""
        map_id = f"MAP{self._next_map_id}"
        self._maps[map_id] = MapArtifact(map_id=map_id, map_spec=map_spec)
        self._next_map_id += 1
        return map_id

    def get_map(self, map_id: str) -> MapArtifact:
        """Return a previously stored map artifact."""
        try:
            return self._maps[map_id]
        except KeyError:
            raise KeyError(f"No map with id {map_id}") from None

    def add_graph(self, graph: GraphView, *, layout: Literal["force", "layered", "tree"] = "force") -> str:
        """Store a standalone graph artifact and return its opaque ``GRAPH*`` id."""
        graph_id = f"GRAPH{self._next_graph_id}"
        self._graphs[graph_id] = GraphArtifact(graph_id=graph_id, graph=graph, layout=layout)
        self._next_graph_id += 1
        return graph_id

    def get_graph(self, graph_id: str) -> GraphArtifact:
        """Return a previously stored graph artifact."""
        try:
            return self._graphs[graph_id]
        except KeyError:
            raise KeyError(f"No graph with id {graph_id}") from None

    # -- spill / hydrate internals --

    async def _ensure_schema(self) -> None:
        """Create the spill schema once."""
        if self._schema_created or self._spill_connector is None:
            return
        await self._spill_connector.run_query_async(f'CREATE SCHEMA IF NOT EXISTS "{_QH_SCHEMA}"')
        self._schema_created = True

    async def _persist(self, record_id: str, df: pd.DataFrame) -> bool:
        """Write a DF to the workspace DuckDB; return whether it can be hydrated later."""
        if self._spill_connector is None:
            return False
        try:
            await self._ensure_schema()
            await self._spill_connector.write_dataframe_async(
                df=df,
                table_name=record_id,
                schema_name=_QH_SCHEMA,
                mode="replace",
            )
            return True
        except Exception:
            logger.warning("Failed to persist %s to workspace", record_id, exc_info=True)
            return False

    def _evict(self) -> None:
        """Remove oldest in-memory DFs until within the limit."""
        if not self._spill_connector:
            return
        while len(self._in_memory) > self._max_in_memory:
            oldest_id = self._in_memory.popleft()
            exec_result = self._records[oldest_id].pred_query.exec_result
            if exec_result is not None:
                exec_result.df = None
            self._spilled.add(oldest_id)

    async def _hydrate(self, record_id: str, record: QueryRecord) -> None:
        """Load a spilled DF back from the workspace DuckDB."""
        assert self._spill_connector is not None
        result = await self._spill_connector.run_query_async(f'SELECT * FROM "{_QH_SCHEMA}"."{record_id}"')
        record.pred_query.exec_result.df = result.df  # type: ignore[union-attr]
        self._spilled.discard(record_id)
        self._in_memory.append(record_id)
        self._evict()
