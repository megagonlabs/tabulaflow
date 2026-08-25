"""Resolve output specifications into display-ready artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

import pandas as pd

import tabulaflow.output.graphs as graphs
import tabulaflow.output.maps as maps
from tabulaflow.output.specs import (
    OutputSpec,
    ArtifactSpecError,
    ArtifactId,
    ArtifactSpec,
    ChartArtifactSpec,
    FixedResultSource,
    GraphArtifactSpec,
    MapArtifactSpec,
    ParameterId,
    ParameterizedSource,
    Selection,
    SourceId,
    SourceSpec,
    TableArtifactSpec,
    artifact_source_ids,
    validate_parameter_value,
)
from tabulaflow.core.results import GraphResult
from tabulaflow.output.charts import validate_chart_spec
from tabulaflow.output.store import OutputStore, ResultPayload, SourceNotApplicable, SourceResolutionError

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
    status: Literal["error", "not_applicable", "no_result"] = "error"


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
        """Resolve an output under one active selection.

        Explicit values override output defaults. Structural selection and
        reference errors raise ``OutputResolutionError``; expected source or
        artifact failures become ``UnavailableArtifact`` entries. Each source
        is resolved at most once per call.

        Args:
            output: Declarative output to resolve.
            selection: Optional parameter overrides.

        Returns:
            Display-ready artifacts and their normalized selection.
        """
        active_selection = _normalize_selection(output, selection)
        sources = {source.id: source for source in output.sources}
        source_outcomes: dict[SourceId, ResultPayload | SourceNotApplicable | SourceResolutionError] = {}
        artifacts: list[ResolvedArtifact] = []
        for artifact in output.artifacts:
            try:
                payload_by_source: dict[SourceId, ResultPayload] = {}
                for source_id in artifact_source_ids(artifact):
                    source = sources.get(source_id)
                    if source is None:
                        raise OutputResolutionError(f"artifact {artifact.id!r} references unknown source {source_id!r}")
                    if source_id not in source_outcomes:
                        try:
                            source_outcomes[source_id] = await self._resolve_source(source, active_selection)
                        except (SourceNotApplicable, SourceResolutionError) as exc:
                            source_outcomes[source_id] = exc
                    outcome = source_outcomes[source_id]
                    if isinstance(outcome, Exception):
                        raise outcome
                    payload_by_source[source_id] = outcome
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
            except (ArtifactSpecError, SourceResolutionError) as exc:
                artifacts.append(UnavailableArtifact(artifact_id=artifact.id, label=artifact.label, reason=str(exc)))
        return ResolvedOutput(selection=active_selection, artifacts=artifacts)

    async def _resolve_source(
        self,
        source: SourceSpec,
        selection: Mapping[ParameterId, object],
    ) -> ResultPayload:
        if isinstance(source, FixedResultSource):
            return await self._output_store.get_payload(source.result_id)
        if isinstance(source, ParameterizedSource):
            return await self._output_store.resolve_source(source.id, selection)
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
                status="no_result",
            )
        return ResolvedTableArtifact(
            artifact_id=artifact.id,
            label=artifact.label,
            source_id=artifact.source_id,
            payload=payload,
        )
    if isinstance(artifact, ChartArtifactSpec):
        unavailable = _no_result_if_missing_dataframe(artifact, payload_by_source)
        if unavailable is not None:
            return unavailable
        payload = payload_by_source[artifact.source_id]
        assert payload.df is not None
        validate_chart_spec(artifact.spec, {artifact.source_id: payload.df})
        return ResolvedChartArtifact(
            artifact_id=artifact.id,
            label=artifact.label,
            source_id=artifact.source_id,
            payload=payload,
            spec=artifact.spec,
        )
    if isinstance(artifact, MapArtifactSpec):
        unavailable = _no_result_if_missing_dataframe(artifact, payload_by_source)
        if unavailable is not None:
            return unavailable
        parsed_map = maps.parse_map_spec(artifact.spec)
        _validate_artifact_source_ids(artifact.id, artifact.source_ids, maps.referenced_source_ids(parsed_map))
        sources = _dataframes_by_source(payload_by_source)
        return ResolvedMapArtifact(
            artifact_id=artifact.id,
            label=artifact.label,
            spec=maps.normalize_map_spec(parsed_map, sources),
            payload_by_source=payload_by_source,
        )
    if isinstance(artifact, GraphArtifactSpec):
        unavailable = _no_result_if_missing_dataframe(artifact, payload_by_source)
        if unavailable is not None:
            return unavailable
        parsed_graph = graphs.parse_graph_spec(artifact.spec)
        _validate_artifact_source_ids(artifact.id, artifact.source_ids, graphs.referenced_source_ids(parsed_graph))
        sources = _dataframes_by_source(payload_by_source)
        normalized = graphs.normalize_graph_spec(parsed_graph, sources)
        graph = graphs.materialize_graph_result(normalized, sources)
        graphs.validate_graph_size(graphs.graph_size(graph))
        layout = normalized.get("layout")
        return ResolvedGraphArtifact(
            artifact_id=artifact.id,
            label=artifact.label,
            graph=graph,
            layout=layout if layout in {"force", "layered", "tree"} else "force",
        )
    raise TypeError(f"unsupported artifact {type(artifact).__name__}")


def _validate_artifact_source_ids(artifact_id: str, declared: list[SourceId], referenced: list[SourceId]) -> None:
    if set(declared) != set(referenced):
        raise OutputResolutionError(
            f"artifact {artifact_id!r} source_ids {declared!r} do not match spec source_ids {referenced!r}"
        )


def _dataframes_by_source(payload_by_source: Mapping[SourceId, ResultPayload]) -> dict[SourceId, pd.DataFrame]:
    return {source_id: payload.df for source_id, payload in payload_by_source.items() if payload.df is not None}


def _no_result_if_missing_dataframe(
    artifact: ArtifactSpec,
    payload_by_source: Mapping[SourceId, ResultPayload],
) -> UnavailableArtifact | None:
    if all(payload.df is not None for payload in payload_by_source.values()):
        return None
    return UnavailableArtifact(
        artifact_id=artifact.id,
        label=artifact.label,
        reason="Source returned no result set",
        status="no_result",
    )


def _no_displayable_data_reason(payload: ResultPayload) -> str:
    affected_rows = payload.metadata.affected_rows
    if affected_rows is None:
        return "Statement executed successfully but returned no displayable data"
    row_word = "row" if affected_rows == 1 else "rows"
    return f"Statement executed successfully, affected {affected_rows:,} {row_word}, and returned no displayable data"
