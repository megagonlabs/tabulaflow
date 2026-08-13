"""Runtime storage and resolution for clean output specs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypeAlias

from tabulaflow.core.outputs import (
    OutputSpec,
    ArtifactId,
    ArtifactSpec,
    ChartView,
    FixedResultSource,
    GraphViewSpec,
    MapView,
    ParameterDef,
    ParameterId,
    ParameterizedSource,
    Selection,
    SelectionValue,
    SourceId,
    SourceDef,
    TableView,
    ViewDef,
    validate_parameter_value,
)
from tabulaflow.toolhub.output_store import OutputStore, ResultPayload


class OutputResolutionError(ValueError):
    """An output cannot resolve for the requested selection."""


@dataclass(frozen=True)
class AvailableArtifact:
    """An artifact with payloads needed to render its view."""

    artifact_id: ArtifactId
    view: ViewDef
    label: str | None = None
    payload_by_source: dict[SourceId, ResultPayload] = field(default_factory=dict)


@dataclass(frozen=True)
class UnavailableArtifact:
    """An artifact that cannot render for the active selection."""

    artifact_id: ArtifactId
    reason: str = "unavailable"
    label: str | None = None


ResolvedArtifact: TypeAlias = AvailableArtifact | UnavailableArtifact


@dataclass(frozen=True)
class ResolvedOutput:
    """An output spec resolved under one active selection."""

    selection: Selection
    artifacts: list[ResolvedArtifact] = field(default_factory=list)


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
        resolved_sources: dict[SourceId, ResultPayload] = {}
        artifacts: list[ResolvedArtifact] = []
        for artifact in output.artifacts:
            try:
                payload_by_source: dict[SourceId, ResultPayload] = {}
                for source_id in _view_source_ids(artifact.view):
                    source = sources.get(source_id)
                    if source is None:
                        raise OutputResolutionError(f"artifact {artifact.id!r} references unknown source {source_id!r}")
                    if source_id not in resolved_sources:
                        resolved_sources[source_id] = await self._resolve_source(source, parameters, active_selection)
                    payload_by_source[source_id] = resolved_sources[source_id]
            except OutputResolutionError:
                raise
            except (KeyError, ValueError) as exc:
                artifacts.append(UnavailableArtifact(artifact_id=artifact.id, label=artifact.label, reason=str(exc)))
            else:
                artifacts.append(_resolved_artifact(artifact, payload_by_source))
        return ResolvedOutput(selection=active_selection, artifacts=artifacts)

    async def _resolve_source(
        self,
        source: SourceDef,
        parameters: Mapping[ParameterId, ParameterDef],
        selection: Mapping[ParameterId, SelectionValue],
    ) -> ResultPayload:
        if isinstance(source, FixedResultSource):
            return await self._output_store.get_payload(source.result_id)
        if isinstance(source, ParameterizedSource):
            return await self._output_store.resolve_source(source.id, _project_selection(source, parameters, selection))
        raise TypeError(f"unsupported source {type(source).__name__}")


def _normalize_selection(
    output: OutputSpec,
    selection: Mapping[ParameterId, object] | None,
) -> Selection:
    parameters = {parameter.id: parameter for parameter in output.parameters}
    active: dict[ParameterId, object] = dict(output.default_selection)
    if selection is not None:
        active.update(selection)
    for parameter_id in active:
        if parameter_id not in parameters:
            raise OutputResolutionError(f"selection references unknown parameter {parameter_id!r}")
    try:
        return {parameter.id: validate_parameter_value(parameter, active[parameter.id]) for parameter in output.parameters}
    except ValueError as exc:
        raise OutputResolutionError(str(exc)) from None


def _resolved_artifact(artifact: ArtifactSpec, payload_by_source: dict[SourceId, ResultPayload]) -> AvailableArtifact:
    return AvailableArtifact(
        artifact_id=artifact.id,
        label=artifact.label,
        view=artifact.view,
        payload_by_source=payload_by_source,
    )


def _project_selection(
    source: ParameterizedSource,
    parameters: Mapping[ParameterId, ParameterDef],
    selection: Mapping[ParameterId, object],
) -> Selection:
    projected: Selection = {}
    for parameter_id in source.parameter_ids:
        parameter = parameters.get(parameter_id)
        if parameter is None:
            raise OutputResolutionError(f"source {source.id!r} references unknown parameter {parameter_id!r}")
        if parameter_id not in selection:
            raise OutputResolutionError(f"missing selection for {parameter_id!r}")
        try:
            projected[parameter_id] = validate_parameter_value(parameter, selection[parameter_id])
        except ValueError as exc:
            raise OutputResolutionError(str(exc)) from None
    return projected


def _view_source_ids(view: ViewDef) -> tuple[SourceId, ...]:
    if isinstance(view, TableView | ChartView):
        return (view.source,)
    if isinstance(view, MapView | GraphViewSpec):
        return tuple(view.sources)
    raise TypeError(f"unsupported view {type(view).__name__}")
