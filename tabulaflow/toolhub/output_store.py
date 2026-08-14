"""Session-level output store with LRU DataFrame spill to a workspace DuckDB."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import TYPE_CHECKING, Literal, NoReturn

import jinja2
import pandas as pd

from tabulaflow.core.outputs import (
    ArtifactId,
    ArtifactSpec,
    ChartArtifactSpec,
    FixedResultSource,
    GraphArtifactSpec,
    MapArtifactSpec,
    ParameterSpec,
    ParameterizedSource,
    ResultId,
    ResultMetadata,
    Selection,
    SourceSpec,
    SourceId,
    artifact_source_ids,
    canonical_selection_key,
)
from tabulaflow.core.types import GraphView, PredQuery

if TYPE_CHECKING:
    from tabulaflow.core.db_connector.db_registry import DBRegistry
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

logger = logging.getLogger(__name__)

# Schema this module spills result DataFrames into — one table per result. Kept out
# of the workspace connector's introspected schema (see ``create_workspace_connector``).
OUTPUT_STORE_SCHEMA = "_output_store"


class SourceNotApplicable(Exception):
    """A parameterized source intentionally does not apply to a selection."""


def _not_applicable(reason: object = "not applicable") -> NoReturn:
    raise SourceNotApplicable(str(reason))


_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True)
_JINJA_ENV.globals["not_applicable"] = _not_applicable


@dataclass
class _StoredResultEntry:
    """Internal metadata and storage pointers for one materialized result."""

    metadata: ResultMetadata
    has_dataframe: bool = False
    graph: GraphView | None = None

@dataclass(frozen=True)
class ResultPayload:
    """Runtime payload for a materialized result."""

    metadata: ResultMetadata
    df: pd.DataFrame | None = None
    graph: GraphView | None = None


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

    async def get_result_dataframe(self, storage_key: str) -> pd.DataFrame:
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
    ``get_payload()``.

    Args:
        max_in_memory: Number of result DataFrames to keep in RAM.
    """

    def __init__(
        self,
        *,
        max_in_memory: int = 5,
        spill_connector: SQLConnector | None = None,
        registry: DBRegistry | None = None,
    ) -> None:
        if max_in_memory < 1:
            raise ValueError("max_in_memory must be >= 1")
        self._results_by_id: dict[str, _StoredResultEntry] = {}
        self._parameters: dict[str, ParameterSpec] = {}
        self._sources: dict[str, SourceSpec] = {}
        self._source_cache: dict[tuple[str, str], str] = {}
        self._artifacts: dict[str, ArtifactSpec] = {}
        self._next_result_id = 1
        self._next_source_id = 1
        self._next_artifact_ids: dict[str, int] = {}
        self._results = _ResultFrameStore(max_in_memory=max_in_memory, spill_connector=spill_connector)
        self._registry = registry

    async def add_fixed_result_source(
        self, db_alias: str, connector_type: Literal["sql", "property_graph"], pred_query: PredQuery
    ) -> FixedResultSource:
        """Store a query result and create a fixed source for it."""
        result_id = self._next_result_id_value()
        source_id = self._next_source_id_value()
        await self._store(result_id, db_alias, connector_type, pred_query)
        source = FixedResultSource(id=source_id, result_id=result_id)
        self._sources[source_id] = source
        return source

    def register_parameter(self, parameter: ParameterSpec) -> None:
        """Register one output parameter, rejecting conflicting reuse."""
        existing = self._parameters.get(parameter.id)
        if existing is None:
            self._parameters[parameter.id] = parameter
            return
        if existing != parameter:
            raise ValueError(f"parameter {parameter.id!r} already exists with a different definition")

    def get_parameter(self, parameter_id: str) -> ParameterSpec:
        """Return a registered parameter definition."""
        try:
            return self._parameters[parameter_id]
        except KeyError:
            raise KeyError(f"No parameter with id {parameter_id}") from None

    def source_parameters(self, source_id: str) -> list[ParameterSpec]:
        """Return the parameter definitions required by ``source_id``."""
        source = self.get_source(source_id)
        if not isinstance(source, ParameterizedSource):
            return []
        return [self.get_parameter(parameter_id) for parameter_id in source.parameter_ids]

    def add_parameterized_source(
        self,
        db_alias: str,
        parameters: list[ParameterSpec],
        query_template: str,
    ) -> ParameterizedSource:
        """Create a parameterized source from registered parameters and a query template."""
        source_id = self._next_source_id_value()
        for parameter in parameters:
            self.register_parameter(parameter)
        source = ParameterizedSource(
            id=source_id,
            parameter_ids=[parameter.id for parameter in parameters],
            db_alias=db_alias,
            query_template=query_template,
        )
        self._sources[source_id] = source
        return source

    async def cache_parameterized_result(
        self,
        source_id: str,
        connector_type: Literal["sql", "property_graph"],
        selection: Selection,
        pred_query: PredQuery,
    ) -> ResultId:
        """Seed or replace one cached materialization for a parameterized source."""
        source = self.get_source(source_id)
        if not isinstance(source, ParameterizedSource):
            raise ValueError(f"source {source_id!r} is not parameterized")
        result_id = self._next_result_id_value()
        await self._store(result_id, source.db_alias, connector_type, pred_query, selection=selection)
        self._source_cache[(source.id, canonical_selection_key(selection))] = result_id
        return result_id

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
        result_id: str,
        db_alias: str,
        connector_type: Literal["sql", "property_graph"],
        pred_query: PredQuery,
        *,
        selection: Selection | None = None,
    ) -> _StoredResultEntry:
        """Register one result under ``result_id``."""
        exec_result = pred_query.exec_result
        if exec_result is not None and exec_result.error is not None:
            raise ValueError(exec_result.error.message)
        df = exec_result.df if exec_result is not None else None
        if df is not None:
            await self._results.put_dataframe(result_id, df)
        row_count = len(df) if df is not None else None
        columns = [str(column) for column in df.columns] if df is not None else None
        metadata = ResultMetadata(
            id=result_id,
            db_alias=db_alias,
            query=pred_query.query,
            connector_type=connector_type,
            source_selection={} if selection is None else dict(selection),
            row_count=row_count,
            columns=columns,
            latency_seconds=exec_result.latency_seconds if exec_result is not None else None,
        )
        stored = _StoredResultEntry(metadata=metadata, has_dataframe=df is not None, graph=exec_result.graph if exec_result is not None else None)
        self._results_by_id[result_id] = stored
        return stored

    def get_source(self, source_id: str) -> SourceSpec:
        """Return a previously stored source."""
        try:
            return self._sources[source_id]
        except KeyError:
            raise KeyError(f"No source with id {source_id}") from None

    def cached_parameterized_results(self, source_id: str) -> dict[str, str]:
        """Return cached selection keys and result ids for a parameterized source."""
        return {
            selection_key: result_id
            for (cached_source_id, selection_key), result_id in self._source_cache.items()
            if cached_source_id == source_id
        }

    async def resolve_source(self, source_id: str, selection: Selection | None = None) -> ResultPayload:
        """Resolve a source to a materialized payload, materializing parameterized cache misses."""
        source = self.get_source(source_id)
        if isinstance(source, FixedResultSource):
            return await self.get_payload(source.result_id)
        if not isinstance(source, ParameterizedSource):
            raise TypeError(f"unsupported source {type(source).__name__}")
        selection = selection or {}
        selection_key = canonical_selection_key(selection)
        result_id = self._source_cache.get((source.id, selection_key))
        if result_id is None:
            result_id = await self._materialize_parameterized_source(source, selection)
        return await self.get_payload(result_id)

    async def _materialize_parameterized_source(
        self,
        source: ParameterizedSource,
        selection: Selection,
    ) -> ResultId:
        query = render_parameterized_query(source.query_template, selection)
        if self._registry is None:
            raise KeyError(f"source {source.id!r} has no result for selection {canonical_selection_key(selection)}")
        connector = self._registry.get(source.db_alias)
        exec_result = await connector.run_query_async(query)
        pred_query = PredQuery(query=query, exec_result=exec_result)
        return await self.cache_parameterized_result(source.id, connector.connector_type, selection, pred_query)

    async def _get_result_entry(self, result_id: str) -> _StoredResultEntry:
        """Return the stored entry for a materialized result."""
        try:
            return self._results_by_id[result_id]
        except KeyError:
            raise KeyError(f"No result with id {result_id}") from None

    async def _get_dataframe(self, result_id: str) -> pd.DataFrame:
        """Return the DataFrame for a tabular query result."""
        stored = await self._get_result_entry(result_id)
        if not stored.has_dataframe:
            raise ValueError(f"query {result_id} returned no data")
        return await self._results.get_result_dataframe(result_id)

    async def get_metadata(self, result_id: ResultId) -> ResultMetadata:
        """Return clean metadata for a materialized result."""
        return (await self._get_result_entry(result_id)).metadata

    async def get_payload(self, result_id: ResultId) -> ResultPayload:
        """Return clean payload for a materialized result."""
        entry = await self._get_result_entry(result_id)
        metadata = await self.get_metadata(result_id)
        df = None
        try:
            df = await self._get_dataframe(result_id)
        except ValueError:
            pass
        return ResultPayload(metadata=metadata, df=df, graph=entry.graph)

    def add_chart_artifact(self, source_id: SourceId, spec: Mapping[str, object], label: str | None = None) -> ChartArtifactSpec:
        """Store a chart artifact under a ``CHART<n>`` id."""
        artifact_id = self._next_artifact_id("CHART")
        artifact = ChartArtifactSpec(id=artifact_id, label=label, source_id=source_id, spec=dict(spec))
        self._store_artifact(artifact)
        return artifact

    def add_map_artifact(self, source_ids: list[SourceId], spec: Mapping[str, object], label: str | None = None) -> MapArtifactSpec:
        """Store a map artifact under a ``MAP<n>`` id."""
        artifact_id = self._next_artifact_id("MAP")
        artifact = MapArtifactSpec(id=artifact_id, label=label, source_ids=source_ids, spec=dict(spec))
        self._store_artifact(artifact)
        return artifact

    def add_graph_artifact(self, source_ids: list[SourceId], spec: Mapping[str, object], label: str | None = None) -> GraphArtifactSpec:
        """Store a graph artifact under a ``GRAPH<n>`` id."""
        artifact_id = self._next_artifact_id("GRAPH")
        artifact = GraphArtifactSpec(id=artifact_id, label=label, source_ids=source_ids, spec=dict(spec))
        self._store_artifact(artifact)
        return artifact

    def _next_artifact_id(self, prefix: str) -> ArtifactId:
        if not prefix or not prefix.isidentifier() or prefix != prefix.upper():
            raise ValueError(f"artifact prefix must be uppercase identifier text, got {prefix!r}")
        next_id = self._next_artifact_ids.get(prefix, 1)
        artifact_id: ArtifactId = f"{prefix}{next_id}"
        self._next_artifact_ids[prefix] = next_id + 1
        return artifact_id

    def _store_artifact(self, artifact: ArtifactSpec) -> None:
        for source_id in artifact_source_ids(artifact):
            self.get_source(source_id)
        self._artifacts[artifact.id] = artifact

    def get_artifact(self, artifact_id: str) -> ArtifactSpec:
        """Return a previously stored chart, map, or graph artifact definition."""
        try:
            return self._artifacts[artifact_id]
        except KeyError:
            raise KeyError(f"No artifact with id {artifact_id}") from None


def render_parameterized_query(query_template: str, selection: Selection) -> str:
    """Render a parameterized-source query template with validated scalar values."""
    for name, value in selection.items():
        if isinstance(value, bool):
            raise ValueError(f"{name} must not be boolean")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    return _JINJA_ENV.from_string(query_template).render(**selection)
