"""Session-backed resolution of logical chat artifacts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING
from tabulaflow.chat.result import (
    AnswerControl,
    Artifact,
    ArtifactPlaceholder,
    ChartArtifact,
    ChatResult,
    ChoiceControl,
    GraphArtifact,
    MapArtifact,
    ResolvedArtifact,
    ResolvedChartArtifact,
    ResolvedGraphArtifact,
    ResolvedMapArtifact,
    ResolvedTableArtifact,
    SelectionValue,
    TableArtifact,
)
from tabulaflow.toolhub import GraphArtifact as StoredGraphArtifact
from tabulaflow.toolhub import MapArtifact as StoredMapArtifact
from tabulaflow.toolhub import QueryHistory, ResolvedQueryRecord
from tabulaflow.toolhub.query_history import SourceNotApplicable

if TYPE_CHECKING:
    import pandas as pd


class ArtifactResolver:
    """Resolve a logical ``ChatResult`` against session artifact storage."""

    def __init__(self, query_history: QueryHistory) -> None:
        self._query_history = query_history

    async def resolve(
        self,
        result: ChatResult,
        selection: Mapping[str, SelectionValue] | None = None,
    ) -> list[ResolvedArtifact]:
        """Resolve ``result`` under ``selection``; omit selection for the default."""
        active_selection = self._default_selection(result) if selection is None else dict(selection)
        controls = result.panel.controls if result.panel is not None else ()
        return await self._resolve_many(result.artifacts, active_selection, controls=controls)

    @staticmethod
    def _default_selection(result: ChatResult) -> dict[str, SelectionValue]:
        return dict(result.panel.default_selection) if result.panel is not None else {}

    async def _resolve_many(
        self,
        artifacts: Sequence[Artifact],
        selection: Mapping[str, SelectionValue],
        *,
        controls: Sequence[AnswerControl] = (),
    ) -> list[ResolvedArtifact]:
        """Resolve logical artifacts under ``selection``."""
        resolved: list[ResolvedArtifact] = []
        for artifact in artifacts:
            item: ResolvedArtifact | None
            if isinstance(artifact, TableArtifact):
                item = await self._resolve_table(artifact, selection, controls)
            elif isinstance(artifact, ChartArtifact):
                item = await self._resolve_chart(artifact, selection, controls)
            elif isinstance(artifact, MapArtifact):
                item = await self._resolve_map(artifact)
            elif isinstance(artifact, GraphArtifact):
                item = await self._resolve_graph(artifact)
            else:
                item = None
            if item is not None:
                resolved.append(item)
        return resolved

    async def _resolve_table(
        self,
        artifact: TableArtifact,
        selection: Mapping[str, SelectionValue],
        controls: Sequence[AnswerControl],
    ) -> ResolvedTableArtifact | ArtifactPlaceholder | None:
        resolution = await self._resolve_query_record(artifact.source_id, selection)
        if isinstance(resolution, SourceNotApplicable):
            return ArtifactPlaceholder(
                label=artifact.label,
                message=self._not_applicable_message(artifact.source_id, selection, controls, resolution.reason),
            )
        if resolution is None:
            return None
        return self._table_from_query_record(resolution, artifact.label)

    async def _resolve_chart(
        self,
        artifact: ChartArtifact,
        selection: Mapping[str, SelectionValue],
        controls: Sequence[AnswerControl],
    ) -> ResolvedChartArtifact | ArtifactPlaceholder | None:
        resolution = await self._resolve_query_record(artifact.source_id, selection)
        if isinstance(resolution, SourceNotApplicable):
            return ArtifactPlaceholder(
                label=artifact.label,
                message=self._not_applicable_message(artifact.source_id, selection, controls, resolution.reason),
            )
        if resolution is None:
            return None
        return ResolvedChartArtifact(
            chart_id=artifact.chart_id,
            label=artifact.label,
            chart_spec=artifact.chart_spec,
            record_id=resolution.record_id,
            query=resolution.query,
            df=resolution.df,
            query_lexer=resolution.query_lexer,
        )

    async def _resolve_map(self, artifact: MapArtifact) -> ResolvedMapArtifact | None:
        try:
            stored = self._query_history.get_map(artifact.map_id)
        except (KeyError, ValueError):
            return None
        return await self._map_from_stored(stored, artifact.label)

    async def _resolve_graph(self, artifact: GraphArtifact) -> ResolvedGraphArtifact | None:
        try:
            stored = self._query_history.get_graph(artifact.graph_id)
        except (KeyError, ValueError):
            return None
        return self._graph_from_stored(stored, artifact.label)

    async def _resolve_query_record(
        self,
        source_id: str,
        selection: Mapping[str, SelectionValue],
    ) -> ResolvedQueryRecord | SourceNotApplicable | None:
        try:
            return await self._query_history.resolve_query_record(source_id, selection)
        except (KeyError, ValueError):
            return None

    def _not_applicable_message(
        self,
        source_id: str,
        selection: Mapping[str, SelectionValue],
        controls: Sequence[AnswerControl],
        fallback: str,
    ) -> str:
        if not source_id.startswith("QS") or not controls:
            return fallback
        try:
            family = self._query_history.get_family(source_id)
        except (KeyError, ValueError):
            return fallback
        by_id = {control.id: control for control in controls if isinstance(control, ChoiceControl)}
        parts: list[str] = []
        for name, choices in family.dimensions.items():
            if name not in selection or str(selection[name]) in choices:
                continue
            control = by_id.get(name)
            if control is None:
                return fallback
            covered = [choice.label for choice in control.choices if choice.id in choices]
            if not covered:
                return fallback
            parts.append(f"{control.label} = {' or '.join(covered)}")
        return "only applies when " + "; ".join(parts) if parts else fallback

    @staticmethod
    def _table_from_query_record(query_record: ResolvedQueryRecord, label: str | None) -> ResolvedTableArtifact:
        return ResolvedTableArtifact(
            record_id=query_record.record_id,
            label=label,
            query=query_record.query,
            df=query_record.df,
            graph=query_record.graph,
            query_lexer=query_record.query_lexer,
        )

    async def _map_from_stored(self, stored: StoredMapArtifact, label: str | None) -> ResolvedMapArtifact:
        spec = stored.map_spec
        layers = spec.get("layers") or []
        source_ids: list[str] = []
        for layer in layers:
            sid = layer.get("source") if isinstance(layer, dict) else None
            if sid and sid not in source_ids:
                source_ids.append(sid)
        sources: dict[str, pd.DataFrame] = {}
        for sid in source_ids:
            try:
                payload = await self._query_history.get_query_record_payload(sid)
            except (KeyError, ValueError):
                continue
            if payload.df is not None:
                sources[sid] = payload.df
        return ResolvedMapArtifact(map_id=stored.map_id, label=label, map_spec=spec, sources=sources)

    @staticmethod
    def _graph_from_stored(stored: StoredGraphArtifact, label: str | None) -> ResolvedGraphArtifact:
        return ResolvedGraphArtifact(
            graph_id=stored.graph_id,
            label=label,
            graph=stored.graph,
            layout=stored.layout,
        )


def artifacts_from_refs(refs: Iterable[tuple[str, str | None]], query_history: QueryHistory) -> list[Artifact]:
    """Convert showable ids to logical chat artifacts, preserving citation order."""
    artifacts: list[Artifact] = []
    for ref_id, label in refs:
        artifact = artifact_from_ref(ref_id, label, query_history)
        if artifact is not None:
            artifacts.append(artifact)
    return artifacts


def artifact_from_ref(ref_id: str, label: str | None, query_history: QueryHistory) -> Artifact | None:
    """Convert one showable id to a logical chat artifact."""
    if ref_id.startswith("CHART"):
        try:
            chart = query_history.get_chart(ref_id)
        except (KeyError, ValueError):
            return None
        return ChartArtifact(
            chart_id=chart.chart_id, label=label, source_id=chart.source_id, chart_spec=chart.chart_spec
        )
    if ref_id.startswith("MAP"):
        try:
            stored_map = query_history.get_map(ref_id)
        except (KeyError, ValueError):
            return None
        return MapArtifact(map_id=stored_map.map_id, label=label)
    if ref_id.startswith("GRAPH"):
        try:
            graph = query_history.get_graph(ref_id)
        except (KeyError, ValueError):
            return None
        return GraphArtifact(graph_id=graph.graph_id, label=label)
    if ref_id.startswith("QS"):
        try:
            query_history.get_family(ref_id)
        except (KeyError, ValueError):
            return None
        return TableArtifact(label=label, source_id=ref_id)
    if ref_id.startswith("Q"):
        return TableArtifact(label=label, source_id=ref_id)
    return None
