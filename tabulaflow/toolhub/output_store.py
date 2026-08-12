"""Session-level output store with LRU DataFrame spill to a workspace DuckDB."""

from __future__ import annotations

import logging
import json
from collections import OrderedDict
from dataclasses import dataclass
import math
from typing import TYPE_CHECKING, Literal

import jinja2
import pandas as pd
from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from tabulaflow.core.dataframe import _deserialize_dataframe, _serialize_dataframe
from tabulaflow.core.outputs import (
    ArtifactId,
    ArtifactSpec,
    FixedResultSource,
    ParameterId,
    ParameterDef,
    ParameterizedSource,
    ResultId,
    ResultMetadata,
    SelectionValue,
    SourceDef,
    ViewDef,
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
_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True)


@dataclass
class _StoredResult:
    """Internal metadata and outcome for a materialized result."""

    metadata: ResultMetadata
    has_dataframe: bool = False
    graph: GraphView | None = None

class ResultPayload(BaseModel):
    """Runtime payload for a materialized result."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: ResultMetadata
    df: pd.DataFrame | None = None
    graph: GraphView | None = None

    @field_serializer("df", when_used="always")
    def _serialize_df(self, df: pd.DataFrame | None) -> dict[str, object] | None:
        return _serialize_dataframe(df)

    @field_validator("df", mode="before")
    @classmethod
    def _deserialize_df(cls, v: dict[str, object] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)


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
        self._records: dict[str, _StoredResult] = {}
        self._parameters: dict[str, ParameterDef] = {}
        self._sources: dict[str, SourceDef] = {}
        self._source_cache: dict[tuple[str, str], str] = {}
        self._artifacts: dict[str, ArtifactSpec] = {}
        self._next_result_id = 1
        self._next_source_id = 1
        self._next_artifact_ids: dict[str, int] = {}
        self._results = _ResultFrameStore(max_in_memory=max_in_memory, spill_connector=spill_connector)
        self._registry = registry

    async def add_result(
        self, db_alias: str, connector_type: Literal["sql", "property_graph"], pred_query: PredQuery
    ) -> SourceDef:
        """Store a query result and create a constant source for it."""
        result_id = self._next_result_id_value()
        source_id = self._next_source_id_value()
        await self._store(result_id, db_alias, connector_type, pred_query)
        source = FixedResultSource(id=source_id, result_id=result_id)
        self._sources[source_id] = source
        return source

    def add_parameter(self, parameter: ParameterDef) -> None:
        """Register one output parameter, rejecting conflicting reuse."""
        existing = self._parameters.get(parameter.id)
        if existing is None:
            self._parameters[parameter.id] = parameter
            return
        if existing != parameter:
            raise ValueError(f"parameter {parameter.id!r} already exists with a different definition")

    def get_parameter(self, parameter_id: str) -> ParameterDef:
        """Return a registered parameter definition."""
        try:
            return self._parameters[parameter_id]
        except KeyError:
            raise KeyError(f"No parameter with id {parameter_id}") from None

    def parameters_for_source(self, source: SourceDef) -> list[ParameterDef]:
        """Return the parameter definitions required by ``source``."""
        if not isinstance(source, ParameterizedSource):
            return []
        return [self.get_parameter(parameter_id) for parameter_id in source.parameter_ids]

    async def add_parameterized_source(
        self,
        db_alias: str,
        parameters: list[ParameterDef],
        query_template: str,
    ) -> ParameterizedSource:
        """Create a parameterized source from registered parameters and a query template."""
        source_id = self._next_source_id_value()
        for parameter in parameters:
            self.add_parameter(parameter)
        source = ParameterizedSource(
            id=source_id,
            parameter_ids=[parameter.id for parameter in parameters],
            db_alias=db_alias,
            query_template=query_template,
        )
        self._sources[source_id] = source
        return source

    async def add_prewarmed_parameterized_source(
        self,
        db_alias: str,
        connector_type: Literal["sql", "property_graph"],
        parameters: list[ParameterDef],
        query_template: str,
        pred_queries_by_selection: dict[str, PredQuery],
    ) -> ParameterizedSource:
        """Create a parameterized source and seed its runtime cache.

        Selections whose query text is identical share a single result.  Variant
        result ids stay out of the citable source namespace.
        """
        source = await self.add_parameterized_source(db_alias, parameters, query_template)
        source_id = source.id
        result_ids_by_query: dict[str, str] = {}
        result_ids_by_selection: dict[str, str] = {}
        for selection_key, pred_query in pred_queries_by_selection.items():
            selection = _selection_from_key(selection_key)
            pred_query.parameter_values = dict(selection)
            result_id = result_ids_by_query.get(pred_query.query)
            if result_id is None:
                result_id = self._next_result_id_value()
                result_ids_by_query[pred_query.query] = result_id
                await self._store(result_id, db_alias, connector_type, pred_query)
            result_ids_by_selection[selection_key] = result_id
        for key, result_id in result_ids_by_selection.items():
            self._source_cache[(source_id, canonical_selection_key(_selection_from_key(key)))] = result_id
        return source

    async def add_cached_parameterized_result(
        self,
        source: ParameterizedSource,
        connector_type: Literal["sql", "property_graph"],
        selection: dict[ParameterId, SelectionValue],
        pred_query: PredQuery,
    ) -> ResultId:
        """Seed or replace one cached materialization for a parameterized source."""
        result_id = self._next_result_id_value()
        pred_query.parameter_values = dict(selection)
        await self._store(result_id, source.db_alias, connector_type, pred_query)
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
    ) -> _StoredResult:
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
            parameter_values=dict(pred_query.parameter_values),
            row_count=row_count,
            columns=columns,
            latency_seconds=exec_result.latency_seconds if exec_result is not None else None,
        )
        stored = _StoredResult(metadata=metadata, has_dataframe=df is not None, graph=exec_result.graph if exec_result is not None else None)
        self._records[result_id] = stored
        return stored

    def get_source(self, source_id: str) -> SourceDef:
        """Return a previously stored source."""
        try:
            return self._sources[source_id]
        except KeyError:
            raise KeyError(f"No source with id {source_id}") from None

    def get_cached_source_selections(self, source_id: str) -> list[dict[ParameterId, SelectionValue]]:
        """Return selections currently cached for a parameterized source."""
        selections: list[dict[ParameterId, SelectionValue]] = []
        for cached_source_id, selection_key in self._source_cache:
            if cached_source_id == source_id:
                selections.append(json.loads(selection_key))
        return selections

    def get_cached_source_results(self, source_id: str) -> dict[str, str]:
        """Return cached selection keys and result ids for a parameterized source."""
        return {
            selection_key: result_id
            for (cached_source_id, selection_key), result_id in self._source_cache.items()
            if cached_source_id == source_id
        }

    async def resolve_parameterized_source(
        self, source: ParameterizedSource, selection: dict[ParameterId, SelectionValue]
    ) -> ResultMetadata:
        """Resolve a parameterized source through the runtime cache."""
        selection_key = canonical_selection_key(selection)
        result_id = self._source_cache.get((source.id, selection_key))
        if result_id is None:
            result_id = await self._materialize_parameterized_source(source, selection)
        return await self.get_metadata(result_id)

    async def _materialize_parameterized_source(
        self,
        source: ParameterizedSource,
        selection: dict[ParameterId, SelectionValue],
    ) -> ResultId:
        if self._registry is None:
            raise KeyError(f"source {source.id!r} has no result for selection {canonical_selection_key(selection)}")
        query = render_parameterized_query(source.query_template, selection)
        connector = self._registry.get(source.db_alias)
        exec_result = await connector.run_query_async(query)
        pred_query = PredQuery(query=query, parameter_values=dict(selection), exec_result=exec_result)
        return await self.add_cached_parameterized_result(source, connector.connector_type, selection, pred_query)

    async def _get_result(self, result_id: str) -> _StoredResult:
        """Return an internal stored result."""
        try:
            return self._records[result_id]
        except KeyError:
            raise KeyError(f"No result with id {result_id}") from None

    async def _get_dataframe(self, result_id: str) -> pd.DataFrame:
        """Return the DataFrame for a tabular query result."""
        stored = await self._get_result(result_id)
        if not stored.has_dataframe:
            raise ValueError(f"query {result_id} returned no data")
        return await self._results.get_result_dataframe(result_id)

    async def get_metadata(self, result_id: ResultId) -> ResultMetadata:
        """Return clean metadata for a materialized result."""
        return (await self._get_result(result_id)).metadata

    async def get_payload(self, result_id: ResultId) -> ResultPayload:
        """Return clean payload for a materialized result."""
        raw = await self._get_result(result_id)
        metadata = await self.get_metadata(result_id)
        df = None
        try:
            df = await self._get_dataframe(result_id)
        except ValueError:
            pass
        return ResultPayload(metadata=metadata, df=df, graph=raw.graph)

    def add_artifact(self, prefix: str, view: ViewDef, label: str | None = None) -> ArtifactSpec:
        """Store an artifact spec under an id allocated from ``prefix``."""
        if not prefix or not prefix.isidentifier() or prefix != prefix.upper():
            raise ValueError(f"artifact prefix must be uppercase identifier text, got {prefix!r}")
        for source_id in _view_source_ids(view):
            self.get_source(source_id)
        next_id = self._next_artifact_ids.get(prefix, 1)
        artifact_id: ArtifactId = f"{prefix}{next_id}"
        self._next_artifact_ids[prefix] = next_id + 1
        artifact = ArtifactSpec(id=artifact_id, label=label, view=view)
        self._artifacts[artifact_id] = artifact
        return artifact

    def get_artifact(self, artifact_id: str) -> ArtifactSpec:
        """Return a previously stored chart, map, or graph artifact definition."""
        try:
            return self._artifacts[artifact_id]
        except KeyError:
            raise KeyError(f"No artifact with id {artifact_id}") from None


def _view_source_ids(view: ViewDef) -> tuple[str, ...]:
    if hasattr(view, "source"):
        return (view.source,)
    if hasattr(view, "sources"):
        return tuple(view.sources)
    return ()


def render_parameterized_query(query_template: str, selection: dict[ParameterId, SelectionValue]) -> str:
    """Render a parameterized-source query template with validated scalar values."""
    for name, value in selection.items():
        if isinstance(value, bool):
            raise ValueError(f"{name} must not be boolean")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    return _JINJA_ENV.from_string(query_template).render(**selection)
