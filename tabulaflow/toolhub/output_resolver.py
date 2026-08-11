"""Runtime resolution of clean output output specs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from tabulaflow.core.outputs import (
    OutputSpec,
    ArtifactId,
    ArtifactSpec,
    ChartView,
    ChoiceParameter,
    ConstantResultPlan,
    GraphArtifactView,
    MapView,
    NumberParameter,
    ParameterDef,
    ParameterId,
    QueryPlan,
    ResultId,
    ResultLookupPlan,
    ResultRecord,
    SelectionValue,
    SourceId,
    SourceDef,
    TableView,
    ViewDef,
    canonical_selection_key,
)
from tabulaflow.core.dataframe import _deserialize_dataframe, _serialize_dataframe
from tabulaflow.core.types import GraphView
from tabulaflow.toolhub.query_history import QueryHistory, TabularResult


class OutputResolutionError(ValueError):
    """An output cannot resolve for the requested selection."""


class ResolvedArtifact(BaseModel):
    """An artifact with the result records needed to render its view."""

    artifact_id: ArtifactId
    label: str | None = None
    view: ViewDef
    results_by_source: dict[SourceId, ResultRecord]


class ResolvedOutput(BaseModel):
    """An output spec resolved under one active selection."""

    selection: dict[ParameterId, SelectionValue]
    artifacts: list[ResolvedArtifact] = Field(default_factory=list)


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


class ResultStore(Protocol):
    """Runtime store for materialized result metadata."""

    async def get_record(self, result_id: ResultId) -> ResultRecord:
        """Return metadata for a materialized result."""

    async def get_payload(self, result_id: ResultId) -> ResultPayload:
        """Return runtime payload for a materialized result."""


class QueryHistoryResultStore:
    """ResultStore adapter over the current query history runtime."""

    def __init__(self, query_history: QueryHistory) -> None:
        self._query_history = query_history

    async def get_record(self, result_id: ResultId) -> ResultRecord:
        record = await self._query_history.get(result_id)
        row_count = None
        columns = None
        if isinstance(record.outcome, TabularResult):
            row_count = record.outcome.row_count
            columns = list(record.outcome.columns)
        return ResultRecord(
            id=record.record_id,
            db_alias=record.db_alias,
            query=record.query,
            connector_type=record.connector_type,
            parameter_values=record.parameter_values,
            row_count=row_count,
            columns=columns,
        )

    async def get_payload(self, result_id: ResultId) -> ResultPayload:
        record = await self.get_record(result_id)
        payload = await self._query_history.get_query_record_payload(result_id)
        return ResultPayload(record=record, df=payload.df, graph=payload.graph)


class OutputResolver:
    """Resolve an OutputSpec under a selection to materialized result records."""

    def __init__(self, result_store: ResultStore) -> None:
        self._result_store = result_store

    async def resolve(
        self,
        output: OutputSpec,
        selection: Mapping[ParameterId, object] | None = None,
    ) -> ResolvedOutput:
        active_selection = _normalize_selection(output, selection)
        parameters = {parameter.id: parameter for parameter in output.parameters}
        sources = {source.id: source for source in output.sources}
        resolved_sources: dict[SourceId, ResultRecord] = {}
        artifacts: list[ResolvedArtifact] = []
        for artifact in output.artifacts:
            source_results: dict[SourceId, ResultRecord] = {}
            for source_id in _view_source_ids(artifact.view):
                source = sources.get(source_id)
                if source is None:
                    raise OutputResolutionError(f"artifact {artifact.id!r} references unknown source {source_id!r}")
                if source_id not in resolved_sources:
                    resolved_sources[source_id] = await self._resolve_source(source, parameters, active_selection)
                source_results[source_id] = resolved_sources[source_id]
            artifacts.append(_resolved_artifact(artifact, source_results))
        return ResolvedOutput(selection=active_selection, artifacts=artifacts)

    async def _resolve_source(
        self,
        source: SourceDef,
        parameters: Mapping[ParameterId, ParameterDef],
        selection: Mapping[ParameterId, SelectionValue],
    ) -> ResultRecord:
        plan = source.plan
        if isinstance(plan, ConstantResultPlan):
            return await self._result_store.get_record(plan.result_id)
        if isinstance(plan, ResultLookupPlan):
            key = canonical_selection_key(_project_selection(source, parameters, selection))
            for variant in plan.variants:
                if canonical_selection_key(variant.selection) == key:
                    return await self._result_store.get_record(variant.result_id)
            raise OutputResolutionError(f"source {source.id!r} has no result for selection {key}")
        if isinstance(plan, QueryPlan):
            raise OutputResolutionError("query source materialization is not implemented")
        raise TypeError(f"unsupported source plan {type(plan).__name__}")


def _normalize_selection(
    output: OutputSpec,
    selection: Mapping[ParameterId, object] | None,
) -> dict[ParameterId, SelectionValue]:
    parameters = {parameter.id: parameter for parameter in output.parameters}
    active: dict[ParameterId, object] = dict(output.default_selection)
    if selection is not None:
        active.update(selection)
    for parameter_id in active:
        if parameter_id not in parameters:
            raise OutputResolutionError(f"selection references unknown parameter {parameter_id!r}")
    return {parameter.id: _validate_parameter_value(parameter, active[parameter.id]) for parameter in output.parameters}


def _resolved_artifact(artifact: ArtifactSpec, results_by_source: dict[SourceId, ResultRecord]) -> ResolvedArtifact:
    return ResolvedArtifact(
        artifact_id=artifact.id,
        label=artifact.label,
        view=artifact.view,
        results_by_source=results_by_source,
    )


def _project_selection(
    source: SourceDef,
    parameters: Mapping[ParameterId, ParameterDef],
    selection: Mapping[ParameterId, object],
) -> dict[ParameterId, SelectionValue]:
    projected: dict[ParameterId, SelectionValue] = {}
    for parameter_id in source.parameter_ids:
        parameter = parameters.get(parameter_id)
        if parameter is None:
            raise OutputResolutionError(f"source {source.id!r} references unknown parameter {parameter_id!r}")
        if parameter_id not in selection:
            raise OutputResolutionError(f"missing selection for {parameter_id!r}")
        projected[parameter_id] = _validate_parameter_value(parameter, selection[parameter_id])
    return projected


def _validate_parameter_value(parameter: ParameterDef, value: object) -> SelectionValue:
    if isinstance(parameter, ChoiceParameter):
        choice = str(value)
        if choice not in {option.id for option in parameter.choices}:
            raise OutputResolutionError(f"{parameter.id}={choice!r} is not a valid choice")
        return choice
    if isinstance(parameter, NumberParameter):
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise OutputResolutionError(f"{parameter.id} must be numeric")
        number = float(value)
        if not parameter.min <= number <= parameter.max:
            raise OutputResolutionError(f"{parameter.id}={number:g} is outside range")
        return value
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")


def _view_source_ids(view: ViewDef) -> tuple[SourceId, ...]:
    if isinstance(view, TableView | ChartView):
        return (view.source,)
    if isinstance(view, MapView | GraphArtifactView):
        return tuple(view.sources)
    raise TypeError(f"unsupported view {type(view).__name__}")
