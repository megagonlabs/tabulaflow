"""Session-backed resolution of logical chat artifacts."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING
from tabulaflow.chat.result import (
    AnswerControl,
    ArtifactPlaceholder,
    ChatResult,
    ChoiceControl,
    ResolvedArtifact,
    ResolvedChartArtifact,
    ResolvedGraphArtifact,
    ResolvedMapArtifact,
    ResolvedTableArtifact,
    SelectionValue,
)
from tabulaflow.core.legacy_outputs import ArtifactDef, ChartArtifactDef, GraphArtifactDef, MapArtifactDef, TableArtifactDef
from tabulaflow.toolhub import QueryHistory, ResolvedQueryRecord
from tabulaflow.toolhub.query_history import SourceNotApplicable
from tabulaflow.toolhub.render_graph import GraphSpecError, materialize_graph_view

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
        artifacts: Sequence[ArtifactDef],
        selection: Mapping[str, SelectionValue],
        *,
        controls: Sequence[AnswerControl] = (),
    ) -> list[ResolvedArtifact]:
        """Resolve logical artifacts under ``selection``."""
        resolved = await asyncio.gather(*(self._resolve_one(artifact, selection, controls) for artifact in artifacts))
        return [artifact for artifact in resolved if artifact is not None]

    async def _resolve_one(
        self,
        artifact: ArtifactDef,
        selection: Mapping[str, SelectionValue],
        controls: Sequence[AnswerControl],
    ) -> ResolvedArtifact | None:
        if isinstance(artifact, TableArtifactDef):
            return await self._resolve_table(artifact, selection, controls)
        if isinstance(artifact, ChartArtifactDef):
            return await self._resolve_chart(artifact, selection, controls)
        if isinstance(artifact, MapArtifactDef):
            return await self._resolve_map(artifact)
        if isinstance(artifact, GraphArtifactDef):
            return await self._resolve_graph(artifact, selection, controls)
        return None

    async def _resolve_table(
        self,
        artifact: TableArtifactDef,
        selection: Mapping[str, SelectionValue],
        controls: Sequence[AnswerControl],
    ) -> ResolvedTableArtifact | ArtifactPlaceholder | None:
        payload = await self._source_payload(artifact.source_id, artifact.label, selection, controls)
        if isinstance(payload, (ArtifactPlaceholder, type(None))):
            return payload
        return self._table_from_query_record(payload, artifact.label)

    async def _resolve_chart(
        self,
        artifact: ChartArtifactDef,
        selection: Mapping[str, SelectionValue],
        controls: Sequence[AnswerControl],
    ) -> ResolvedChartArtifact | ArtifactPlaceholder | None:
        payload = await self._source_payload(artifact.source_id, artifact.label, selection, controls)
        if isinstance(payload, (ArtifactPlaceholder, type(None))):
            return payload
        return ResolvedChartArtifact(
            chart_id=artifact.chart_id,
            label=artifact.label,
            chart_spec=artifact.chart_spec,
            record_id=payload.record_id,
            query=payload.query,
            df=payload.df,
            query_lexer=payload.query_lexer,
        )

    async def _resolve_map(self, artifact: MapArtifactDef) -> ResolvedMapArtifact | None:
        return await self._map_from_artifact(artifact)

    async def _resolve_graph(
        self,
        artifact: GraphArtifactDef,
        selection: Mapping[str, SelectionValue],
        controls: Sequence[AnswerControl],
    ) -> ResolvedGraphArtifact | ArtifactPlaceholder | None:
        sources = await self._graph_sources(artifact.graph_spec, artifact.label, selection, controls)
        if isinstance(sources, (ArtifactPlaceholder, type(None))):
            return sources
        try:
            return self._graph_from_artifact(artifact, sources)
        except GraphSpecError:
            return None

    async def _source_payload(
        self,
        source_id: str,
        label: str | None,
        selection: Mapping[str, SelectionValue],
        controls: Sequence[AnswerControl],
    ) -> ResolvedQueryRecord | ArtifactPlaceholder | None:
        resolution = await self._resolve_query_record(source_id, selection)
        if isinstance(resolution, SourceNotApplicable):
            return ArtifactPlaceholder(
                label=label,
                message=self._not_applicable_message(source_id, selection, controls, resolution.reason),
            )
        return resolution

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

    async def _map_from_artifact(self, artifact: MapArtifactDef) -> ResolvedMapArtifact:
        spec = artifact.map_spec
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
        return ResolvedMapArtifact(map_id=artifact.map_id, label=artifact.label, map_spec=spec, sources=sources)

    async def _graph_sources(
        self,
        graph_spec: Mapping[str, object],
        label: str | None,
        selection: Mapping[str, SelectionValue],
        controls: Sequence[AnswerControl],
    ) -> dict[str, pd.DataFrame] | ArtifactPlaceholder | None:
        source_ids: list[str] = []
        for key in ("nodes", "edges"):
            raw_sources = graph_spec.get(key)
            for source in raw_sources if isinstance(raw_sources, list) else []:
                if not isinstance(source, Mapping) or "data" in source:
                    continue
                source_id = source.get("source_id")
                if isinstance(source_id, str) and source_id not in source_ids:
                    source_ids.append(source_id)
        sources: dict[str, pd.DataFrame] = {}
        for source_id in source_ids:
            payload = await self._source_payload(source_id, label, selection, controls)
            if isinstance(payload, ArtifactPlaceholder):
                return payload
            if payload is None or payload.df is None:
                return None
            sources[source_id] = payload.df
        return sources

    @staticmethod
    def _graph_from_artifact(artifact: GraphArtifactDef, sources: Mapping[str, pd.DataFrame]) -> ResolvedGraphArtifact:
        raw_layout = artifact.graph_spec.get("layout")
        return ResolvedGraphArtifact(
            graph_id=artifact.graph_id,
            label=artifact.label,
            graph=materialize_graph_view(artifact.graph_spec, sources),
            layout=raw_layout if raw_layout in {"force", "layered", "tree"} else "force",
        )
