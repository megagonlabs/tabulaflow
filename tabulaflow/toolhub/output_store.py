"""Session-level output store with LRU DataFrame spill to a workspace DuckDB."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from tabulaflow.core.dataframe import _deserialize_dataframe, _serialize_dataframe
from tabulaflow.core.outputs import (
    ArtifactSpec,
    ChartView,
    ConstantResultPlan,
    GraphArtifactView,
    MapView,
    ResultId,
    ResultLookupPlan,
    ResultRecord,
    ResultVariant,
    SelectionValue,
    SourceDef,
)
from tabulaflow.core.types import ErrorInfo, GraphView, PredQuery

if TYPE_CHECKING:
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)

# Schema this module spills result DataFrames into — one table per record. Kept out
# of the workspace connector's introspected schema (see ``create_workspace_connector``).
OUTPUT_STORE_SCHEMA = "_output_store"


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
class StoredResult:
    """Internal metadata and outcome for a materialized result."""

    result_id: str
    source_id: str | None
    connector_type: Literal["sql", "property_graph"]
    db_alias: str
    query: str
    parameter_names: tuple[str, ...]
    parameter_values: dict[str, Any]
    outcome: QueryOutcome
    latency_seconds: float | None = None

class ResultPayload(BaseModel):
    """Runtime payload for a materialized result."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    record: ResultRecord
    df: pd.DataFrame | None = None
    graph: GraphView | None = None

    @field_serializer("df", when_used="always")
    def _serialize_df(self, df: pd.DataFrame | None) -> dict[str, object] | None:
        return _serialize_dataframe(df)

    @field_validator("df", mode="before")
    @classmethod
    def _deserialize_df(cls, v: dict[str, object] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)


def _map_source_ids(spec: Mapping[str, Any]) -> list[str]:
    source_ids: list[str] = []
    for layer in spec.get("layers") or []:
        source_id = layer.get("source") if isinstance(layer, Mapping) else None
        if isinstance(source_id, str) and source_id not in source_ids:
            source_ids.append(source_id)
    return source_ids


def _graph_source_ids(spec: Mapping[str, Any]) -> list[str]:
    source_ids: list[str] = []
    for key in ("nodes", "edges"):
        raw_sources = spec.get(key)
        for source in raw_sources if isinstance(raw_sources, list) else []:
            if not isinstance(source, Mapping) or "data" in source:
                continue
            source_id = source.get("source_id")
            if isinstance(source_id, str) and source_id not in source_ids:
                source_ids.append(source_id)
    return source_ids


def _selection_from_key(key: str) -> dict[str, SelectionValue]:
    if not key:
        return {}
    selection: dict[str, SelectionValue] = {}
    for part in key.split(";"):
        if not part:
            continue
        name, value = part.split("=", 1)
        selection[name] = value
    return selection


