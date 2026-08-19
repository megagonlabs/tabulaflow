"""Resolve output specifications into display-ready artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

import pandas as pd

from tabulaflow.output.specs import (
    OutputSpec,
    ArtifactId,
    ArtifactSpec,
    ChartArtifactSpec,
    FixedResultSource,
    GraphArtifactSpec,
    MapArtifactSpec,
    ParameterId,
    ParameterSpec,
    ParameterizedSource,
    Selection,
    SelectionValue,
    SourceId,
    SourceSpec,
    TableArtifactSpec,
    artifact_source_ids,
    validate_parameter_value,
)
from tabulaflow.core import GraphResult
from tabulaflow.output.charts import validate_chart_spec
from tabulaflow.output.store import OutputStore, ResultPayload, SourceNotApplicable
from tabulaflow.output.graphs import (
    graph_result_size,
    materialize_graph_result,
    normalize_graph_spec,
    validate_graph_size,
)
from tabulaflow.output.maps import normalize_map_spec

__all__ = [
    "OutputResolutionError",
    "OutputResolver",
    "ResolvedArtifact",
    "ResolvedChartArtifact",
    "ResolvedGraphArtifact",
    "ResolvedMapArtifact",
    "ResolvedOutput",
    "ResolvedTableArtifact",
    "UnavailableArtifact",
]


class OutputResolutionError(ValueError):
    """An output cannot resolve for the requested selection."""


@dataclass(frozen=True)
class ResolvedTableArtifact:
    """Resolved table artifact with its source payload attached."""

    artifact_id: ArtifactId
    source_id: SourceId
    payload: ResultPayload
    label: str | None = None


@dataclass(frozen=True)
class ResolvedChartArtifact:
    """Resolved chart artifact with its source payload and chart spec attached."""

    artifact_id: ArtifactId
    source_id: SourceId
    payload: ResultPayload
    spec: dict[str, object]
    label: str | None = None


@dataclass(frozen=True)
class ResolvedMapArtifact:
    """Resolved map artifact with all source payloads attached."""

    artifact_id: ArtifactId
    spec: dict[str, object]
    payload_by_source: Mapping[SourceId, ResultPayload]
    label: str | None = None


@dataclass(frozen=True)
class ResolvedGraphArtifact:
    """Resolved graph artifact with its materialized graph attached."""

    artifact_id: ArtifactId
    graph: GraphResult
    layout: str = "force"
    label: str | None = None


@dataclass(frozen=True)
class UnavailableArtifact:
    """An artifact that cannot render for the active selection."""

    artifact_id: ArtifactId
    reason: str = "unavailable"
    label: str | None = None
    status: Literal["error", "not_applicable", "no_data"] = "error"


ResolvedArtifact: TypeAlias = (
    ResolvedTableArtifact | ResolvedChartArtifact | ResolvedMapArtifact | ResolvedGraphArtifact | UnavailableArtifact
)


@dataclass(frozen=True)
class ResolvedOutput:
    """An output spec resolved under one active selection."""

    selection: Selection
    artifacts: list[ResolvedArtifact] = field(default_factory=list)


class OutputResolver:
    """Resolve an OutputSpec under a selection to display-ready artifacts."""

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
                for source_id in artifact_source_ids(artifact):
                    source = sources.get(source_id)
                    if source is None:
                        raise OutputResolutionError(f"artifact {artifact.id!r} references unknown source {source_id!r}")
                    if source_id not in resolved_sources:
                        resolved_sources[source_id] = await self._resolve_source(source, parameters, active_selection)
                    payload_by_source[source_id] = resolved_sources[source_id]
                artifacts.append(_resolved_artifact(artifact, payload_by_source))
            except OutputResolutionError:
                raise
            except SourceNotApplicable as exc:
                artifacts.append(
                    UnavailableArtifact(
                        artifact_id=artifact.id,
                        label=artifact.label,
                        reason=str(exc),
                        status="not_applicable",
                    )
                )
            except (KeyError, ValueError) as exc:
                artifacts.append(UnavailableArtifact(artifact_id=artifact.id, label=artifact.label, reason=str(exc)))
        return ResolvedOutput(selection=active_selection, artifacts=artifacts)

    async def _resolve_source(
        self,
        source: SourceSpec,
        parameters: Mapping[ParameterId, ParameterSpec],
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
        return {
            parameter.id: validate_parameter_value(parameter, active[parameter.id]) for parameter in output.parameters
        }
    except ValueError as exc:
        raise OutputResolutionError(str(exc)) from None


def _resolved_artifact(artifact: ArtifactSpec, payload_by_source: dict[SourceId, ResultPayload]) -> ResolvedArtifact:
    if isinstance(artifact, TableArtifactSpec):
        payload = payload_by_source[artifact.source_id]
        if payload.df is None and payload.graph is None:
            return UnavailableArtifact(
                artifact_id=artifact.id,
                label=artifact.label,
                reason=_no_displayable_data_reason(payload),
                status="no_data",
            )
        return ResolvedTableArtifact(
            artifact_id=artifact.id,
            label=artifact.label,
            source_id=artifact.source_id,
            payload=payload,
        )
    if isinstance(artifact, ChartArtifactSpec):
        payload = payload_by_source[artifact.source_id]
        if payload.df is None:
            return UnavailableArtifact(
                artifact_id=artifact.id,
                label=artifact.label,
                reason="Source returned no tabular data",
                status="no_data",
            )
        return ResolvedChartArtifact(
            artifact_id=artifact.id,
            label=artifact.label,
            source_id=artifact.source_id,
            payload=payload,
            spec=validate_chart_spec(artifact.spec, {artifact.source_id: payload.df}),
        )
    if isinstance(artifact, MapArtifactSpec):
        sources = _dataframes_by_source(payload_by_source)
        return ResolvedMapArtifact(
            artifact_id=artifact.id,
            label=artifact.label,
            spec=normalize_map_spec(artifact.spec, sources),
            payload_by_source=payload_by_source,
        )
    if isinstance(artifact, GraphArtifactSpec):
        sources = _dataframes_by_source(payload_by_source)
        normalized = normalize_graph_spec(artifact.spec, sources)
        graph = materialize_graph_result(normalized, sources)
        validate_graph_size(graph_result_size(graph))
        layout = normalized.get("layout")
        return ResolvedGraphArtifact(
            artifact_id=artifact.id,
            label=artifact.label,
            graph=graph,
            layout=layout if layout in {"force", "layered", "tree"} else "force",
        )
    raise TypeError(f"unsupported artifact {type(artifact).__name__}")


def _dataframes_by_source(payload_by_source: Mapping[SourceId, ResultPayload]) -> dict[SourceId, pd.DataFrame]:
    sources = {}
    for source_id, payload in payload_by_source.items():
        if payload.df is None:
            raise ValueError(f"source {source_id!r} returned no data")
        sources[source_id] = payload.df
    return sources


def _no_displayable_data_reason(payload: ResultPayload) -> str:
    affected_rows = payload.metadata.affected_rows
    if affected_rows is None:
        return "Statement executed successfully but returned no displayable data"
    row_word = "row" if affected_rows == 1 else "rows"
    return f"Statement executed successfully, affected {affected_rows:,} {row_word}, and returned no displayable data"


def _project_selection(
    source: ParameterizedSource,
    parameters: Mapping[ParameterId, ParameterSpec],
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
