"""Convert resolved output specs to current display payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from tabulaflow.chat.result import (
    ArtifactPlaceholder,
    ChatResult,
    ResolvedArtifact,
    ResolvedChartArtifact,
    ResolvedGraphArtifact,
    ResolvedMapArtifact,
    ResolvedTableArtifact,
    SelectionValue,
)
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
from tabulaflow.toolhub.render_graph import GraphSpecError, materialize_graph_view

if TYPE_CHECKING:
    import pandas as pd

    from tabulaflow.core.outputs import ArtifactSpec
    from tabulaflow.toolhub.output_resolver import ResolvedArtifact as OutputResolvedArtifact


class OutputDisplayResolver:
    """Resolve a ChatResult's OutputSpec to temporary display payloads."""

    def __init__(self, query_history: QueryHistory) -> None:
        self._query_history = query_history

    async def resolve(
        self,
        result: ChatResult,
        selection: Mapping[str, SelectionValue] | None = None,
    ) -> list[ResolvedArtifact]:
        return await self._resolve_output(result.output, selection)

    async def get_dataframe(self, record_id: str) -> pd.DataFrame:
        return await self._query_history.get_dataframe(record_id)

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
            return _table_from_query_record(payload, artifact.label)
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


def _table_from_query_record(query_record: ResolvedQueryRecord, label: str | None) -> ResolvedTableArtifact:
    return ResolvedTableArtifact(
        record_id=query_record.record_id,
        label=label,
        query=query_record.query,
        df=query_record.df,
        graph=query_record.graph,
        query_lexer=query_record.query_lexer,
    )


def _view_source_ids(view: ViewDef) -> tuple[SourceId, ...]:
    if isinstance(view, TableView | ChartView):
        return (view.source,)
    if isinstance(view, MapView | GraphArtifactView):
        return tuple(view.sources)
    raise TypeError(f"unsupported view {type(view).__name__}")