class _ResultFrameStore:
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
        result = await self._spill_connector.run_query_async(f'SELECT * FROM "{OUTPUT_STORE_SCHEMA}"."{storage_key}"')
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
        await self._spill_connector.run_query_async(f'CREATE SCHEMA IF NOT EXISTS "{OUTPUT_STORE_SCHEMA}"')
        self._schema_created = True

    async def _persist(self, storage_key: str, df: pd.DataFrame) -> bool:
        if self._spill_connector is None:
            return False
        try:
            await self._ensure_schema()
            await self._spill_connector.write_dataframe_async(
                df=df,
                table_name=storage_key,
                schema_name=OUTPUT_STORE_SCHEMA,
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


class OutputStore:
    """Output store with write-through result storage in a workspace DuckDB.

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
        self._records: dict[str, StoredResult] = {}
        self._sources: dict[str, SourceDef] = {}
        self._artifacts: dict[str, ArtifactSpec] = {}
        self._next_result_id = 1
        self._next_source_id = 1
        self._next_chart_id = 1
        self._next_map_id = 1
        self._next_graph_id = 1
        self._results = _ResultFrameStore(max_in_memory=max_in_memory, spill_connector=spill_connector)

    async def add(
        self, db_alias: str, connector_type: Literal["sql", "property_graph"], pred_query: PredQuery
    ) -> StoredResult:
        """Store a query result and create a constant source for it."""
        result_id = self._next_result_id_value()
        source_id = self._next_source_id_value()
        record = await self._store(result_id, db_alias, connector_type, pred_query, source_id=source_id)
        self._sources[source_id] = SourceDef(id=source_id, plan=ConstantResultPlan(result_id=result_id))
        return record

    async def add_family(
        self,
        db_alias: str,
        connector_type: Literal["sql", "property_graph"],
        dimensions: dict[str, list[str]],
        query_template: str,
        pred_queries_by_selection: dict[str, PredQuery],
    ) -> SourceDef:
        """Store a result-lookup source and its per-selection results.

        Selections whose query text is identical share a single record.  Variant
        result ids stay out of the citable source namespace.
        """
        source_id = self._next_source_id_value()
        record_ids_by_query: dict[str, str] = {}
        record_ids_by_selection: dict[str, str] = {}
        for selection_key, pred_query in pred_queries_by_selection.items():
            record_id = record_ids_by_query.get(pred_query.query)
            if record_id is None:
                record_id = self._next_result_id_value()
                record_ids_by_query[pred_query.query] = record_id
                await self._store(record_id, db_alias, connector_type, pred_query, source_id=None)
            record_ids_by_selection[selection_key] = record_id
        source = SourceDef(
            id=source_id,
            parameter_ids=list(dimensions),
            plan=ResultLookupPlan(
                variants=[
                    ResultVariant(selection=_selection_from_key(key), result_id=result_id)
                    for key, result_id in record_ids_by_selection.items()
                ]
            ),
        )
        self._sources[source_id] = source
        return source

    def _next_result_id_value(self) -> str:
        result_id = f"R{self._next_result_id}"
        self._next_result_id += 1
        return result_id

    def _next_source_id_value(self) -> str:
        source_id = f"S{self._next_source_id}"
        self._next_source_id += 1
        return source_id

    async def _store(
        self,
        record_id: str,
        db_alias: str,
        connector_type: Literal["sql", "property_graph"],
        pred_query: PredQuery,
        *,
        source_id: str | None,
    ) -> StoredResult:
        """Register one record under ``record_id``."""
        outcome = await self._outcome(record_id, pred_query)
        exec_result = pred_query.exec_result
        record = StoredResult(
            result_id=record_id,
            source_id=source_id,
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

    def get_source(self, source_id: str) -> SourceDef:
        """Return a previously stored source."""
        try:
            return self._sources[source_id]
        except KeyError:
            raise KeyError(f"No source with id {source_id}") from None

    def get_constant_source_result_id(self, source_id: str) -> str:
        """Return the result id for a single-result source."""
        source = self.get_source(source_id)
        if not isinstance(source.plan, ConstantResultPlan):
            raise ValueError(f"source {source_id!r} is not a single-result source")
        return source.plan.result_id

    def _require_record(self, record_id: str) -> None:
        if record_id not in self._records:
            raise KeyError(f"No result with id {record_id}")

    async def get(self, record_id: str) -> StoredResult:
        """Return an internal stored result."""
        try:
            return self._records[record_id]
        except KeyError:
            raise KeyError(f"No result with id {record_id}") from None

    async def get_dataframe(self, record_id: str) -> pd.DataFrame:
        """Return the DataFrame for a tabular query result."""
        record = await self.get(record_id)
        if isinstance(record.outcome, QueryFailure):
            raise ValueError(f"query {record_id} failed: {record.outcome.error.message}")
        if not isinstance(record.outcome, TabularResult):
            raise ValueError(f"query {record_id} returned no data")
        return await self._results.get_dataframe(record.outcome.storage_key)

    async def get_record(self, result_id: ResultId) -> ResultRecord:
        """Return clean metadata for a materialized result."""
        record = await self.get(result_id)
        row_count = None
        columns = None
        if isinstance(record.outcome, TabularResult):
            row_count = record.outcome.row_count
            columns = list(record.outcome.columns)
        return ResultRecord(
            id=record.result_id,
            db_alias=record.db_alias,
            query=record.query,
            connector_type=record.connector_type,
            parameter_values=record.parameter_values,
            row_count=row_count,
            columns=columns,
        )

    async def get_payload(self, result_id: ResultId) -> ResultPayload:
        """Return clean payload for a materialized result."""
        raw = await self.get(result_id)
        record = await self.get_record(result_id)
        df = None
        try:
            df = await self.get_dataframe(result_id)
        except ValueError:
            pass
        return ResultPayload(record=record, df=df, graph=getattr(raw.outcome, "graph", None))

    def add_chart(self, source_id: str, chart_spec: dict[str, Any]) -> str:
        """Store a chart artifact for an existing source and return its opaque ``CHART*`` id."""
        self.get_source(source_id)
        chart_id = f"CHART{self._next_chart_id}"
        self._artifacts[chart_id] = ArtifactSpec(id=chart_id, view=ChartView(source=source_id, spec=chart_spec))
        self._next_chart_id += 1
        return chart_id

    def get_chart(self, chart_id: str) -> ArtifactSpec:
        """Return a previously stored chart artifact."""
        artifact = self.get_artifact(chart_id)
        if not isinstance(artifact.view, ChartView):
            raise KeyError(f"No chart with id {chart_id}") from None
        return artifact

    def add_map(self, map_spec: dict[str, Any]) -> str:
        """Store a standalone map artifact and return its opaque ``MAP*`` id."""
        map_id = f"MAP{self._next_map_id}"
        self._artifacts[map_id] = ArtifactSpec(id=map_id, view=MapView(sources=_map_source_ids(map_spec), spec=map_spec))
        self._next_map_id += 1
        return map_id

    def get_map(self, map_id: str) -> ArtifactSpec:
        """Return a previously stored map artifact."""
        artifact = self.get_artifact(map_id)
        if not isinstance(artifact.view, MapView):
            raise KeyError(f"No map with id {map_id}") from None
        return artifact

    def add_graph(self, graph_spec: dict[str, Any]) -> str:
        """Store a standalone graph artifact and return its opaque ``GRAPH*`` id."""
        graph_id = f"GRAPH{self._next_graph_id}"
        self._artifacts[graph_id] = ArtifactSpec(
            id=graph_id, view=GraphArtifactView(sources=_graph_source_ids(graph_spec), spec=graph_spec)
        )
        self._next_graph_id += 1
        return graph_id

    def get_graph(self, graph_id: str) -> ArtifactSpec:
        """Return a previously stored graph artifact."""
        artifact = self.get_artifact(graph_id)
        if not isinstance(artifact.view, GraphArtifactView):
            raise KeyError(f"No graph with id {graph_id}") from None
        return artifact

    def get_artifact(self, artifact_id: str) -> ArtifactSpec:
        """Return a previously stored chart, map, or graph artifact definition."""
        try:
            return self._artifacts[artifact_id]
        except KeyError:
            raise KeyError(f"No artifact with id {artifact_id}") from None
