"""Session-level query history with LRU spill to a workspace DuckDB."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from tabulaflow.core.outputs import ArtifactDef, ChartArtifactDef, GraphArtifactDef, MapArtifactDef
from tabulaflow.core.types import ErrorInfo, GraphView, PredQuery

if TYPE_CHECKING:
    import pandas as pd

    from tabulaflow.core.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)

# Schema this module spills result DataFrames into — one table per record. Kept out
# of the workspace connector's introspected schema (see ``create_workspace_connector``).
QUERY_HISTORY_SCHEMA = "_query_history"


@dataclass
class QueryFailure:
    """A query that failed during execution."""

    error: ErrorInfo


@dataclass
class TabularResult:
    """A successful query result with rows stored in the result store."""

    storage_key: str
    row_count: int
    columns: tuple[str, ...]
    df_is_truncated: bool = False
    graph: GraphView | None = None


@dataclass
class StatementSuccess:
    """A successful statement that did not return a tabular result set."""

    affected_rows: int | None = None


QueryOutcome: TypeAlias = QueryFailure | TabularResult | StatementSuccess


@dataclass
class QueryRecord:
    """Metadata for a query executed through the registry tool."""

    record_id: str
    connector_type: Literal["sql", "property_graph"]
    db_alias: str
    query: str
    parameter_names: tuple[str, ...]
    parameter_values: dict[str, Any]
    outcome: QueryOutcome
    latency_seconds: float | None = None


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
class ResolvedRecordRef:
    """Concrete query record selected for an artifact source."""

    record_id: str


@dataclass
class ResolvedQueryRecord:
    """Concrete query record payload selected for display/export."""

    record_id: str
    connector_type: Literal["sql", "property_graph"]
    query: str
    df: pd.DataFrame | None = None
    graph: GraphView | None = None

    @property
    def query_lexer(self) -> Literal["sql", "cypher"]:
        return "cypher" if self.connector_type == "property_graph" else "sql"


@dataclass
class SourceNotApplicable:
    """An artifact source has no record at the selected controls."""

    reason: str


SourceResolution: TypeAlias = ResolvedRecordRef | SourceNotApplicable


def _selection_key(selection: Mapping[str, str]) -> str:
    """Key a projected finite-choice selection into a query-family variant map."""
    return ";".join(f"{name}={choice}" for name, choice in sorted(selection.items()))


def _project_family_selection(
    family: QueryFamily, selection: Mapping[str, Any]
) -> dict[str, str] | SourceNotApplicable:
    """Project an answer selection onto the finite choices covered by ``family``."""
    projected: dict[str, str] = {}
    for name, choices in family.dimensions.items():
        if name not in selection:
            return SourceNotApplicable(f"missing selection for {name!r}")
        choice = str(selection[name])
        if choice not in choices:
            return SourceNotApplicable(f"{name}={choice} is outside {family.family_id}")
        projected[name] = choice
    return projected


class _ResultStore:
    """DuckDB-backed store for tabular query results, with a small memory cache."""

    def __init__(self, *, max_in_memory: int, spill_connector: SQLConnector | None = None) -> None:
        self._max_in_memory = max_in_memory
        self._spill_connector = spill_connector
        self._schema_created = False
        self._cache: OrderedDict[str, pd.DataFrame] = OrderedDict()
        self._persisted: set[str] = set()

    async def put_dataframe(self, storage_key: str, df: pd.DataFrame) -> str:
        if self._spill_connector is not None and await self._persist(storage_key, df):
            self._persisted.add(storage_key)
        self._cache[storage_key] = df
        self._cache.move_to_end(storage_key)
        self._evict()
        return storage_key

    async def get_dataframe(self, storage_key: str) -> pd.DataFrame:
        if storage_key in self._cache:
            self._cache.move_to_end(storage_key)
            return self._cache[storage_key]
        if storage_key not in self._persisted or self._spill_connector is None:
            raise KeyError(f"No stored result for {storage_key}")
        result = await self._spill_connector.run_query_async(f'SELECT * FROM "{QUERY_HISTORY_SCHEMA}"."{storage_key}"')
        if result.df is None:
            raise KeyError(f"No stored result for {storage_key}")
        self._cache[storage_key] = result.df
        self._cache.move_to_end(storage_key)
        self._evict()
        return result.df

    def has_in_memory(self, storage_key: str) -> bool:
        return storage_key in self._cache

    def is_persisted(self, storage_key: str) -> bool:
        return storage_key in self._persisted

    @property
    def in_memory_count(self) -> int:
        return len(self._cache)

    async def _ensure_schema(self) -> None:
        if self._schema_created or self._spill_connector is None:
            return
        await self._spill_connector.run_query_async(f'CREATE SCHEMA IF NOT EXISTS "{QUERY_HISTORY_SCHEMA}"')
        self._schema_created = True

    async def _persist(self, storage_key: str, df: pd.DataFrame) -> bool:
        if self._spill_connector is None:
            return False
        try:
            await self._ensure_schema()
            await self._spill_connector.write_dataframe_async(
                df=df,
                table_name=storage_key,
                schema_name=QUERY_HISTORY_SCHEMA,
                mode="replace",
            )
            return True
        except Exception:
            logger.warning("Failed to persist %s to workspace", storage_key, exc_info=True)
            return False

    def _evict(self) -> None:
        if self._spill_connector is None:
            return
        while len(self._cache) > self._max_in_memory:
            evictable = next((storage_key for storage_key in self._cache if storage_key in self._persisted), None)
            if evictable is None:
                return
            self._cache.pop(evictable)


class QueryHistory:
    """Query history with write-through result storage in a workspace DuckDB.

    Every successful result DataFrame is persisted to the workspace
    connector (when set). The most recent ``max_in_memory`` DataFrames are
    cached in RAM; older cached frames are reloaded explicitly through
    ``get_dataframe()``.

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
        self._artifacts: dict[str, ArtifactDef] = {}
        self._next_query_id = 1
        self._next_family_id = 1
        self._next_chart_id = 1
        self._next_map_id = 1
        self._next_graph_id = 1
        self._results = _ResultStore(max_in_memory=max_in_memory, spill_connector=spill_connector)

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
        """Register one record under ``record_id``."""
        outcome = await self._outcome(record_id, pred_query)
        exec_result = pred_query.exec_result
        record = QueryRecord(
            record_id=record_id,
            connector_type=connector_type,
            db_alias=db_alias,
            query=pred_query.query,
            parameter_names=tuple(pred_query.parameter_names),
            parameter_values=dict(pred_query.parameter_values),
            outcome=outcome,
            latency_seconds=exec_result.latency_seconds if exec_result is not None else None,
        )
        self._records[record_id] = record
        return record

    async def _outcome(self, record_id: str, pred_query: PredQuery) -> QueryOutcome:
        exec_result = pred_query.exec_result
        if exec_result is None:
            return StatementSuccess()
        if exec_result.error is not None:
            return QueryFailure(exec_result.error)
        if exec_result.df is None:
            return StatementSuccess(affected_rows=exec_result.affected_rows)
        storage_key = await self._results.put_dataframe(record_id, exec_result.df)
        return TabularResult(
            storage_key=storage_key,
            row_count=len(exec_result.df),
            columns=tuple(str(column) for column in exec_result.df.columns),
            df_is_truncated=exec_result.df_is_truncated,
            graph=exec_result.graph,
        )

    def get_family(self, family_id: str) -> QueryFamily:
        """Return a previously stored query family."""
        try:
            return self._families[family_id]
        except KeyError:
            raise KeyError(f"No query family with id {family_id}") from None

    def resolve_source_id(self, source_id: str, selection: Mapping[str, Any]) -> SourceResolution:
        """Resolve an artifact's logical source to a concrete query record under ``selection``."""
        if source_id.startswith("QS"):
            family = self.get_family(source_id)
            projected = _project_family_selection(family, selection)
            if isinstance(projected, SourceNotApplicable):
                return projected
            key = _selection_key(projected)
            record_id = family.record_ids_by_selection.get(key)
            if record_id is None:
                return SourceNotApplicable(f"{source_id} has no result for {key}")
            self._require_record(record_id)
            return ResolvedRecordRef(record_id)

        if source_id.startswith("Q"):
            self._require_record(source_id)
            return ResolvedRecordRef(source_id)

        raise ValueError(f"source_id must start with 'Q' or 'QS', got {source_id!r}")

    def _require_record(self, record_id: str) -> None:
        if record_id not in self._records:
            raise KeyError(f"No query with id {record_id}")

    async def get(self, record_id: str) -> QueryRecord:
        """Return a previously stored query record."""
        try:
            return self._records[record_id]
        except KeyError:
            raise KeyError(f"No query with id {record_id}") from None

    async def get_dataframe(self, record_id: str) -> pd.DataFrame:
        """Return the DataFrame for a tabular query result."""
        record = await self.get(record_id)
        if isinstance(record.outcome, QueryFailure):
            raise ValueError(f"query {record_id} failed: {record.outcome.error.message}")
        if not isinstance(record.outcome, TabularResult):
            raise ValueError(f"query {record_id} returned no data")
        return await self._results.get_dataframe(record.outcome.storage_key)

    async def get_query_record_payload(self, record_id: str) -> ResolvedQueryRecord:
        """Return a query record with its stored DataFrame when one exists."""
        record = await self.get(record_id)
        df = None
        try:
            df = await self.get_dataframe(record.record_id)
        except ValueError:
            pass
        return ResolvedQueryRecord(
            record_id=record.record_id,
            connector_type=record.connector_type,
            query=record.query,
            df=df,
            graph=getattr(record.outcome, "graph", None),
        )

    async def resolve_query_record(
        self,
        source_id: str,
        selection: Mapping[str, Any],
    ) -> ResolvedQueryRecord | SourceNotApplicable:
        """Resolve a ``Q*``/``QS*`` source id to its concrete query record payload."""
        resolution = self.resolve_source_id(source_id, selection)
        if isinstance(resolution, SourceNotApplicable):
            return resolution
        return await self.get_query_record_payload(resolution.record_id)

    def add_chart(self, source_id: str, chart_spec: dict[str, Any]) -> str:
        """Store a chart artifact for an existing query record and return its opaque ``CHART*`` id."""
        if source_id.startswith("QS"):
            self.get_family(source_id)
        elif source_id.startswith("Q"):
            self._require_record(source_id)
        else:
            raise ValueError(f"source_id must start with 'Q' or 'QS', got {source_id!r}")
        chart_id = f"CHART{self._next_chart_id}"
        self._artifacts[chart_id] = ChartArtifactDef(chart_id=chart_id, source_id=source_id, chart_spec=chart_spec)
        self._next_chart_id += 1
        return chart_id

    def get_chart(self, chart_id: str) -> ChartArtifactDef:
        """Return a previously stored chart artifact."""
        artifact = self.get_artifact(chart_id)
        if not isinstance(artifact, ChartArtifactDef):
            raise KeyError(f"No chart with id {chart_id}") from None
        return artifact

    def add_map(self, map_spec: dict[str, Any]) -> str:
        """Store a standalone map artifact and return its opaque ``MAP*`` id."""
        map_id = f"MAP{self._next_map_id}"
        self._artifacts[map_id] = MapArtifactDef(map_id=map_id, map_spec=map_spec)
        self._next_map_id += 1
        return map_id

    def get_map(self, map_id: str) -> MapArtifactDef:
        """Return a previously stored map artifact."""
        artifact = self.get_artifact(map_id)
        if not isinstance(artifact, MapArtifactDef):
            raise KeyError(f"No map with id {map_id}") from None
        return artifact

    def add_graph(self, graph_spec: dict[str, Any]) -> str:
        """Store a standalone graph artifact and return its opaque ``GRAPH*`` id."""
        graph_id = f"GRAPH{self._next_graph_id}"
        self._artifacts[graph_id] = GraphArtifactDef(graph_id=graph_id, graph_spec=graph_spec)
        self._next_graph_id += 1
        return graph_id

    def get_graph(self, graph_id: str) -> GraphArtifactDef:
        """Return a previously stored graph artifact."""
        artifact = self.get_artifact(graph_id)
        if not isinstance(artifact, GraphArtifactDef):
            raise KeyError(f"No graph with id {graph_id}") from None
        return artifact

    def get_artifact(self, artifact_id: str) -> ArtifactDef:
        """Return a previously stored chart, map, or graph artifact definition."""
        try:
            return self._artifacts[artifact_id]
        except KeyError:
            raise KeyError(f"No artifact with id {artifact_id}") from None
