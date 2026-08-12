"""Runtime storage and resolution for clean output specs."""

from __future__ import annotations

from collections.abc import Mapping
import math

from pydantic import BaseModel, Field

from tabulaflow.core.outputs import (
    OutputSpec,
    ArtifactId,
    ArtifactSpec,
    ChartView,
    ChoiceParameter,
    FixedResultSource,
    GraphViewSpec,
    MapView,
    NumberParameter,
    ParameterDef,
    ParameterId,
    ParameterizedSource,
    ResultMetadata,
    SelectionValue,
    SourceId,
    SourceDef,
    TableView,
    ViewDef,
)
from tabulaflow.toolhub.output_store import OutputStore


class OutputResolutionError(ValueError):
    """An output cannot resolve for the requested selection."""


class ResolvedArtifact(BaseModel):
    """An artifact with the result records needed to render its view."""

    artifact_id: ArtifactId
    label: str | None = None
    view: ViewDef
    metadata_by_source: dict[SourceId, ResultMetadata]


class ResolvedOutput(BaseModel):
    """An output spec resolved under one active selection."""

    selection: dict[ParameterId, SelectionValue]
    artifacts: list[ResolvedArtifact] = Field(default_factory=list)


class OutputResolver:
    """Resolve an OutputSpec under a selection to materialized result records."""

    def __init__(self, output_store: OutputStore) -> None:
        self._output_store = output_store

    async def resolve(
        self,
        output: OutputSpec,
        selection: Mapping[ParameterId, object] | None = None,
    ) -> ResolvedOutput:
        active_selection = _normalize_selection(output, selection)
        parameters = {parameter.id: parameter for parameter in output.parameters}
        sources = {source.id: source for source in output.sources}
        resolved_sources: dict[SourceId, ResultMetadata] = {}
        artifacts: list[ResolvedArtifact] = []
        for artifact in output.artifacts:
            source_results: dict[SourceId, ResultMetadata] = {}
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
    ) -> ResultMetadata:
        if isinstance(source, FixedResultSource):
            return await self._output_store.get_metadata(source.result_id)
        if isinstance(source, ParameterizedSource):
            try:
                return await self._output_store.resolve_source(source.id, _project_selection(source, parameters, selection))
            except KeyError as exc:
                raise OutputResolutionError(str(exc)) from None
        raise TypeError(f"unsupported source {type(source).__name__}")


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


def _resolved_artifact(artifact: ArtifactSpec, metadata_by_source: dict[SourceId, ResultMetadata]) -> ResolvedArtifact:
    return ResolvedArtifact(
        artifact_id=artifact.id,
        label=artifact.label,
        view=artifact.view,
        metadata_by_source=metadata_by_source,
    )


def _project_selection(
    source: ParameterizedSource,
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
        if not math.isfinite(number):
            raise OutputResolutionError(f"{parameter.id} must be finite")
        if not parameter.min <= number <= parameter.max:
            raise OutputResolutionError(f"{parameter.id}={number:g} is outside range")
        return value
    raise TypeError(f"unsupported parameter {type(parameter).__name__}")


def _view_source_ids(view: ViewDef) -> tuple[SourceId, ...]:
    if isinstance(view, TableView | ChartView):
        return (view.source,)
    if isinstance(view, MapView | GraphViewSpec):
        return tuple(view.sources)
    raise TypeError(f"unsupported view {type(view).__name__}")
