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
from tabulaflow.core.outputs import (
    ChartView,
    ChoiceParameter,
    GraphArtifactView,
    MapView,
    OutputSpec,
    ResultLookupPlan,
    SourceId,
    TableView,
    ViewDef,
)
from tabulaflow.toolhub import QueryHistory, ResolvedQueryRecord
from tabulaflow.toolhub.output_resolver import OutputResolutionError, OutputResolver, QueryHistoryResultStore
from tabulaflow.toolhub.query_history import SourceNotApplicable
from tabulaflow.toolhub.render_graph import GraphSpecError, materialize_graph_view

if TYPE_CHECKING:
    import pandas as pd

    from tabulaflow.core.outputs import ArtifactSpec
    from tabulaflow.toolhub.output_resolver import ResolvedArtifact as OutputResolvedArtifact


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
        if result.output is not None:
            return await self._resolve_output(result.output, selection)
        active_selection = self._default_selection(result) if selection is None else dict(selection)
        controls = result.panel.controls if result.panel is not None else ()
        return await self._resolve_many(result.artifacts, active_selection, controls=controls)

    async def get_dataframe(self, record_id: str) -> pd.DataFrame:
        return await self._query_history.get_dataframe(record_id)

    @staticmethod
    def _default_selection(result: ChatResult) -> dict[str, SelectionValue]:
        return dict(result.panel.default_selection) if result.panel is not None else {}

    async def _resolve_output(
        self,
        output: OutputSpec,
        selection: Mapping[str, SelectionValue] | None,
    ) -> list[ResolvedArtifact]:
        resolver = OutputResolver(QueryHistoryResultStore(self._query_history))
        resolved: list[ResolvedArtifact] = []
        for artifact in output.artifacts:
            single = output.model_copy(update={"artifacts": [artifact]})
            try:
                resolved_output = await resolver.resolve(single, selection)
            except OutputResolutionError as exc:
                resolved.append(
                    ArtifactPlaceholder(
                        label=artifact.label,
                        message=self._output_not_applicable_message(output, artifact, selection, str(exc)),
                    )
                )
                continue
            if not resolved_output.artifacts:
                continue
            converted = await self._display_artifact_from_output(resolved_output.artifacts[0])
            if converted is not None:
                resolved.append(converted)
        return resolved

    def _output_not_applicable_message(
        self,
        output: OutputSpec,
        artifact: "ArtifactSpec",
        selection: Mapping[str, SelectionValue] | None,
        fallback: str,
    ) -> str:
        active = dict(output.default_selection)
        if selection is not None:
            active.update(selection)
        parameters = {parameter.id: parameter for parameter in output.parameters}
        sources = {source.id: source for source in output.sources}
        parts: list[str] = []
        for source_id in _view_source_ids(artifact.view):
            source = sources.get(source_id)
            if source is None or not isinstance(source.plan, ResultLookupPlan):
                continue
            for parameter_id in source.parameter_ids:
                selected = active.get(parameter_id)
                if selected is None:
                    continue
                covered = {variant.selection.get(parameter_id) for variant in source.plan.variants}
                if selected in covered:
                    continue
                parameter = parameters.get(parameter_id)
                if not isinstance(parameter, ChoiceParameter):
                    continue
                labels = [choice.label for choice in parameter.choices if choice.id in covered]
                if labels:
                    parts.append(f"{parameter.label} = {' or '.join(labels)}")
        return "only applies when " + "; ".join(parts) if parts else fallback

    async def _display_artifact_from_output(
        self, artifact: "OutputResolvedArtifact"
    ) -> ResolvedArtifact | None:
        view = artifact.view
        if isinstance(view, TableView):
            payload = await self._payload_for_output_source(artifact, view.source)
            if payload is None:
                return None
            return self._table_from_query_record(payload, artifact.label)
        if isinstance(view, ChartView):
            payload = await self._payload_for_output_source(artifact, view.source)
            if payload is None:
                return None
            return ResolvedChartArtifact(
                chart_id=artifact.artifact_id,
                label=artifact.label,
                chart_spec=view.spec,
                record_id=payload.record_id,
                query=payload.query,
                df=payload.df,
                query_lexer=payload.query_lexer,
            )
        if isinstance(view, MapView):
            map_sources: dict[str, pd.DataFrame] = {}
            for source_id, record in artifact.results_by_source.items():
                payload = await self._query_history.get_query_record_payload(record.id)
                if payload.df is not None:
                    map_sources[source_id] = payload.df
            return ResolvedMapArtifact(
                map_id=artifact.artifact_id, label=artifact.label, map_spec=view.spec, sources=map_sources
            )
        if isinstance(view, GraphArtifactView):
            graph_sources: dict[str, pd.DataFrame] = {}
            for source_id, record in artifact.results_by_source.items():
                payload = await self._query_history.get_query_record_payload(record.id)
                if payload.df is None:
                    return None
                graph_sources[source_id] = payload.df
            try:
                raw_layout = view.spec.get("layout")
                return ResolvedGraphArtifact(
                    graph_id=artifact.artifact_id,
                    label=artifact.label,
                    graph=materialize_graph_view(view.spec, graph_sources),
                    layout=raw_layout if raw_layout in {"force", "layered", "tree"} else "force",
                )
            except GraphSpecError:
                return None
        return None

    async def _payload_for_output_source(
        self, artifact: "OutputResolvedArtifact", source_id: str
    ) -> ResolvedQueryRecord | None:
        record = artifact.results_by_source.get(source_id)
        if record is None:
            return None
        try:
            return await self._query_history.get_query_record_payload(record.id)
        except (KeyError, ValueError):
            return None

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


def _view_source_ids(view: ViewDef) -> tuple[SourceId, ...]:
    if isinstance(view, TableView | ChartView):
        return (view.source,)
    if isinstance(view, MapView | GraphArtifactView):
        return tuple(view.sources)
    raise TypeError(f"unsupported view {type(view).__name__}")
