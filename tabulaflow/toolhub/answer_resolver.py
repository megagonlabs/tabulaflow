"""Runtime resolution of clean output answer specs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from pydantic import BaseModel, Field

from tabulaflow.core.outputs import (
    AnswerSpec,
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
from tabulaflow.toolhub.query_history import QueryHistory, TabularResult


class AnswerResolutionError(ValueError):
    """An answer cannot resolve for the requested selection."""


class ResolvedArtifact(BaseModel):
    """An artifact with the result records needed to render its view."""

    artifact_id: ArtifactId
    label: str | None = None
    view: ViewDef
    results_by_source: dict[SourceId, ResultRecord]


class ResolvedAnswer(BaseModel):
    """A resolved answer spec under one active selection."""

    selection: dict[ParameterId, SelectionValue]
    artifacts: list[ResolvedArtifact] = Field(default_factory=list)


class ResultStore(Protocol):
    """Runtime store for materialized result metadata."""

    async def get_record(self, result_id: ResultId) -> ResultRecord:
        """Return metadata for a materialized result."""


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


class AnswerResolver:
    """Resolve an AnswerSpec under a selection to materialized result records."""

    def __init__(self, result_store: ResultStore) -> None:
        self._result_store = result_store

    async def resolve(
        self,
        answer: AnswerSpec,
        selection: Mapping[ParameterId, object] | None = None,
    ) -> ResolvedAnswer:
        active_selection = _active_selection(answer, selection)
        parameters = {parameter.id: parameter for parameter in answer.parameters}
        sources = {source.id: source for source in answer.sources}
        resolved_sources: dict[SourceId, ResultRecord] = {}
        artifacts: list[ResolvedArtifact] = []
        for artifact in answer.artifacts:
            source_results: dict[SourceId, ResultRecord] = {}
            for source_id in _view_source_ids(artifact.view):
                source = sources.get(source_id)
                if source is None:
                    raise AnswerResolutionError(f"artifact {artifact.id!r} references unknown source {source_id!r}")
                if source_id not in resolved_sources:
                    resolved_sources[source_id] = await self._resolve_source(source, parameters, active_selection)
                source_results[source_id] = resolved_sources[source_id]
            artifacts.append(_resolved_artifact(artifact, source_results))
        return ResolvedAnswer(selection=active_selection, artifacts=artifacts)

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
            raise AnswerResolutionError(f"source {source.id!r} has no result for selection {key}")
        if isinstance(plan, QueryPlan):
            raise AnswerResolutionError("query source materialization is not implemented")
        raise TypeError(f"unsupported source plan {type(plan).__name__}")


def _active_selection(
    answer: AnswerSpec,
    selection: Mapping[ParameterId, object] | None,
) -> dict[ParameterId, SelectionValue]:
    parameters = {parameter.id: parameter for parameter in answer.parameters}
    active: dict[ParameterId, object] = {
        parameter.id: _parameter_default(parameter) for parameter in answer.parameters
    }
    active.update(answer.default_selection)
    if selection is not None:
        active.update(selection)
    for parameter_id in active:
        if parameter_id not in parameters:
            raise AnswerResolutionError(f"selection references unknown parameter {parameter_id!r}")
    return {parameter.id: _validate_parameter_value(parameter, active[parameter.id]) for parameter in answer.parameters}


def _parameter_default(parameter: ParameterDef) -> SelectionValue:
    if isinstance(parameter, ChoiceParameter):
        return parameter.default if parameter.default is not None else parameter.choices[0].id
    if isinstance(parameter, NumberParameter):
        return parameter.default
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")


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
            raise AnswerResolutionError(f"source {source.id!r} references unknown parameter {parameter_id!r}")
        if parameter_id not in selection:
            raise AnswerResolutionError(f"missing selection for {parameter_id!r}")
        projected[parameter_id] = _validate_parameter_value(parameter, selection[parameter_id])
    return projected


def _validate_parameter_value(parameter: ParameterDef, value: object) -> SelectionValue:
    if isinstance(parameter, ChoiceParameter):
        choice = str(value)
        if choice not in {option.id for option in parameter.choices}:
            raise AnswerResolutionError(f"{parameter.id}={choice!r} is not a valid choice")
        return choice
    if isinstance(parameter, NumberParameter):
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise AnswerResolutionError(f"{parameter.id} must be numeric")
        number = float(value)
        if not parameter.min <= number <= parameter.max:
            raise AnswerResolutionError(f"{parameter.id}={number:g} is outside range")
        return value
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")


def _view_source_ids(view: ViewDef) -> tuple[SourceId, ...]:
    if isinstance(view, TableView | ChartView):
        return (view.source,)
    if isinstance(view, MapView | GraphArtifactView):
        return tuple(view.sources)
    raise TypeError(f"unsupported view {type(view).__name__}")
